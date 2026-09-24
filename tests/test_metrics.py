"""build_summary/append_turn are pure(ish) aside from file I/O, so these test
against a tmp_path METRICS_DIR rather than mocking the module."""

import json

from joulie import config, metrics


class TestBuildSummary:
    def test_averages_and_maxes_across_turns(self):
        turns = [
            metrics.TurnMetrics(turn_index=1, started_at=0.0, llm_ttft_seconds=1.05,
                                 tts_chunk_rtf=[0.80, 0.39, 0.36]),
            metrics.TurnMetrics(turn_index=2, started_at=1.0, llm_ttft_seconds=5.93,
                                 tts_chunk_rtf=[2.28, 0.90, 0.38, 0.39]),
        ]
        summary = metrics.build_summary("sess1", started_at=0.0, turns=turns)
        assert summary.num_turns == 2
        assert summary.max_llm_ttft_seconds == 5.93
        assert summary.avg_llm_ttft_seconds == (1.05 + 5.93) / 2
        assert summary.max_tts_rtf == 2.28

    def test_flags_throttled_when_any_turn_saw_non_nominal_pressure(self):
        turns = [
            metrics.TurnMetrics(turn_index=1, started_at=0.0,
                                 power={"thermal_pressure_max": "Nominal"}),
            metrics.TurnMetrics(turn_index=2, started_at=1.0,
                                 power={"thermal_pressure_max": "Serious"}),
        ]
        summary = metrics.build_summary("sess1", started_at=0.0, turns=turns)
        assert summary.throttled is True

    def test_not_throttled_when_no_power_data_at_all(self):
        turns = [metrics.TurnMetrics(turn_index=1, started_at=0.0)]
        summary = metrics.build_summary("sess1", started_at=0.0, turns=turns)
        assert summary.throttled is False

    def test_empty_turns_do_not_divide_by_zero(self):
        summary = metrics.build_summary("sess1", started_at=0.0, turns=[])
        assert summary.avg_llm_ttft_seconds == 0.0
        assert summary.avg_tts_rtf == 0.0


class TestPersistence:
    def test_append_turn_writes_one_jsonl_line_per_call(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "METRICS_DIR", str(tmp_path))
        metrics.append_turn("sess1", metrics.TurnMetrics(turn_index=1, started_at=0.0))
        metrics.append_turn("sess1", metrics.TurnMetrics(turn_index=2, started_at=1.0))
        lines = (tmp_path / "sessions" / "sess1.jsonl").read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["turn_index"] == 2

    def test_append_turn_is_a_no_op_when_metrics_disabled(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "METRICS_DIR", str(tmp_path))
        monkeypatch.setattr(config, "METRICS_ENABLED", False)
        metrics.append_turn("sess1", metrics.TurnMetrics(turn_index=1, started_at=0.0))
        assert not (tmp_path / "sessions").exists()

    def test_write_summary_creates_the_summary_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "METRICS_DIR", str(tmp_path))
        summary = metrics.build_summary("sess1", started_at=0.0, turns=[])
        metrics.write_summary(summary)
        path = tmp_path / "sessions" / "sess1_summary.json"
        assert json.loads(path.read_text())["session_id"] == "sess1"
