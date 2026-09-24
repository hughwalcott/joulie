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

# XTTS speaks at ~2.45 spoken words per second, so a chunk's word count fixes
# both how long it takes to synthesise and how much playback time it buys the
# chunk behind it. The budgets ramp rather than jumping straight to the full
# size because playback of one chunk is the only thing covering synthesis of the
# next: chunk k+1 must synthesise in less than chunk k takes to play, which is
#
#     rtf * W(k+1) / 2.45  <=  W(k) / 2.45      ->      W(k+1) <= W(k) / rtf
#
# The rtf to solve that against is the CONTENDED one, not XTTS's steady state.
# Session 20260916T225408 measured every chunk synthesised while Ollama was
# still decoding at RTF 0.759 mean / 0.804 median, against 0.406 / 0.371 for
# chunks synthesised after the stream finished — XTTS and Ollama contend for the
# same Metal device, and the opening chunks always land inside that window.
# The previous 14/18/25 ramp was fitted by isolate_xtts.py with no Ollama in the
# process, so it budgeted the 0.36 steady state and stepped 1.29x and 1.39x
# where the contended rate only allows 1.25x. It also made chunk 1 ~5.7s of
# audio costing ~4.6s to synthesise — 40% of the 10.9s to first audio.
# See logs/latency-analysis.md, "Third pass".
CONTENDED_RTF = 0.80

# Each step stays within the 1.25x the contended rate allows. The opening budget
# is not pushed below 11 on purpose: MIN_FIRST_CHUNK_WORDS is 8, and a [8, 9]
# window is too narrow for a clause break to ever land inside, which would make
# every first chunk a mid-clause word-gap cut. [8, 11] leaves room to find one.
# Index past the end uses the last entry, the steady-state budget.
CHUNK_WORD_BUDGETS = (11, 13, 16, 20, 25)

# Kept as names because tests and callers read them; they are the ends of the ramp.
FIRST_CHUNK_MAX_WORDS = CHUNK_WORD_BUDGETS[0]
RAMP_CHUNK_MAX_WORDS = CHUNK_WORD_BUDGETS[1]
CHUNK_MAX_WORDS = CHUNK_WORD_BUDGETS[-1]


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
            # List numbering: "1. Check your meter". A DECIMAL cannot reach
            # here — _END_RE requires whitespace or end-of-string after the dot,
            # and "2.5" has a digit there — so this guard only ever sees an
            # integer that ends a sentence. Matching every integer meant a
            # sentence closing on a year or a statistic ("…compared to 2023.")
            # was never a boundary, and SYSTEM_PROMPT asks for a year on every
            # statistic: 17% of the answers in evals/results-tuning-a-baseline
            # .json were affected, and the un-split text accumulated into a
            # single end-of-stream chunk — one measured 52 spoken words, ~21s of
            # audio. Two digits is enough for list numbering and leaves years
            # and quantities alone.
            if re.fullmatch(r'\d{1,2}', preceding_word):
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

    # Fold sub-floor units forward BEFORE budgeting, not after. A reply opening
    # with a short complete sentence ("Yes." / "Great question.") produces a unit
    # that cannot be spoken alone, and budgeting first would hand the sentence
    # behind it the index-1 budget on the assumption that the stub survives as
    # chunk 1 — then merge the two and ship 19-21 spoken words as chunk 1, more
    # than twice the budget. Merging first means every unit is budgeted against
    # the index it will actually be spoken at.
    units = _merge_short_units(units)

    chunks: list[Chunk] = []
    for body, boundary in units:
        pieces = _split_to_budget(body, spoken + len(chunks))
        chunks.extend(Chunk(p, "clause") for p in pieces[:-1])
        chunks.append(Chunk(pieces[-1], boundary))

    # Catches the one case unit-merging cannot: a sub-floor tail left by
    # _split_to_budget when a unit does not divide evenly into its budgets.
    chunks = _merge_short(chunks, spoken)

    # A trailing sub-floor chunk goes back on the buffer so it can merge with
    # whatever arrives next; the caller's end-of-stream flush speaks it if
    # nothing else follows.
    if chunks and _too_short(chunks[-1].text):
        remainder = chunks[-1].text + " " + remainder.lstrip()
        chunks = chunks[:-1]

    return chunks, remainder


def split_to_budget(text: str, spoken: int = 0) -> list[Chunk]:
    """Cut a span that is already known to be complete into budgeted chunks.

    The streaming path reaches chunks through split_speakable, which only emits
    text it can close off at a sentence or clause. say_stream's end-of-stream
    flush has no such text — it has whatever is left in the buffer — and used to
    queue all of it as a single chunk whatever its length. This gives that tail
    the same budget as everything else. The final piece carries a "sentence"
    boundary because it ends the utterance.
    """
    body = text.strip()
    if not body:
        return []
    pieces = _split_to_budget(body, spoken)
    chunks = [Chunk(p, "clause") for p in pieces[:-1]]
    chunks.append(Chunk(pieces[-1], "sentence"))
    return _merge_short(chunks, spoken)


def _budget(index: int) -> int:
    return CHUNK_WORD_BUDGETS[min(index, len(CHUNK_WORD_BUDGETS) - 1)]


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
        # Stop while what is left would not survive on its own. Cutting a
        # 12-15 word sentence against the opening budget leaves a two-word tail,
        # and XTTS babbles on inputs that short — the very thing
        # _MIN_CHUNK_WORDS exists to prevent. Speaking such a sentence whole
        # costs at most _MIN_CHUNK_WORDS over budget and keeps a real terminal
        # contour, which beats both the babble and a mid-clause break.
        if spoken_words(rest) <= budget + _MIN_CHUNK_WORDS:
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


def _merge_short_units(units: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Fold a unit too short to speak into the unit behind it, keeping the later
    unit's boundary. Runs on units rather than budgeted chunks so the merge
    cannot change which budget a chunk is measured against."""
    merged: list[tuple[str, str]] = []
    for body, boundary in units:
        if merged and _too_short(merged[-1][0]):
            prev_body, _ = merged.pop()
            merged.append((f"{prev_body} {body}".strip(), boundary))
        else:
            merged.append((body, boundary))
    return merged


def _merge_short(chunks: list[Chunk], spoken: int = 0) -> list[Chunk]:
    """Fold sub-floor chunks into the one behind them, then re-apply the word
    budget to whatever that produced.

    _merge_short_units already handles the common case upstream, on units. This
    is the net for what it cannot reach: a sub-floor tail left behind when a
    unit does not divide evenly into its budgets. The re-budget matters either
    way — a merge that does not re-check produces exactly the bug this pair was
    written for, chunk 1 shipping at 19-21 spoken words against an 11-word
    budget (6.2-6.9s of synthesis at the contended RTF, the 6.12s outlier in
    session 20260916T225408 turn 2). Merging is right, because XTTS babbles on
    two-word inputs; merging without re-budgeting is not.
    """
    merged: list[Chunk] = []
    for c in chunks:
        if merged and _too_short(merged[-1].text):
            prev = merged.pop()
            merged.append(Chunk(f"{prev.text} {c.text}".strip(), c.boundary))
        else:
            merged.append(c)

    rebudgeted: list[Chunk] = []
    for c in merged:
        pieces = _split_to_budget(c.text, spoken + len(rebudgeted))
        rebudgeted.extend(Chunk(p, "clause") for p in pieces[:-1])
        rebudgeted.append(Chunk(pieces[-1], c.boundary))
    return rebudgeted
