"""Background macOS power/thermal sampling via `sudo powermetrics`.

Runs one long-lived `powermetrics` process for the kiosk's lifetime rather
than shelling out per turn — a one-shot invocation costs a full sample
interval (~1s) of its own and would skew the very latency it's measuring.
Turn code instead asks for the samples that fell inside a turn's time
window after the fact.

Requires a passwordless NOPASSWD sudoers entry for `powermetrics` on the
kiosk account, e.g.:

    <kiosk-user> ALL=(root) NOPASSWD: /usr/bin/powermetrics

Without it, `sudo -n` fails immediately (never prompts, never hangs the
kiosk) and PowerSampler.available stays False — turn metrics just come back
without power/thermal fields.
"""

import re
import subprocess
import threading
import time
from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Optional

import psutil

from joulie import config

_POWER_LINE = re.compile(r"^([A-Za-z][\w ()/+]*) Power: (\d+) mW$")
# Residency lines carry a parenthesised per-frequency breakdown on some macOS
# versions ("35.24% (444 MHz: 35% ...)") — matching stops at the first "%" so
# both the bare and annotated forms parse the same leading figure.
_GPU_FREQ_LINE = re.compile(r"^GPU HW active frequency: (\d+) MHz$")
_GPU_ACTIVE_LINE = re.compile(r"^GPU HW active residency:\s+([\d.]+)%")
_GPU_IDLE_LINE = re.compile(r"^GPU idle residency:\s+([\d.]+)%")
_PRESSURE_LINE = re.compile(r"^Current pressure level: (\w+)$")
_SAMPLE_START = re.compile(r"^\*\*\* Sampled system activity")

_PRESSURE_RANK = {"Nominal": 0, "Fair": 1, "Serious": 2, "Critical": 3}


@dataclass
class PowerSample:
    wall_time: float
    cpu_mw: Optional[float] = None
    gpu_mw: Optional[float] = None
    # Distinguishes "doing more real work" (residency up, frequency steady)
    # from "throttled" (frequency down, residency up to compensate) or "GPU
    # busy independent of Joulie's own turn" — power draw alone can't tell
    # those apart, since a throttled GPU can draw about the same wattage for
    # longer instead of less wattage for the same time.
    gpu_freq_mhz: Optional[float] = None
    gpu_active_pct: Optional[float] = None
    gpu_idle_pct: Optional[float] = None
    thermal_pressure: Optional[str] = None
    # System-wide memory/swap pressure, via psutil rather than powermetrics —
    # a separate data source, attached in PowerSampler._push() at the same
    # cadence rather than parsed from the powermetrics text stream. Added to
    # test whether occasional severe stalls (e.g. a single 52.8s TTS chunk
    # amid otherwise-normal ones) coincide with page-fault/compression cost
    # from running Whisper + a 14B Ollama model + XTTS on the same unified
    # memory, once history/prompt-size and thermal throttling were ruled out.
    mem_used_pct: Optional[float] = None
    mem_available_mb: Optional[float] = None
    swap_used_mb: Optional[float] = None
    swap_pct: Optional[float] = None


def _worst_pressure(levels: list[str]) -> str:
    return max(levels, key=lambda lvl: _PRESSURE_RANK.get(lvl, 0))


def _apply_sample_line(sample: PowerSample, line: str) -> None:
    """Mutates `sample` in place from one powermetrics output line."""
    m = _POWER_LINE.match(line)
    if m:
        label, mw = m.group(1).strip(), float(m.group(2))
        if label == "CPU":
            sample.cpu_mw = mw
        elif label == "GPU":
            sample.gpu_mw = mw
        return
    m = _GPU_FREQ_LINE.match(line)
    if m:
        sample.gpu_freq_mhz = float(m.group(1))
        return
    m = _GPU_ACTIVE_LINE.match(line)
    if m:
        sample.gpu_active_pct = float(m.group(1))
        return
    m = _GPU_IDLE_LINE.match(line)
    if m:
        sample.gpu_idle_pct = float(m.group(1))
        return
    m = _PRESSURE_LINE.match(line)
    if m:
        sample.thermal_pressure = m.group(1)


def _iter_samples(lines: Iterable[str]) -> Iterator[PowerSample]:
    """One PowerSample per `*** Sampled system activity` block. A sample is
    flushed when the *next* block starts (or the input ends) — not on seeing
    thermal pressure, which was the bug: real powermetrics output prints
    "**** Thermal pressure ****" *before* "**** GPU usage ****", so treating
    thermal as "sample complete" pushed each sample before its own GPU
    frequency/residency lines had even arrived, silently discarding them into
    a sample that was then reset by the next block's start and never pushed."""
    current: Optional[PowerSample] = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if _SAMPLE_START.match(line):
            if current is not None:
                yield current
            current = PowerSample(wall_time=time.time())
            continue
        if current is not None:
            _apply_sample_line(current, line)
    if current is not None:
        yield current


