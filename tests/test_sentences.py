import string

from joulie.sentences import (
    CHUNK_MAX_WORDS,
    CHUNK_WORD_BUDGETS,
    CONTENDED_RTF,
    FIRST_CHUNK_MAX_WORDS,
    MIN_FIRST_CHUNK_WORDS,
    RAMP_CHUNK_MAX_WORDS,
    split_sentences,
    split_speakable,
    split_to_budget,
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
            for n in range(len(CHUNK_WORD_BUDGETS))
        ]
        assert widths == list(CHUNK_WORD_BUDGETS)

    def test_the_ramp_never_steps_faster_than_synthesis_can_keep_up(self):
        """The non-starvation condition, as an invariant rather than a literal
        table: chunk k+1 must synthesise in less time than chunk k takes to play,
        so W(k+1) <= W(k) / rtf. Solved against the CONTENDED rtf, because the
        opening chunks are always synthesised while Ollama is still decoding —
        session 20260916T225408 measured 0.759 mean there against 0.406 once the
        stream finished. The previous 14/18/25 ramp stepped 1.29x and 1.39x
        against a 1.25x ceiling because it was fitted with no Ollama running."""
        for earlier, later in zip(CHUNK_WORD_BUDGETS, CHUNK_WORD_BUDGETS[1:]):
            assert later / earlier <= 1 / CONTENDED_RTF + 1e-9, (
                f"{earlier} -> {later} words outruns synthesis at RTF {CONTENDED_RTF}"
            )

    def test_the_opening_window_is_wide_enough_for_a_clause_break(self):
        """MIN_FIRST_CHUNK_WORDS and the opening budget bracket chunk 1. If they
        are adjacent there is nowhere for a clause boundary to land and every
        first chunk becomes a mid-clause word-gap cut."""
        assert CHUNK_WORD_BUDGETS[0] - MIN_FIRST_CHUNK_WORDS >= 2

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

    def test_a_short_opener_does_not_blow_the_first_chunk_budget(self):
        """The 6.12s outlier in session 20260916T225408 turn 2. A sub-floor
        opening sentence used to be merged into the sentence behind it and
        shipped unchecked at 19-21 spoken words, more than twice the budget —
        7.8-8.6s of audio, 6.2-6.9s to synthesise while Ollama was decoding.
        The body here is long enough that the merged result must be re-split;
        test_merges_a_short_sentence_forward only passes because its body is
        short enough to stay under budget either way."""
        body = ("A heat pump hot water cylinder uses roughly a third of the "
                "electricity of a standard resistive element, so you'd save "
                "about $600 a year.")
        for opener in ("Yes.", "Great question.", "Short answer: yes."):
            texts, _ = feed(f"{opener} {body}")
            assert spoken_words(texts[0]) <= FIRST_CHUNK_MAX_WORDS, (
                f"opener {opener!r} produced a {spoken_words(texts[0])}-word first chunk"
            )
            assert texts[0].startswith(opener), "the opener must still be spoken first"

    def test_every_chunk_respects_the_budget_for_its_position(self):
        body = ("A heat pump hot water cylinder uses roughly a third of the "
                "electricity of a standard resistive element, so you'd save "
                "about $600 a year on a typical Auckland hot water load.")
        for opener in ("", "Yes.", "Great question."):
            texts, _ = feed(f"{opener} {body}".strip())
            for i, text in enumerate(texts):
                budget = CHUNK_WORD_BUDGETS[min(i, len(CHUNK_WORD_BUDGETS) - 1)]
                # A chunk may run up to _MIN_CHUNK_WORDS over budget rather than
                # leave a sub-floor tail behind it; see _split_to_budget.
                assert spoken_words(text) <= budget + 4, (
                    f"chunk {i + 1} of {opener!r} is {spoken_words(text)}w against a {budget}w budget"
                )

    def test_a_short_sentence_is_never_split_into_a_babbling_tail(self):
        """XTTS babbles on very short inputs. Cutting an 11-word sentence at the
        opening budget would leave "gas heating." to be synthesised alone, so a
        unit that cannot be split cleanly is spoken whole instead."""
        text = "Heat pumps are about three times more efficient than gas heating."
        texts, _ = feed(text)
        assert texts == [text]

    def test_a_held_fragment_merges_with_what_arrives_next(self):
        _, remainder = split_speakable("Sure. ")
        chunks, _ = split_speakable(remainder + "Heat pumps are the efficient choice. ")
        assert [c.text for c in chunks] == ["Sure. Heat pumps are the efficient choice."]

    def test_flush_still_speaks_a_lone_fragment(self):
        # Nothing follows, so accumulate()'s end-of-stream flush must say it.
        texts, _ = feed("Sure. ")
        assert texts == ["Sure."]


class TestSentenceBoundariesOnNumbers:
    """SYSTEM_PROMPT asks for a year on every statistic, so answers end
    sentences on numbers constantly. Treating every trailing integer as a
    decimal meant those boundaries were never found and the text piled up into
    one oversized end-of-stream chunk."""

    def test_a_sentence_ending_in_a_year_is_a_boundary(self):
        sentences, _ = split_sentences(
            "Gas supply dropped compared to 2023. Operators expect 85 PJ in 2026."
        )
        assert sentences == [
            "Gas supply dropped compared to 2023.",
            "Operators expect 85 PJ in 2026.",
        ]

    def test_decimals_are_still_not_boundaries(self):
        # _END_RE needs whitespace or end-of-string after the dot, so "2.5"
        # cannot reach the guard at all — this pins that it stays that way.
        sentences, _ = split_sentences("A 2.5 kW unit costs $3.70 daily. Right.")
        assert sentences == ["A 2.5 kW unit costs $3.70 daily.", "Right."]

    def test_list_numbering_is_still_not_a_boundary(self):
        sentences, _ = split_sentences("1. Find the ICP number. ")
        assert sentences == ["1. Find the ICP number."]


class TestEndOfStreamTail:
    """say_stream's flush queues whatever is left in the buffer. It used to do
    that as one chunk at any length — an answer in the eval corpus produced a
    52-word tail, ~21s of audio in a single synthesis."""

    def test_a_long_tail_is_budgeted_not_shipped_whole(self):
        tail = " ".join(filler(60))
        chunks = split_to_budget(tail, spoken=0)
        assert len(chunks) > 1
        for i, c in enumerate(chunks):
            budget = CHUNK_WORD_BUDGETS[min(i, len(CHUNK_WORD_BUDGETS) - 1)]
            assert spoken_words(c.text) <= budget + 4

    def test_the_tail_continues_the_ramp_rather_than_restarting_it(self):
        tail = " ".join(filler(60))
        assert (len(split_to_budget(tail, spoken=4)[0].text.split())
                > len(split_to_budget(tail, spoken=0)[0].text.split()))

    def test_a_short_tail_is_left_alone(self):
        chunks = split_to_budget("That is the whole answer.", spoken=2)
        assert [c.text for c in chunks] == ["That is the whole answer."]
        assert chunks[0].boundary == "sentence"

    def test_an_empty_tail_produces_nothing(self):
        assert split_to_budget("   ", spoken=1) == []


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
