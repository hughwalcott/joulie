import re

_ABBREVS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st",
    "nz", "eg", "ie", "etc", "approx", "dept", "govt",
    "inc", "ltd", "vs", "no",
})

# Matches sentence-ending punctuation followed by whitespace or end-of-string.
_END_RE = re.compile(r'([.?!]+["\']?)(\s+|$)')


def split_sentences(text: str) -> tuple[list[str], str]:
    """Split text into complete sentences. Returns (sentences, remainder).

    remainder is an unterminated partial sentence — the caller should
    prepend it to the next incoming text chunk before calling again.
    """
    sentences: list[str] = []
    pos = 0

    for m in _END_RE.finditer(text):
        punc_start = m.start(1)

        # Get the word token immediately before the punctuation.
        preceding = text[:punc_start].rstrip()
        word_match = re.search(r'(\w+)$', preceding)
        preceding_word = word_match.group(1).lower() if word_match else ""

        dot_only = set(m.group(1)) == {"."}
        if dot_only:
            if preceding_word in _ABBREVS:
                continue
            # Single letter initialisms: "A. Smith", "e.g."
            if re.fullmatch(r'[a-z]', preceding_word):
                continue
            # Decimal numbers: "2.5 kW", "$3.70 per kWh"
            if re.fullmatch(r'\d+', preceding_word):
                continue

        sentence = text[pos:m.end()].strip()
        if sentence:
            sentences.append(sentence)
        pos = m.end()

    return sentences, text[pos:]
