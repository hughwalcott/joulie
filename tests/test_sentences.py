import string

from joulie.sentences import (
    CHUNK_MAX_WORDS,
    FIRST_CHUNK_MAX_WORDS,
    MIN_FIRST_CHUNK_WORDS,
    RAMP_CHUNK_MAX_WORDS,
    split_sentences,
    split_speakable,
    spoken_words,
)


def filler(n: int) -> list[str]:
    """n distinct alphabetic words. Deliberately digit-free so word count and
    spoken_words() agree and the budget assertions stay readable."""
    letters = string.ascii_lowercase
    return [f"{letters[i // 26]}{letters[i % 26]}" for i in range(n)]


def feed(text: str, spoken: int = 0):
    """Run the whole text through split_speakable in one go, then flush, the way
    say_stream's accumulate() does at end-of-stream."""
    chunks, remainder = split_speakable(text, spoken=spoken)
    texts = [c.text for c in chunks]
    if remainder.strip():
        texts.append(remainder.strip())
    return texts, chunks


class TestSplitSentences:
    """Behaviour must be unchanged — _render_greeting still depends on it."""

    def test_splits_on_terminators(self):
        assert split_sentences("One. Two! Three? ") == (
            ["One.", "Two!", "Three?"], "")

    def test_returns_unterminated_remainder(self):
        assert split_sentences("Done. Not yet") == (["Done."], "Not yet")

    def test_ignores_abbreviations(self):
        sentences, _ = split_sentences("Dr. Smith called. Yes.")
        assert sentences == ["Dr. Smith called.", "Yes."]

    def test_ignores_decimals_and_currency(self):
        sentences, _ = split_sentences("A 2.5 kW unit costs $3.70 daily. Right.")
        assert sentences == ["A 2.5 kW unit costs $3.70 daily.", "Right."]


class TestFirstChunk:
    def test_breaks_at_clause_before_sentence_ends(self):
        text = ("Heat pumps are far more efficient than gas, which means your "
                "power bill drops noticeably over a whole year")
        chunks, remainder = split_speakable(text, spoken=0)
        assert [c.text for c in chunks] == ["Heat pumps are far more efficient than gas,"]
        assert chunks[0].boundary == "clause"
        assert remainder.strip().startswith("which means")

    def test_waits_when_nothing_speakable_yet(self):
        chunks, remainder = split_speakable("Heat pumps", spoken=0)
        assert chunks == []
        assert remainder == "Heat pumps"

    def test_does_not_break_below_the_floor(self):
        # "Yes," is only one word — breaking there would hand XTTS a fragment.
        chunks, _ = split_speakable("Yes, heat pumps are the efficient option here", spoken=0)
        assert all(spoken_words(c.text) >= MIN_FIRST_CHUNK_WORDS for c in chunks)

    def test_opening_clause_must_cover_the_next_chunks_synthesis(self):
        # A 4-word opener yields ~2.1s of audio while the chunk behind it takes
        # ~2.7s to synthesise, so playback runs dry. The floor pushes past it.
        text = ("According to Rewiring Aotearoa, homes using gas appliances could save "
                "around a thousand dollars, which is worth checking")
        # The 4-word opener is below the floor, so the chunker waits for the
        # second clause boundary rather than emitting it.
        assert split_speakable("According to Rewiring Aotearoa, homes", spoken=0)[0] == []
        chunks, _ = split_speakable(text, spoken=0)
        assert chunks[0].text.startswith("According to Rewiring Aotearoa, homes")
        assert spoken_words(chunks[0].text) >= MIN_FIRST_CHUNK_WORDS

    def test_hard_breaks_when_no_clause_in_budget(self):
        words = filler(40)
        chunks, remainder = split_speakable(" ".join(words), spoken=0)
        assert chunks[0].text.split() == words[:FIRST_CHUNK_MAX_WORDS]
        assert remainder.strip().startswith(words[FIRST_CHUNK_MAX_WORDS])

    def test_caps_a_long_opening_sentence(self):
        chunks, _ = split_speakable(" ".join(filler(40)) + ".", spoken=0)
        assert len(chunks[0].text.split()) == FIRST_CHUNK_MAX_WORDS

    def test_short_opening_sentence_passes_through(self):
        text = "Heat pumps are about three times more efficient than gas heating."
        chunks, _ = split_speakable(text, spoken=0)
        assert [c.text for c in chunks] == [text]
        assert chunks[0].boundary == "sentence"


