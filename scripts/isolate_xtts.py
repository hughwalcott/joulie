"""One-shot diagnostic script: run XTTS-v2 synthesis alone — no Whisper, no
Ollama, no ChromaDB, no audio playback — to test whether the turn-5+ swap
growth documented in logs/latency-analysis.md lives inside XTTS/the PyTorch
MPS allocator, independent of the rest of the pipeline sharing the machine's
unified memory.

Loads XTTS-v2 the same way joulie.audio.Speaker does (same conditioning
latents, same warmup) but skips Speaker's sd.OutputStream entirely — this
script never plays audio, it only measures synthesis cost and memory.

Pass --empty-cache to call torch.mps.empty_cache() after every sentence, to
test whether that reclaims the MPS allocator's pool and flattens the growth.
Run once without the flag and once with it, then diff the two output files.

Usage:
    source .venv/bin/activate
    python scripts/isolate_xtts.py [--empty-cache] [--turns 12]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from joulie import config
from joulie.quiet import allow_xtts_checkpoint_unpickling, silenced_stdout

allow_xtts_checkpoint_unpickling()

# Multi-sentence replies shaped like real Joulie answers (3-5 sentences,
# ~300-700 chars) so per-turn synthesis workload matches production instead
# of a single short utterance.
_TURN_REPLIES = [
    [
        "Rooftop solar in Auckland typically pays itself back in seven to ten years.",
        "That depends heavily on your daytime usage and whether you export excess to the grid.",
        "A north-facing four kilowatt system is a common starting point for a three bedroom home.",
    ],
    [
        "A heat pump hot water cylinder uses about a third of the energy a standard electric one does.",
        "The trade-off is a higher upfront cost and a bit more installation space.",
        "Most households recover that difference within four to six years through lower power bills.",
        "It also tends to run quietly once it's bedded in.",
    ],
    [
        "Switching from LPG to induction cooking is worth it for most households.",
        "Induction is more energy efficient and removes the ongoing cost of bottle refills.",
        "You will need induction-compatible cookware, which is the main upfront cost.",
    ],
    [
        "There are a few rebate schemes for EV chargers depending on your region and power company.",
        "Some lines companies offer a discount on off-peak charging plans instead of a straight rebate.",
        "It's worth checking with your specific retailer, since offers change fairly often.",
        "Community charging hubs are also expanding in a lot of towns.",
    ],
    [
        "Insulation retrofitting can cut heating costs meaningfully, especially in older villas.",
        "Ceiling and underfloor insulation together often make the biggest difference.",
        "Savings vary by climate zone, but many households see a noticeable drop in their winter power bill.",
    ],
    [
        "A home battery makes the most sense if you already have solar and want to use more of what you generate.",
        "Without solar, a battery mostly just shifts when you draw from the grid rather than saving energy overall.",
        "Payback periods for batteries are still longer than for solar panels alone.",
    ],
    [
        "A hybrid heat pump keeps a gas or electric booster for very cold days, while a fully electric one relies entirely on the heat pump.",
        "Fully electric systems are simpler and cheaper to run long term in most of New Zealand's climate.",
        "Hybrids can still make sense in colder inland regions.",
    ],
    [
        "Time-of-use plans charge different rates depending on when you use power.",
        "For EV owners, charging overnight on an off-peak rate can cut charging costs substantially.",
        "Not every retailer offers a time-of-use plan, so it's worth comparing a few before switching.",
        "Smart chargers can automate this so you don't have to remember to plug in at a certain time.",
    ],
    [
        "Off-grid solar is realistic on a lifestyle block, but it usually needs a generator for backup during long overcast stretches.",
        "Sizing the battery bank correctly for winter generation is the part people most often get wrong.",
        "Grid-connected hybrid setups are usually cheaper unless the connection cost is very high.",
    ],
    [
        "A three bedroom house typically needs a system in the four to six kilowatt range, depending on usage.",
        "Roof orientation and shading make a bigger difference than most people expect.",
        "An energy assessment before installation will give a much more accurate number than a rule of thumb.",
    ],
    [
        "EV batteries in New Zealand conditions typically last eight to fifteen years before capacity drops meaningfully.",
        "Our mild climate is actually kinder to batteries than places with extreme heat.",
        "Most manufacturers back this with an eight year or one hundred and sixty thousand kilometre warranty.",
    ],
    [
        "There are a few financing options for whole-home electrification, including green home loans from some banks.",
        "Some lines companies also offer interest-free finance for specific upgrades like heat pumps.",
        "It's worth stacking a rebate with a low-interest loan where both are available.",
        "Costs vary a lot by scope, so getting quotes for the whole project up front helps with financing decisions.",
    ],
]


def _mem_snapshot(proc: psutil.Process) -> dict:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    snap = {
        "mem_used_pct": vm.percent,
        "mem_available_mb": round(vm.available / (1024 * 1024), 1),
        "swap_used_mb": round(swap.used / (1024 * 1024), 1),
        "swap_pct": swap.percent,
        "proc_rss_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
    }
    try:
        import torch
        if torch.backends.mps.is_available():
            snap["mps_current_allocated_mb"] = round(
                torch.mps.current_allocated_memory() / (1024 * 1024), 1
            )
            snap["mps_driver_allocated_mb"] = round(
                torch.mps.driver_allocated_memory() / (1024 * 1024), 1
            )
    except Exception:
        pass
    return snap


def run(turns: int, empty_cache: bool) -> list[dict]:
    import torch

    ref_wav = Path(config.XTTS_REF_WAV)
    if not ref_wav.exists():
        raise SystemExit(f"reference WAV not found: {ref_wav}")

    mps = torch.backends.mps.is_available()
    device = "mps" if mps else "cpu"
    print(f"[isolate-xtts] loading XTTS-v2 (device: {device}, empty_cache={empty_cache})...")
    from TTS.api import TTS
    with silenced_stdout():
        tts = TTS(config.XTTS_MODEL)
    model = tts.synthesizer.tts_model
    if mps:
        model = model.to("mps")

    print("[isolate-xtts] computing speaker conditioning latents...")
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
        audio_path=[str(ref_wav)],
        gpt_cond_len=config.XTTS_GPT_COND_LEN,
        gpt_cond_chunk_len=config.XTTS_GPT_COND_CHUNK_LEN,
        max_ref_length=config.XTTS_MAX_REF_LEN,
        sound_norm_refs=config.XTTS_SOUND_NORM_REFS,
    )
    print(f"[isolate-xtts] warming up {device} kernels...")
    model.inference(
        text="ok",
        language=config.XTTS_LANGUAGE,
        gpt_cond_latent=gpt_cond_latent,
        speaker_embedding=speaker_embedding,
    )
    if mps:
        torch.mps.synchronize()

    proc = psutil.Process(os.getpid())
    results = []
    session_start = time.monotonic()
    baseline = _mem_snapshot(proc)
    print(f"[isolate-xtts] baseline: {baseline}")

    for i in range(turns):
        sentences = _TURN_REPLIES[i % len(_TURN_REPLIES)]
        t0 = time.monotonic()
        synth_seconds = []
        synth_rtf = []
        for sentence in sentences:
            s0 = time.monotonic()
            out = model.inference(
                text=sentence,
                language=config.XTTS_LANGUAGE,
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                speed=config.XTTS_SPEED,
            )
            if mps:
                torch.mps.synchronize()
            wav = np.array(out["wav"], dtype=np.float32)
            synth_s = time.monotonic() - s0
            audio_s = max(wav.size / config.XTTS_SAMPLE_RATE, 1e-6)
            synth_seconds.append(round(synth_s, 3))
            synth_rtf.append(round(synth_s / audio_s, 3))
            del out, wav
            if empty_cache and mps:
                torch.mps.empty_cache()
        turn_s = time.monotonic() - t0
        snap = _mem_snapshot(proc)
        elapsed = time.monotonic() - session_start
        row = {
            "turn": i + 1,
            "elapsed_s": round(elapsed, 2),
            "turn_synth_s": round(turn_s, 3),
            "chunk_synth_seconds": synth_seconds,
            "chunk_rtf": synth_rtf,
            **snap,
        }
        results.append(row)
        print(
            f"[isolate-xtts] turn {row['turn']:2d}  +{row['elapsed_s']:6.1f}s  "
            f"turn_synth={row['turn_synth_s']:5.2f}s  max_rtf={max(synth_rtf):4.2f}  "
            f"mem={snap['mem_used_pct']:.1f}%  avail={snap['mem_available_mb']:.0f}MB  "
            f"swap={snap['swap_used_mb']:.0f}MB  rss={snap['proc_rss_mb']:.0f}MB"
            + (
                f"  mps_alloc={snap.get('mps_current_allocated_mb', 0):.0f}MB"
                f"  mps_driver={snap.get('mps_driver_allocated_mb', 0):.0f}MB"
                if mps else ""
            )
        )

    return [{"baseline": baseline}] + results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=12)
    parser.add_argument("--empty-cache", action="store_true")
    args = parser.parse_args()

    rows = run(args.turns, args.empty_cache)
    out_dir = Path(config.METRICS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "emptycache" if args.empty_cache else "baseline"
    out_path = out_dir / f"isolate_xtts_{suffix}_{time.strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"[isolate-xtts] wrote {out_path}")
