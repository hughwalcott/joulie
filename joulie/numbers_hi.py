"""Hindi numbers as words, for XTTS's Hindi voice.

XTTS expands digits for every language it voices except Hindi (its Hindi text
path is only basic_cleaners), and num2words has no Hindi, so "₹" aside, every
price and year in a Hindi answer would reach the voice as bare digits. Hindi
numbers below a hundred are each their own word, not a regular tens-plus-units
compound, hence the full table; above that the Indian grouping applies — सौ
(hundred), हज़ार (thousand), लाख (hundred thousand), करोड़ (ten million).

Needs a native speaker's check alongside the rest of the Hindi strings.
"""

import re

_BELOW_100 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ "
    "दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
    "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस "
    "तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस "
    "चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास "
    "पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ "
    "साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर "
    "सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी "
    "अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी "
    "नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()
assert len(_BELOW_100) == 100

_GROUPS = ((10**7, "करोड़"), (10**5, "लाख"), (1000, "हज़ार"), (100, "सौ"))

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_CURRENCY_RE = re.compile(rf"\$\s?({_NUMBER})")
_PERCENT_RE = re.compile(rf"({_NUMBER})\s?%")
_NUMBER_RE = re.compile(_NUMBER)


def number_words(n: int) -> str:
    if n < 100:
        return _BELOW_100[n]
    parts = []
    for value, name in _GROUPS:
        if n >= value:
            count, n = divmod(n, value)
            parts.append(f"{number_words(count)} {name}")
    if n:
        parts.append(_BELOW_100[n])
    return " ".join(parts)


def _spoken(number: str) -> str:
    whole, _, fraction = number.replace(",", "").partition(".")
    words = number_words(int(whole))
    if fraction:
        # Digits after the point are read one by one, as in "छह दशमलव पाँच".
        words += " दशमलव " + " ".join(_BELOW_100[int(d)] for d in fraction)
    return words


def expand_numbers(text: str) -> str:
    """Spell out digits, dollar amounts and percentages in Hindi words."""
    text = text.translate(_DEVANAGARI_DIGITS)
    text = _CURRENCY_RE.sub(lambda m: f"{_spoken(m.group(1))} डॉलर", text)
    text = _PERCENT_RE.sub(lambda m: f"{_spoken(m.group(1))} प्रतिशत", text)
    return _NUMBER_RE.sub(lambda m: _spoken(m.group()), text)