class TestLaterChunks:
    def test_prefers_whole_sentences(self):
        text = "Heat pumps run on electricity. Gas boilers burn fossil fuel. "
        chunks, remainder = split_speakable(text, spoken=1)
        assert [c.text for c in chunks] == [
            "Heat pumps run on electricity.",
            "Gas boilers burn fossil fuel.",
        ]
        assert all(c.boundary == "sentence" for c in chunks)
        assert remainder.strip() == ""

    def test_splits_an_over_budget_sentence(self):
        chunks, _ = split_speakable(" ".join(filler(60)) + ".", spoken=1)
        assert all(len(c.text.split()) <= CHUNK_MAX_WORDS for c in chunks)
        # Only the final piece closes the sentence.
        assert [c.boundary for c in chunks] == ["clause"] * (len(chunks) - 1) + ["sentence"]

    def test_budget_ramps_so_a_short_chunk_is_not_followed_by_a_huge_one(self):
        # Playback of chunk N has to cover synthesis of chunk N+1; without the
        # ramp the output stream starved for over a second after chunk 1.
        long_sentence = " ".join(filler(80)) + "."
        widths = [
            len(split_speakable(long_sentence, spoken=n)[0][0].text.split())
            for n in range(3)
        ]
        assert widths == [FIRST_CHUNK_MAX_WORDS, RAMP_CHUNK_MAX_WORDS, CHUNK_MAX_WORDS]

    def test_budget_counts_currency_at_its_spoken_length(self):
        # This exact reply starved the output stream for 1.4s: 18 raw words, but
        # "$1,500"/"$4,500" each become ~5 spoken words, so 12s of audio.
        text = ("homes using gas appliances and petrol vehicles could save around "
                "$1,500 per year or around $4,500 per year with a loan.")
        assert spoken_words(text) > CHUNK_MAX_WORDS
        chunks, _ = split_speakable(text, spoken=1)
        assert len(chunks) > 1
        assert all(spoken_words(c.text) <= CHUNK_MAX_WORDS for c in chunks)

    def test_reassembles_to_the_original_words(self):
        text = ("The Electricity Authority says most households save money, though "
                "the exact figure depends on your usage; check your bill first. Then "
                "compare plans.")
        chunks, remainder = split_speakable(text, spoken=1)
        rebuilt = " ".join(c.text for c in chunks) + " " + remainder
        assert rebuilt.split() == text.split()


class TestFragmentHandling:
    def test_merges_a_short_sentence_forward(self):
        chunks, _ = split_speakable("Yes. Heat pumps are the efficient choice here. ")
        assert [c.text for c in chunks] == ["Yes. Heat pumps are the efficient choice here."]

    def test_holds_a_short_trailing_sentence_for_more_text(self):
        # "Sure." must not be synthesised alone — it goes back on the buffer.
        chunks, remainder = split_speakable("Sure. ")
        assert chunks == []
        assert remainder.strip() == "Sure."

    def test_a_held_fragment_merges_with_what_arrives_next(self):
        _, remainder = split_speakable("Sure. ")
        chunks, _ = split_speakable(remainder + "Heat pumps are the efficient choice. ")
        assert [c.text for c in chunks] == ["Sure. Heat pumps are the efficient choice."]

    def test_flush_still_speaks_a_lone_fragment(self):
        # Nothing follows, so accumulate()'s end-of-stream flush must say it.
        texts, _ = feed("Sure. ")
        assert texts == ["Sure."]


class TestStreaming:
    def test_token_by_token_matches_the_input(self):
        text = ("Heat pumps are efficient, and they cost less to run over a year. "
                "The Electricity Authority publishes the figures each season.")
        buf = ""
        spoken: list[str] = []
        for token in text.split(" "):
            buf += token + " "
            chunks, buf = split_speakable(buf, spoken=len(spoken))
            spoken.extend(c.text for c in chunks)
        if buf.strip():
            spoken.append(buf.strip())
        assert " ".join(spoken).split() == text.split()

    def test_first_chunk_is_short_enough_to_be_fast(self):
        text = ("According to the Electricity Authority, most New Zealand households "
                "could save several hundred dollars a year by switching.")
        buf = ""
        first = None
        for token in text.split(" "):
            buf += token + " "
            chunks, buf = split_speakable(buf, spoken=0)
            if chunks:
                first = chunks[0]
                break
        assert first is not None
        # ~0.65s + 0.10s/word on M4 Pro, so this is the time-to-first-speech dial.
        assert len(first.text.split()) <= FIRST_CHUNK_MAX_WORDS
