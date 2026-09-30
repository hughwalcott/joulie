"""The language-switching policy (JTBD-03). A false switch answers an English
visitor in Mandarin, so staying put is the default and a switch has to be earned."""

from joulie import config, language
from joulie.language import choose_language

ALLOWED = frozenset({"en", "zh"})


def choose(session, probs, seconds=3.0, **kw):
    return choose_language(session, probs, seconds, allowed=ALLOWED,
                           min_prob=0.7, min_seconds=1.5, **kw)


class TestChooseLanguage:
    def test_a_confident_mandarin_question_switches_the_session(self):
        assert choose("en", [("zh", 0.95), ("en", 0.03)]) == "zh"

    def test_an_unsure_detection_keeps_the_session_language(self):
        assert choose("en", [("zh", 0.55), ("en", 0.45)]) == "en"

    def test_a_short_utterance_cannot_switch_even_when_confident(self):
        # "ok" mid-Mandarin: Whisper's language ID on one word is a coin toss.
        assert choose("zh", [("en", 0.99)], seconds=0.8) == "zh"

    def test_a_long_confident_english_utterance_switches_back(self):
        assert choose("zh", [("en", 0.96), ("zh", 0.02)]) == "en"

    def test_unsupported_languages_are_discounted_not_followed(self):
        # Kiwi English half-heard as Welsh: restricted to what Joulie supports,
        # English is the clear winner.
        assert choose("en", [("cy", 0.6), ("en", 0.35), ("zh", 0.05)]) == "en"

    def test_a_confident_unsupported_language_keeps_the_session(self):
        assert choose("en", [("ja", 0.97), ("zh", 0.02), ("en", 0.01)]) == "en"

    def test_no_probabilities_keeps_the_session(self):
        assert choose("zh", None) == "zh"
        assert choose("zh", ()) == "zh"

    def test_defaults_come_from_config(self, monkeypatch):
        monkeypatch.setattr(config, "LANGUAGES", ("en", "zh"))
        monkeypatch.setattr(config, "TEXT_ONLY_LANGUAGES", ())
        monkeypatch.setattr(config, "LANG_SWITCH_MIN_PROB", 0.99)
        assert choose_language("en", [("zh", 0.95), ("en", 0.05)], 3.0) == "en"


class TestRegistry:
    def test_english_has_no_directive_so_its_prompt_is_unchanged(self):
        assert language.reply_directive("en") == ""

    def test_mandarin_keeps_tool_names_in_english_for_the_qr_panel(self):
        assert "Billy" in language.reply_directive("zh")

    def test_text_only_languages_join_the_allowlist(self, monkeypatch):
        monkeypatch.setattr(config, "LANGUAGES", ("en",))
        monkeypatch.setattr(config, "TEXT_ONLY_LANGUAGES", ("mi",))
        assert language.active_codes() == {"en", "mi"}
        assert language.is_text_only("mi")

    def test_unknown_codes_in_config_are_ignored(self, monkeypatch):
        monkeypatch.setattr(config, "LANGUAGES", ("en", "xx"))
        monkeypatch.setattr(config, "TEXT_ONLY_LANGUAGES", ())
        assert language.active_codes() == {"en"}

    def test_te_reo_cannot_be_voiced(self):
        assert language.is_text_only("mi")
        assert "te reo Māori" in language.fallback_notice("mi")


class TestConfidenceIsNotInflated:
    def test_dropping_unsupported_candidates_does_not_manufacture_confidence(self):
        # 55% English with the rest on Welsh is not a confident English switch.
        assert choose("zh", [("en", 0.55), ("cy", 0.45)]) == "zh"


# The languages XTTS-v2's tokenizer implements; anything else raises inside it.
XTTS_LANGUAGES = {"en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl",
                  "cs", "ar", "zh-cn", "hu", "ko", "ja", "hi"}


class TestEveryConfiguredLanguage:
    """A language in config.LANGUAGES without a complete entry silently answers
    in English — the bug that made Hindi and German visitors get English."""

    def test_every_default_language_has_an_entry(self):
        assert set(config.LANGUAGES) <= set(language.LANGUAGES)

    def test_hindi_and_the_major_european_languages_are_on_by_default(self):
        assert {"hi", "es", "fr", "de", "it", "pt", "nl", "pl", "ru"} <= set(config.LANGUAGES)

    def test_every_voiced_language_is_one_xtts_can_speak(self):
        for code in config.LANGUAGES:
            assert language.get(code).xtts_code in XTTS_LANGUAGES, code

    def test_every_non_english_entry_is_complete(self):
        english = language.get("en")
        for code in set(config.LANGUAGES) - {"en"}:
            entry = language.get(code)
            assert entry.reply_directive and entry.badge and entry.disclaimer, code
            assert entry.error_line != english.error_line, code
            assert entry.units != english.units and entry.country != english.country, code

    def test_hindi_is_asked_for_in_devanagari(self):
        assert "Devanagari" in language.reply_directive("hi")

    def test_unreviewed_languages_are_reported_and_english_is_not(self, monkeypatch):
        monkeypatch.setattr(config, "LANGUAGES", ("en", "de"))
        monkeypatch.setattr(config, "TEXT_ONLY_LANGUAGES", ())
        assert language.unreviewed() == ["de"]


class TestHindiUrdu:
    ALLOWED = frozenset({"en", "hi"})

    def test_urdu_probability_counts_towards_hindi(self):
        # Neither half clears 0.7 alone; together they are a confident Hindi.
        assert choose_language("en", [("hi", 0.45), ("ur", 0.40), ("en", 0.1)], 3.0,
                               allowed=self.ALLOWED, min_prob=0.7, min_seconds=1.5) == "hi"

    def test_a_confident_urdu_detection_answers_in_hindi(self):
        assert choose_language("en", [("ur", 0.9)], 3.0, allowed=self.ALLOWED,
                               min_prob=0.7, min_seconds=1.5) == "hi"
