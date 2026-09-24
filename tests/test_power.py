"""PowerSampler's own constructor shells out to `sudo powermetrics`, so these
exercise the line-parsing and window-aggregation logic directly against a
bare instance built via __new__ (mirrors the CoreStub pattern in
test_session_core.py) rather than paying for a real subprocess."""

from pathlib import Path

from joulie.power import PowerSample, PowerSampler, _apply_sample_line, _iter_samples, _worst_pressure

FIXTURES = Path(__file__).parent / "fixtures"


def make_sampler(samples):
    sampler = PowerSampler.__new__(PowerSampler)
    sampler.available = True
    sampler._samples = list(samples)
    sampler._lock = __import__("threading").Lock()
    return sampler


class TestWorstPressure:
    def test_ranks_serious_above_nominal(self):
        assert _worst_pressure(["Nominal", "Serious", "Fair"]) == "Serious"

    def test_unknown_levels_rank_lowest(self):
        assert _worst_pressure(["Nominal", "SomeFutureLevel"]) == "Nominal"


class TestWindowStats:
    def test_averages_power_within_the_window(self):
        sampler = make_sampler([
            PowerSample(wall_time=10.0, cpu_mw=1000, gpu_mw=500, thermal_pressure="Nominal"),
            PowerSample(wall_time=11.0, cpu_mw=2000, gpu_mw=1500, thermal_pressure="Fair"),
            PowerSample(wall_time=20.0, cpu_mw=9000, gpu_mw=9000, thermal_pressure="Critical"),
        ])
        stats = sampler.window_stats(start_wall=9.5, end_wall=11.5)
        assert stats["cpu_power_mw_avg"] == 1500
        assert stats["gpu_power_mw_max"] == 1500
        assert stats["thermal_pressure_max"] == "Fair"
        # The 20.0s sample is outside the window and must not pull in Critical.
        assert stats["thermal_pressure_max"] != "Critical"

    def test_empty_when_unavailable(self):
        sampler = make_sampler([])
        sampler.available = False
        assert sampler.window_stats(0.0, 100.0) == {}

    def test_empty_when_no_samples_fall_in_window(self):
        sampler = make_sampler([PowerSample(wall_time=1.0, cpu_mw=100)])
        assert sampler.window_stats(50.0, 60.0) == {}

    def test_averages_gpu_frequency_and_residency_within_the_window(self):
        sampler = make_sampler([
            PowerSample(wall_time=10.0, gpu_freq_mhz=444, gpu_active_pct=20.0, gpu_idle_pct=80.0),
            PowerSample(wall_time=11.0, gpu_freq_mhz=612, gpu_active_pct=40.0, gpu_idle_pct=60.0),
        ])
        stats = sampler.window_stats(start_wall=9.5, end_wall=11.5)
        assert stats["gpu_freq_mhz_avg"] == 528
        assert stats["gpu_freq_mhz_max"] == 612
        assert stats["gpu_active_pct_avg"] == 30.0
        assert stats["gpu_idle_pct_avg"] == 70.0

    def test_gpu_frequency_fields_are_none_rather_than_absent_when_unparsed(self):
        # A sample can complete (thermal pressure seen) without ever matching
        # the GPU HW active frequency/residency lines — e.g. a macOS version
        # that phrases them differently. Must not KeyError downstream.
        sampler = make_sampler([PowerSample(wall_time=10.0, thermal_pressure="Nominal")])
        stats = sampler.window_stats(9.0, 11.0)
        assert stats["gpu_freq_mhz_avg"] is None
        assert stats["gpu_active_pct_avg"] is None

    def test_averages_memory_and_swap_within_the_window(self):
        sampler = make_sampler([
            PowerSample(wall_time=10.0, mem_used_pct=60.0, mem_available_mb=8000.0, swap_used_mb=100.0, swap_pct=1.0),
            PowerSample(wall_time=11.0, mem_used_pct=80.0, mem_available_mb=4000.0, swap_used_mb=500.0, swap_pct=5.0),
        ])
        stats = sampler.window_stats(start_wall=9.5, end_wall=11.5)
        assert stats["mem_used_pct_avg"] == 70.0
        assert stats["mem_used_pct_max"] == 80.0
        # Minimum, not average — the worst (lowest) headroom point is what
        # would explain an isolated stall inside the window.
        assert stats["mem_available_mb_min"] == 4000.0
        assert stats["swap_used_mb_avg"] == 300.0
        assert stats["swap_used_mb_max"] == 500.0
        assert stats["swap_pct_max"] == 5.0

    def test_memory_fields_are_none_rather_than_absent_when_unread(self):
        sampler = make_sampler([PowerSample(wall_time=10.0, thermal_pressure="Nominal")])
        stats = sampler.window_stats(9.0, 11.0)
        assert stats["mem_used_pct_avg"] is None
        assert stats["mem_available_mb_min"] is None
        assert stats["swap_used_mb_max"] is None
        assert stats["swap_pct_max"] is None


