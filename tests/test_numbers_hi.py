from joulie.numbers_hi import expand_numbers, number_words


class TestNumberWords:
    def test_the_irregular_below_hundred_table(self):
        assert [number_words(n) for n in (0, 5, 19, 29, 45, 79, 99)] == [
            "शून्य", "पाँच", "उन्नीस", "उनतीस", "पैंतालीस", "उन्यासी", "निन्यानवे"]

    def test_hundreds_and_thousands(self):
        assert number_words(105) == "एक सौ पाँच"
        assert number_words(1500) == "एक हज़ार पाँच सौ"

    def test_years(self):
        assert number_words(2024) == "दो हज़ार चौबीस"

    def test_indian_grouping(self):
        assert number_words(150000) == "एक लाख पचास हज़ार"
        assert number_words(12500000) == "एक करोड़ पच्चीस लाख"


class TestExpand:
    def test_dollars(self):
        assert expand_numbers("$1,500") == "एक हज़ार पाँच सौ डॉलर"

    def test_percent(self):
        assert expand_numbers("45%") == "पैंतालीस प्रतिशत"

    def test_decimals_are_read_digit_by_digit(self):
        assert expand_numbers("6.5") == "छह दशमलव पाँच"

    def test_devanagari_digits(self):
        assert expand_numbers("२०२४ में") == "दो हज़ार चौबीस में"

    def test_indian_comma_grouping(self):
        assert expand_numbers("1,50,000") == "एक लाख पचास हज़ार"
