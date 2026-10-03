"""sanitize_for_speech is a pure function, but importing joulie.audio pulls in
XTTS and faster-whisper. Nothing here loads a model — only the module."""

from joulie.audio import resolve_input_device, sanitize_for_speech


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
        assert out == "Eeka and M-B-I-E both publish this."

    def test_acronym_letters_never_leave_a_lone_a(self):
        # A spaced "A" is read as the article: "EEC. A", "a sea power".
        assert sanitize_for_speech("EECA says AC, not DC.") == "Eeka says Ay-C, not D-C."
        assert sanitize_for_speech("The EA tool.") == "The E-Ay tool."

    def test_ruc_is_said_as_a_word(self):
        assert sanitize_for_speech("EVs pay RUCs; one RUC licence.") == "E-V's pay rucks; one ruck licence."

    def test_acronyms_inside_words_are_untouched(self):
        assert sanitize_for_speech("ACC and HVAC and EVSE.") == "ACC and HVAC and EVSE."

    def test_energy_and_power_units(self):
        out = sanitize_for_speech("500 Wh, 2 MW, 3 MWh, 4 GWh and 5 kW.")
        assert out == "500 watt hours, 2 megawatts, 3 megawatt hours, 4 gigawatt hours and 5 kilowatts."

    def test_area_and_volume_units(self):
        assert sanitize_for_speech("120 m2 and 3 m³.") == "120 square metres and 3 cubic metres."

    def test_units_touching_their_number(self):
        assert sanitize_for_speech("300kWh over 10m2.") == "300 kilowatt hours over 10 square metres."

    def test_co2_equivalent(self):
        for written in ("CO2eq", "CO2-e", "CO2e", "CO₂-eq"):
            assert sanitize_for_speech(f"2 tonnes of {written}.") == "2 tonnes of C-O-2 equivalent."
        assert sanitize_for_speech("Less CO2.") == "Less C-O-2."


class TestCurrency:
    def test_magnitude_word_comes_before_dollars(self):
        assert sanitize_for_speech("About $1 Million.") == "About 1 million dollars."
        assert sanitize_for_speech("About $1.5 billion.") == "About 1.5 billion dollars."

    def test_abbreviated_magnitudes(self):
        assert sanitize_for_speech("$20k or $1.5m or $2bn.") == (
            "20 thousand dollars or 1.5 million dollars or 2 billion dollars.")

    def test_plain_amounts_are_left_for_the_xtts_cleaner(self):
        # It already reads "$1,000,000" as "one million dollars".
        assert sanitize_for_speech("It cost $1,000,000.") == "It cost $1,000,000."
        assert sanitize_for_speech("$5 more each month.") == "$5 more each month."

    def test_nz_dollar_prefix_is_dropped(self):
        assert sanitize_for_speech("About NZ$500.") == "About $500."

    def test_other_languages_keep_their_own_currency_path(self):
        assert sanitize_for_speech("$1 million", "de") == "$1 million"

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
        assert out == "Scan the Q-R code on screen."


class TestPassthrough:
    def test_ordinary_sentence_is_unchanged(self):
        text = "Heat pumps are about three times more efficient than gas heating."
        assert sanitize_for_speech(text) == text

    def test_currency_and_percentages_survive_for_the_xtts_cleaner(self):
        # XTTS's own cleaner expands these; we must not damage them first.
        text = "Households saved $284 in 2024, about 30% of the bill."
        assert sanitize_for_speech(text) == text


class TestSanitizeMandarin:
    def test_units_are_spoken_in_chinese(self):
        assert sanitize_for_speech("每年节省300 kWh。", "zh") == "每年节省300 千瓦时。"

    def test_units_touching_han_characters_are_still_found(self):
        assert sanitize_for_speech("用kWh计算", "zh") == "用千瓦时计算"

    def test_nz_becomes_the_chinese_name(self):
        assert sanitize_for_speech("NZ的电价", "zh") == "新西兰的电价"

    def test_acronyms_are_still_spelled_out(self):
        assert sanitize_for_speech("根据EECA的数据", "zh") == "根据E E C A的数据"

    def test_english_is_the_default(self):
        assert sanitize_for_speech("300 kWh") == "300 kilowatt hours"


class TestSanitizeOtherLanguages:
    def test_german_units_and_country(self):
        assert (sanitize_for_speech("Rund 3000 kWh pro Jahr in NZ.", "de")
                == "Rund 3000 Kilowattstunden pro Jahr in Neuseeland.")

    def test_french_units(self):
        assert sanitize_for_speech("6,5 kW", "fr") == "6,5 kilowatts"

    def test_hindi_spells_out_its_numbers(self):
        # XTTS expands digits for every voiced language except Hindi.
        assert sanitize_for_speech("2024 में 300 kWh", "hi") == "दो हज़ार चौबीस में तीन सौ किलोवाट घंटे"

    def test_european_digits_are_left_for_the_xtts_cleaner(self):
        assert "3000" in sanitize_for_speech("3000 kWh", "es")

    def test_an_unknown_language_falls_back_to_english_forms(self):
        assert sanitize_for_speech("300 kWh", "xx") == "300 kilowatt hours"


class TestWhisperRouting:
    def _transcriber(self, monkeypatch):
        from joulie import config
        from joulie.audio import Transcriber
        monkeypatch.setattr(config, "WHISPER_STRONG_LANGUAGES", ("hi",))
        t = Transcriber.__new__(Transcriber)
        t.model, t.strong_model = "base", "small"
        return t

    def test_hindi_is_transcribed_by_the_stronger_model(self, monkeypatch):
        assert self._transcriber(monkeypatch)._model_for("hi") == "small"

    def test_detection_and_english_stay_on_base(self, monkeypatch):
        t = self._transcriber(monkeypatch)
        assert t._model_for(None) == "base" and t._model_for("en") == "base"
        assert t._model_for("de") == "base"


class TestInputDevice:
    DEVICES = [
        {"name": "JBL Quantum Stream Talk", "max_input_channels": 0},
        {"name": "SRS-XB30", "max_input_channels": 1},
        {"name": "JBL Quantum Stream Talk", "max_input_channels": 1},
    ]

    def test_matches_an_input_device_by_name_prefix_ignoring_case(self):
        assert resolve_input_device("jbl quantum", self.DEVICES) == 2

    def test_output_only_devices_are_skipped(self):
        assert resolve_input_device("JBL", self.DEVICES[:1]) is None

    def test_empty_name_means_the_system_default(self):
        assert resolve_input_device("", self.DEVICES) is None

    def test_no_match_falls_back_to_the_system_default(self):
        assert resolve_input_device("Shure MV7", self.DEVICES) is None
