import re
from dataclasses import dataclass

_ABBREVS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st",
    "nz", "eg", "ie", "etc", "approx", "dept", "govt",
    "inc", "ltd", "vs", "no",
})

# Matches sentence-ending punctuation followed by whitespace or end-of-string.
_END_RE = re.compile(r'([.?!]+["\']?)(\s+|$)')

# Points inside a sentence where a break still sounds natural: a comma, colon
# or semicolon, or a spaced dash. Breaking anywhere else leaves XTTS with a
# falling terminal contour mid-clause, which is heard as a cut-off word.
_CLAUSE_RE = re.compile(r'[,;:](?=\s)|\s[—–]\s|\s-\s')

# XTTS produces babble on very short inputs, so a chunk below this floor is
# folded into its neighbour rather than synthesised alone.
_MIN_CHUNK_WORDS = 4
_MIN_CHUNK_CHARS = 20

# The opening chunk gets a higher floor than the rest. Playback of chunk N is the
# only thing covering synthesis of chunk N+1, and there is no buffer yet at the
# start: a four-word opener ("According to Rewiring Aotearoa,") yields ~2.1s of
# audio against ~2.7s to synthesise what follows, which stalls audibly.
MIN_FIRST_CHUNK_WORDS = 8

# XTTS's text cleaner expands numbers and currency before synthesis, so "$1,500"
# is five spoken words, not one. Budgeting on raw word count let an 18-word chunk
# run to 12s of audio and starve the output stream mid-answer.
_NUMBER_RE = re.compile(r'\d[\d,]*(?:\.\d+)?')
_SPOKEN_UNIT_RE = re.compile(r'[$%]')

# XTTS costs roughly 0.65s + 0.10s per word (measured on M4 Pro / MPS), so these
# budgets are latency dials: ~14 words is ~2s of synthesis, ~25 words is ~3.2s.
# They ramp rather than jumping straight to the full budget because playback of
# one chunk has to cover synthesis of the next — a short opening chunk followed
# by a full-size one starves the output stream and leaves an audible gap.
FIRST_CHUNK_MAX_WORDS = 14
RAMP_CHUNK_MAX_WORDS = 18
CHUNK_MAX_WORDS = 25


@dataclass(frozen=True)
class Chunk:
    """A span of text ready for TTS. `boundary` is "sentence" when the chunk
    ends an utterance and "clause" when it is a mid-sentence split — callers use
    it to pick how much silence to leave after the audio."""
    text: str
    boundary: str


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


def split_speakable(text: str, spoken: int = 0) -> tuple[list[Chunk], str]:
    """Split streamed LLM text into chunks worth handing to TTS.

    `spoken` is how many chunks this turn has already produced; it selects the
    word budget, so the caller just keeps a running count.

    Same streaming contract as split_sentences — the caller prepends the returned
    remainder to the next arriving text. The difference is that the FIRST chunk of
    a turn is cut at the earliest clause boundary rather than waiting for a whole
    sentence: synthesis cost is linear in chunk length, so a 30-word opening
    sentence costs ~3.7s before any audio plays while its opening clause costs
    ~0.8s. Later chunks prefer whole sentences, where prosody matters more than
    the latency we have already won.
    """
    sentences, remainder = split_sentences(text)
    units: list[tuple[str, str]] = [(s, "sentence") for s in sentences]

    if spoken == 0 and not units:
        pos = _clause_split_pos(remainder, _budget(0), _floor(0))
        if pos:
            units.append((remainder[:pos].strip(), "clause"))
            remainder = remainder[pos:]

    chunks: list[Chunk] = []
    for body, boundary in units:
        pieces = _split_to_budget(body, spoken + len(chunks))
        chunks.extend(Chunk(p, "clause") for p in pieces[:-1])
        chunks.append(Chunk(pieces[-1], boundary))

    chunks = _merge_short(chunks)

    # A trailing sub-floor chunk goes back on the buffer so it can merge with
    # whatever arrives next; the caller's end-of-stream flush speaks it if
    # nothing else follows.
    if chunks and _too_short(chunks[-1].text):
        remainder = chunks[-1].text + " " + remainder.lstrip()
        chunks = chunks[:-1]

    return chunks, remainder


def _budget(index: int) -> int:
    if index == 0:
        return FIRST_CHUNK_MAX_WORDS
    if index == 1:
        return RAMP_CHUNK_MAX_WORDS
    return CHUNK_MAX_WORDS


def _floor(index: int) -> int:
    return MIN_FIRST_CHUNK_WORDS if index == 0 else _MIN_CHUNK_WORDS


def spoken_words(text: str) -> int:
    """Word count as XTTS will actually say it, counting the expansion of numbers
    and currency. Digits carry roughly one spoken word each beyond the first, and
    a $ or % becomes a word of its own."""
    extra = sum(
        max(0, sum(c.isdigit() for c in m.group()) - 1)
        for m in _NUMBER_RE.finditer(text)
    )
    extra += len(_SPOKEN_UNIT_RE.findall(text))
    return len(text.split()) + extra


def _too_short(text: str) -> bool:
    return spoken_words(text) < _MIN_CHUNK_WORDS or len(text) < _MIN_CHUNK_CHARS


def _clause_split_pos(text: str, max_words: int, min_words: int) -> int:
    """Index just past the earliest usable clause break in text, or 0 if there
    isn't one yet and the text is still short enough to wait for more."""
    for m in _CLAUSE_RE.finditer(text):
        head = text[:m.end()]
        if spoken_words(head) < min_words or len(head.strip()) < _MIN_CHUNK_CHARS:
            continue
        if spoken_words(head) <= max_words:
            return m.end()
        break

    # Over budget with no clause break in reach — cut on a word gap rather than
    # stall. Prosody suffers slightly; waiting suffers more.
    matches = list(re.finditer(r'\S+', text))
    count = 0
    for i, m in enumerate(matches):
        count += spoken_words(m.group())
        if count >= max_words and i < len(matches) - 1:
            return m.end()
    return 0


def _split_to_budget(text: str, index: int) -> list[str]:
    pieces: list[str] = []
    rest = text.strip()
    while True:
        at = index + len(pieces)
        budget = _budget(at)
        if spoken_words(rest) <= budget:
            break
        pos = _clause_split_pos(rest, budget, _floor(at))
        head = rest[:pos].strip() if pos else ""
        if not head:
            break
        pieces.append(head)
        rest = rest[pos:].strip()
    if rest:
        pieces.append(rest)
    return pieces or [text.strip()]


def _merge_short(chunks: list[Chunk]) -> list[Chunk]:
    merged: list[Chunk] = []
    for c in chunks:
        if merged and _too_short(merged[-1].text):
            prev = merged.pop()
            merged.append(Chunk(f"{prev.text} {c.text}".strip(), c.boundary))
        else:
            merged.append(c)
    return merged
