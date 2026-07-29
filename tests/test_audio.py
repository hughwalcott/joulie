"""sanitize_for_speech is a pure function, but importing joulie.audio pulls in
XTTS and faster-whisper. Nothing here loads a model — only the module."""

from joulie.audio import sanitize_for_speech


class TestDegenerateInput:
    def test_url_only_chunk_is_rejected(self):
        # Scrubs down to "." — XTTS answers a lone full stop with babble.
        assert sanitize_for_speech("https://www.eeca.govt.nz/calculator.") == ""

    def test_punctuation_only_is_rejected(self):
        assert sanitize_for_speech(" -- ... ") == ""

    def test_empty_is_rejected(self):
        assert sanitize_for_speech("   ") == ""


class TestMarkdownAndUrls:
    def test_markdown_link_leaves_no_stray_parens(self):
        out = sanitize_for_speech("Try [Billy](https://billy.org.nz) today.")
        assert "(" not in out and ")" not in out
        assert out == "Try Billy today."

    def test_bare_url_is_removed_without_orphan_punctuation(self):
        out = sanitize_for_speech("Visit www.eeca.govt.nz for details.")
        assert "www" not in out
        assert out == "Visit for details."

    def test_bold_markers_are_stripped(self):
        assert sanitize_for_speech("That is **very** efficient.") == "That is very efficient."

    def test_parentheses_become_plain_speech(self):
        out = sanitize_for_speech("Use Billy (the comparison tool) first.")
        assert out == "Use Billy the comparison tool first."


class TestPronunciation:
    def test_acronyms_are_spelled_out(self):
        out = sanitize_for_speech("EECA and MBIE both publish this.")
        assert out == "E E C A and M B I E both publish this."

    def test_units_are_spoken_as_words(self):
        assert sanitize_for_speech("A 6.5 kW unit.") == "A 6.5 kilowatts unit."

    def test_kwh_wins_over_kw(self):
        out = sanitize_for_speech("You used 300 kWh last month.")
        assert out == "You used 300 kilowatt hours last month."

    def test_nz_becomes_new_zealand(self):
        assert sanitize_for_speech("Across NZ homes.") == "Across New Zealand homes."

    def test_lowercase_words_are_untouched(self):
        # \b...\b is case-sensitive, so ordinary prose can't be mangled.
        assert sanitize_for_speech("We are between the two.") == "We are between the two."

    def test_qr_prompt_is_readable(self):
        out = sanitize_for_speech("Scan the QR code on screen.")
        assert out == "Scan the Q R code on screen."


class TestPassthrough:
    def test_ordinary_sentence_is_unchanged(self):
        text = "Heat pumps are about three times more efficient than gas heating."
        assert sanitize_for_speech(text) == text

    def test_currency_and_percentages_survive_for_the_xtts_cleaner(self):
        # XTTS's own cleaner expands these; we must not damage them first.
        text = "Households saved $284 in 2024, about 30% of the bill."
        assert sanitize_for_speech(text) == text