def _apply_memory(sample: PowerSample) -> None:
    """Mutates `sample` with a psutil memory/swap reading. Best-effort like
    everything else here — never raises into the sampling loop."""
    try:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
    except Exception:
        return
    sample.mem_used_pct = vm.percent
    sample.mem_available_mb = vm.available / (1024 * 1024)
    sample.swap_used_mb = swap.used / (1024 * 1024)
    sample.swap_pct = swap.percent


class PowerSampler:
    """Best-effort background sampler. Every method degrades to inert/empty
    rather than raising — power/thermal data is diagnostic, never load-bearing
    for the kiosk pipeline."""

    def __init__(
        self,
        interval_ms: int = config.POWER_SAMPLE_INTERVAL_MS,
        history_seconds: float = 300.0,
    ):
        self.available = False
        self._interval_ms = interval_ms
        self._history_seconds = history_seconds
        self._samples: deque[PowerSample] = deque()
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        if config.POWER_SAMPLING_ENABLED:
            self._start()

    def _start(self) -> None:
        try:
            self._proc = subprocess.Popen(
                [
                    "sudo", "-n", "powermetrics",
                    "-i", str(self._interval_ms),
                    "--samplers", "cpu_power,gpu_power,thermal",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            print(f"[power] powermetrics unavailable: {exc}")
            return
        threading.Thread(target=self._read_loop, daemon=True).start()
        # A missing NOPASSWD sudoers entry makes `sudo -n` exit immediately
        # with no output — give it one interval to prove otherwise.
        time.sleep(min(1.0, self._interval_ms / 1000))
        if self._proc.poll() is not None:
            print("[power] powermetrics exited immediately — is passwordless "
                  "sudo configured for it? See README. Power metrics disabled.")
            return
        self.available = True
        print("[power] powermetrics sampling started")

    def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            for sample in _iter_samples(self._proc.stdout):
                self._push(sample)
        except Exception as exc:
            print(f"[power] sampling loop stopped: {exc}")

    def _push(self, sample: PowerSample) -> None:
        _apply_memory(sample)
        with self._lock:
            self._samples.append(sample)
            cutoff = time.time() - self._history_seconds
            while self._samples and self._samples[0].wall_time < cutoff:
                self._samples.popleft()

    def window_stats(self, start_wall: float, end_wall: float) -> dict:
        """Aggregate samples timestamped within [start_wall, end_wall].
        Empty dict if sampling is unavailable or the window caught nothing —
        e.g. a turn shorter than the sampling interval."""
        if not self.available:
            return {}
        with self._lock:
            window = [s for s in self._samples if start_wall <= s.wall_time <= end_wall]
        if not window:
            return {}
        cpu = [s.cpu_mw for s in window if s.cpu_mw is not None]
        gpu = [s.gpu_mw for s in window if s.gpu_mw is not None]
        gpu_freq = [s.gpu_freq_mhz for s in window if s.gpu_freq_mhz is not None]
        gpu_active = [s.gpu_active_pct for s in window if s.gpu_active_pct is not None]
        gpu_idle = [s.gpu_idle_pct for s in window if s.gpu_idle_pct is not None]
        pressures = [s.thermal_pressure for s in window if s.thermal_pressure]
        mem_used_pct = [s.mem_used_pct for s in window if s.mem_used_pct is not None]
        mem_available_mb = [s.mem_available_mb for s in window if s.mem_available_mb is not None]
        swap_used_mb = [s.swap_used_mb for s in window if s.swap_used_mb is not None]
        swap_pct = [s.swap_pct for s in window if s.swap_pct is not None]
        return {
            "cpu_power_mw_avg": sum(cpu) / len(cpu) if cpu else None,
            "cpu_power_mw_max": max(cpu) if cpu else None,
            "gpu_power_mw_avg": sum(gpu) / len(gpu) if gpu else None,
            "gpu_power_mw_max": max(gpu) if gpu else None,
            "gpu_freq_mhz_avg": sum(gpu_freq) / len(gpu_freq) if gpu_freq else None,
            "gpu_freq_mhz_max": max(gpu_freq) if gpu_freq else None,
            "gpu_active_pct_avg": sum(gpu_active) / len(gpu_active) if gpu_active else None,
            "gpu_idle_pct_avg": sum(gpu_idle) / len(gpu_idle) if gpu_idle else None,
            "thermal_pressure_max": _worst_pressure(pressures) if pressures else None,
            "mem_used_pct_avg": sum(mem_used_pct) / len(mem_used_pct) if mem_used_pct else None,
            "mem_used_pct_max": max(mem_used_pct) if mem_used_pct else None,
            # Minimum, not average — a headroom metric, so the worst (lowest)
            # point in the window is what would explain an isolated stall.
            "mem_available_mb_min": min(mem_available_mb) if mem_available_mb else None,
            "swap_used_mb_avg": sum(swap_used_mb) / len(swap_used_mb) if swap_used_mb else None,
            "swap_used_mb_max": max(swap_used_mb) if swap_used_mb else None,
            "swap_pct_max": max(swap_pct) if swap_pct else None,
        }

    def stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