class TestApplyMemory:
    def test_populates_memory_and_swap_fields(self):
        from joulie.power import _apply_memory

        sample = PowerSample(wall_time=0.0)
        _apply_memory(sample)
        assert sample.mem_used_pct is not None
        assert sample.mem_available_mb is not None
        assert sample.swap_used_mb is not None
        assert sample.swap_pct is not None

    def test_degrades_silently_if_psutil_raises(self, monkeypatch):
        import joulie.power as power_mod

        def _boom():
            raise RuntimeError("no permission")

        monkeypatch.setattr(power_mod.psutil, "virtual_memory", _boom)
        sample = PowerSample(wall_time=0.0)
        power_mod._apply_memory(sample)  # must not raise
        assert sample.mem_used_pct is None


class TestApplySampleLine:
    """The real per-line parsing powermetrics output goes through — exercised
    directly since PowerSampler._read_loop reads from a live subprocess."""

    def test_parses_cpu_and_gpu_power(self):
        sample = PowerSample(wall_time=0.0)
        _apply_sample_line(sample, "CPU Power: 3928 mW")
        _apply_sample_line(sample, "GPU Power: 1521 mW")
        assert (sample.cpu_mw, sample.gpu_mw) == (3928, 1521)

    def test_parses_gpu_frequency_and_residency(self):
        sample = PowerSample(wall_time=0.0)
        _apply_sample_line(sample, "GPU HW active frequency: 444 MHz")
        _apply_sample_line(sample, "GPU HW active residency:  35.24%")
        _apply_sample_line(sample, "GPU idle residency:  64.76%")
        assert sample.gpu_freq_mhz == 444
        assert sample.gpu_active_pct == 35.24
        assert sample.gpu_idle_pct == 64.76

    def test_residency_line_with_per_frequency_breakdown_still_parses(self):
        sample = PowerSample(wall_time=0.0)
        _apply_sample_line(sample, "GPU HW active residency:  35.24% (444 MHz: 35% 612 MHz: 0.0%)")
        assert sample.gpu_active_pct == 35.24

    def test_thermal_pressure_line_is_captured(self):
        sample = PowerSample(wall_time=0.0)
        _apply_sample_line(sample, "CPU Power: 1000 mW")
        _apply_sample_line(sample, "Current pressure level: Fair")
        assert sample.thermal_pressure == "Fair"

    def test_unrecognised_line_is_ignored(self):
        sample = PowerSample(wall_time=0.0)
        _apply_sample_line(sample, "Some unrelated powermetrics line")
        assert sample == PowerSample(wall_time=0.0)


class TestIterSamples:
    """A sample must flush on the *next* block's start, not on seeing thermal
    pressure — real powermetrics output prints thermal pressure *before* the
    GPU usage section, so flushing early silently dropped every turn's GPU
    frequency/residency data (0/30 turns captured it before this fix)."""

    def test_splits_on_sample_start_not_on_thermal_pressure(self):
        lines = [
            "*** Sampled system activity (t1) ***",
            "CPU Power: 100 mW",
            "**** Thermal pressure ****",
            "Current pressure level: Nominal",
            "**** GPU usage ****",
            "GPU HW active frequency: 444 MHz",
            "GPU idle residency: 80.0%",
            "*** Sampled system activity (t2) ***",
            "CPU Power: 200 mW",
        ]
        samples = list(_iter_samples(lines))
        assert len(samples) == 2
        first = samples[0]
        assert first.cpu_mw == 100
        assert first.thermal_pressure == "Nominal"
        # These are the fields the old push-on-thermal design lost entirely.
        assert first.gpu_freq_mhz == 444
        assert first.gpu_idle_pct == 80.0

    def test_real_powermetrics_capture_from_the_kiosk_mac(self):
        text = (FIXTURES / "powermetrics_sample.txt").read_text().splitlines()
        samples = list(_iter_samples(text))
        assert len(samples) == 2
        s1, s2 = samples
        assert (s1.cpu_mw, s1.gpu_mw) == (37, 3)
        assert s1.thermal_pressure == "Nominal"
        assert s1.gpu_freq_mhz == 338
        assert s1.gpu_active_pct == 1.38
        assert s1.gpu_idle_pct == 98.62
        assert (s2.cpu_mw, s2.gpu_mw) == (12, 0)
        assert s2.gpu_freq_mhz == 338
        assert s2.gpu_active_pct == 0.44
        assert s2.gpu_idle_pct == 99.56
