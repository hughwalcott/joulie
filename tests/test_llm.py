"""Agent._build_messages is exercised directly (no Ollama call) since it's the
part that decides prompt shape — the actual request/response is a thin
requests.post wrapper not worth mocking here."""

import time

from joulie import config
from joulie.llm import Agent, _eval_stats


class FakeRetriever:
    def __init__(self, chunks=None):
        self.chunks = chunks or []

    def retrieve(self, text):
        return self.chunks

    def summarise_sources(self, chunks):
        return tuple(c["publisher_short"] for c in chunks)

    def format_context(self, chunks):
        return "\n".join(c["text"] for c in chunks)


def make_agent(max_history_turns=5, trim_to=2, retriever=None, num_ctx=6144,
               num_predict=0, rag_placement="question"):
    return Agent(model="test-model", url="http://x", system_prompt="SYS",
                 retriever=retriever, max_history_turns=max_history_turns,
                 trim_to=trim_to, num_ctx=num_ctx, num_predict=num_predict,
                 rag_placement=rag_placement)


def user_texts(messages):
    return [m["content"] for m in messages if m["role"] == "user"]


def finish_turn(agent, user_text, reply_text):
    """Mirrors what stream()/reply() do without a network call."""
    messages, current_turn = agent._build_messages(user_text)
    current_turn.append({"role": "assistant", "content": reply_text})
    return messages


class TestBlockTrim:
    """History is cut back by a block, not by one turn per turn. The per-turn
    version shifted the prompt's leading tokens on every request, so Ollama
    could never reuse its cached prefix — see logs/latency-analysis.md."""

    def test_defaults_come_from_config(self):
        agent = Agent(model="test-model", url="http://x", system_prompt="SYS")
        assert agent.max_history_turns == config.LLM_MAX_HISTORY_TURNS
        assert agent.trim_to == config.LLM_HISTORY_TRIM_TO
        assert agent.num_ctx == config.LLM_NUM_CTX

    def test_history_is_untouched_until_it_exceeds_the_cap(self):
        agent = make_agent(max_history_turns=6, trim_to=3)
        for i in range(6):
            finish_turn(agent, f"q{i}", f"a{i}")
        # 6 completed turns is exactly the cap, so nothing has been dropped yet.
        messages, _ = agent._build_messages("q6")
        assert user_texts(messages) == [f"q{i}" for i in range(7)]
        assert agent.last_prompt_stats["history_trimmed"] is False

    def test_a_trim_cuts_back_to_trim_to_not_by_one(self):
        agent = make_agent(max_history_turns=6, trim_to=3)
        for i in range(7):
            finish_turn(agent, f"q{i}", f"a{i}")
        # 7 completed turns is over the cap of 6, so the next turn trims back to
        # the last 3 (q4, q5, q6) rather than merely dropping q0.
        messages, _ = agent._build_messages("q7")
        assert user_texts(messages) == ["q4", "q5", "q6", "q7"]
        assert agent.last_prompt_stats["history_trimmed"] is True

    def test_only_one_turn_per_block_pays_a_trim(self):
        agent = make_agent(max_history_turns=6, trim_to=3)
        trims = []
        for i in range(16):
            finish_turn(agent, f"q{i}", f"a{i}")
            trims.append(agent.last_prompt_stats["history_trimmed"])
        # Period is (max + 1 - trim_to) == 4: one re-prefill per four turns,
        # instead of one on every turn from turn 5 onward.
        assert trims.count(True) == 3
        trimmed_at = [i for i, t in enumerate(trims) if t]
        assert [b - a for a, b in zip(trimmed_at, trimmed_at[1:])] == [4, 4]

    def test_history_stays_between_trim_to_and_the_cap_once_running(self):
        # The floor is what the depth/latency trade is actually made on: at the
        # bottom of a block the prompt holds trim_to prior turns, which at the
        # shipped 5/2 is one fewer than the old constant 3. The ceiling is what
        # num_ctx has to be sized against.
        agent = make_agent(max_history_turns=5, trim_to=2)
        depths = []
        for i in range(20):
            finish_turn(agent, f"q{i}", f"a{i}")
            depths.append(agent.last_prompt_stats["history_turns"])
        steady = depths[3:]  # before turn 4 there simply aren't the turns to hold
        assert min(steady) == 3   # trim_to prior turns + the current one
        assert max(steady) == 6   # cap + the current one

    def test_trim_to_above_the_cap_is_clamped_so_a_trim_still_shrinks(self):
        # trim_to > max would leave history untouched and the cap unenforceable.
        agent = make_agent(max_history_turns=3, trim_to=99)
        assert agent.trim_to == 3
        for i in range(5):
            finish_turn(agent, f"q{i}", f"a{i}")
        assert agent.last_prompt_stats["history_turns"] <= 4

    def test_trim_to_zero_is_clamped_so_a_trim_never_wipes_history(self):
        agent = make_agent(max_history_turns=3, trim_to=0)
        assert agent.trim_to == 1
        for i in range(5):
            finish_turn(agent, f"q{i}", f"a{i}")
        messages, _ = agent._build_messages("q5")
        assert user_texts(messages)[0] != "q5"  # something older survived

    def test_trim_to_equal_to_the_cap_reproduces_the_old_per_turn_trim(self):
        # Kept reachable so the old behaviour can still be A/B'd against this one.
        agent = make_agent(max_history_turns=2, trim_to=2)
        for i in range(5):
            finish_turn(agent, f"q{i}", f"a{i}")
        messages, _ = agent._build_messages("q5")
        assert user_texts(messages) == ["q3", "q4", "q5"]

    def test_a_short_conversation_is_never_trimmed(self):
        agent = make_agent()
        finish_turn(agent, "q1", "a1")
        messages, _ = agent._build_messages("q2")
        assert user_texts(messages) == ["q1", "q2"]

    def test_zero_disables_trimming(self):
        agent = make_agent(max_history_turns=0)
        for i in range(10):
            finish_turn(agent, f"q{i}", f"a{i}")
        messages, _ = agent._build_messages("q10")
        assert len(user_texts(messages)) == 11

    def test_reset_clears_the_per_turn_timing_too(self):
        # end_session() resets between visitors; a stale timing would be
        # attributed to the next visitor's first turn.
        agent = make_agent()
        agent.last_post_ttft_seconds = 9.9
        agent.reset()
        assert agent.last_post_ttft_seconds == 0.0

    def test_reset_clears_trimmed_history_too(self):
        agent = make_agent(max_history_turns=2, trim_to=1)
        finish_turn(agent, "q1", "a1")
        agent.reset()
        messages, _ = agent._build_messages("q2")
        assert user_texts(messages) == ["q2"]


class TestPromptPrefixStability:
    """The whole point of the cap: once a turn is complete, its messages must
    never be rewritten — only ever dropped whole — so the system prompt +
    surviving turns form a stable, append-only prefix a KV cache can reuse."""

    def test_a_completed_turns_messages_are_never_mutated_by_a_later_turn(self):
        agent = make_agent(max_history_turns=3)
        messages_1 = finish_turn(agent, "q1", "a1")
        finish_turn(agent, "q2", "a2")
        messages_3, _ = agent._build_messages("q3")
        # The exact message objects from turn 1 must still be present, unchanged,
        # inside turn 3's request — a stable prefix, not a rebuilt one.
        assert messages_1[0] == messages_3[0]  # system prompt
        assert messages_1[1] in messages_3      # turn 1's own user message

    def test_new_prefix_extends_the_old_one_rather_than_replacing_it(self):
        agent = make_agent(max_history_turns=3)
        messages_1 = finish_turn(agent, "q1", "a1")
        messages_2, _ = agent._build_messages("q2")
        assert messages_2[:len(messages_1)] == messages_1

    def test_only_one_system_message_is_ever_sent(self):
        # Ollama collates EVERY role=system message into one block at the top of
        # the rendered prompt, so a per-turn context message lands in front of
        # all history and shifts it — the prefix then breaks on every turn, trim
        # or no trim. Verified with "_debug_render_only" on 0.32.1.
        retriever = FakeRetriever([{"publisher_short": "EECA", "text": "ctx-1"}])
        agent = make_agent(max_history_turns=3, retriever=retriever)
        finish_turn(agent, "q1", "a1")
        retriever.chunks = [{"publisher_short": "MBIE", "text": "ctx-2"}]
        messages, _ = agent._build_messages("q2")
        assert [m["role"] for m in messages].count("system") == 1
        assert messages[0]["content"] == "SYS"

    def test_context_rides_on_the_live_question_and_is_not_kept_in_history(self):
        retriever = FakeRetriever([{"publisher_short": "EECA", "text": "ctx-1"}])
        agent = make_agent(max_history_turns=3, retriever=retriever)
        finish_turn(agent, "q1", "a1")
        retriever.chunks = [{"publisher_short": "MBIE", "text": "ctx-2"}]
        messages, _ = agent._build_messages("q2")
        # This turn's context is on this turn's question...
        assert "ctx-2" in messages[-1]["content"]
        assert messages[-1]["content"].endswith("q2")
        # ...and last turn's is gone, though its question and answer remain.
        assert not any("ctx-1" in m["content"] for m in messages)
        assert [m["content"] for m in messages[1:3]] == ["q1", "a1"]

    def test_stripping_context_rewrites_only_the_previous_question(self):
        # The cost of not keeping context: turn 1's question is re-sent without
        # it, so the prefix diverges there rather than at the system prompt.
        # Everything before it is byte-identical and stays in the KV cache.
        retriever = FakeRetriever([{"publisher_short": "EECA", "text": "ctx-1"}])
        agent = make_agent(max_history_turns=3, retriever=retriever)
        messages_1 = finish_turn(agent, "q1", "a1")
        retriever.chunks = [{"publisher_short": "MBIE", "text": "ctx-2"}]
        messages_2, _ = agent._build_messages("q2")
        assert messages_2[:len(messages_1) - 1] == messages_1[:-1]

    def test_system_placement_restores_the_old_shape_for_ab_testing(self):
        retriever = FakeRetriever([{"publisher_short": "EECA", "text": "ctx-1"}])
        agent = make_agent(max_history_turns=3, retriever=retriever,
                           rag_placement="system")
        finish_turn(agent, "q1", "a1")
        retriever.chunks = [{"publisher_short": "MBIE", "text": "ctx-2"}]
        messages, _ = agent._build_messages("q2")
        assert [m["role"] for m in messages].count("system") == 3
        assert any("ctx-1" in m["content"] for m in messages)


class TestLastPromptStats:
    """Read by SessionCore after each turn to test whether latency tracks
    input size rather than turn position, once history is capped."""

    def test_prompt_chars_matches_the_messages_actually_sent(self):
        agent = make_agent(max_history_turns=3)
        messages, _ = agent._build_messages("q1")
        expected = sum(len(m["content"]) for m in messages)
        assert agent.last_prompt_stats["prompt_chars"] == expected

    def test_retrieval_is_timed_separately_from_the_llm(self):
        """llm_ttft_seconds is named for the LLM but runs from end of utterance,
        so it also carries retrieval. Recording retrieval on its own is what
        stops a component hiding inside a metric named for another one —
        logs/latency-analysis.md recommendation 6."""
        class SlowRetriever(FakeRetriever):
            def retrieve(self, text):
                time.sleep(0.05)
                return self.chunks

        retriever = SlowRetriever([{"publisher_short": "EECA", "text": "ctx"}])
        agent = make_agent(max_history_turns=3, retriever=retriever)
        agent._build_messages("q1")
        assert agent.last_prompt_stats["retrieval_seconds"] >= 0.05

    def test_retrieval_seconds_is_zero_with_no_retriever(self):
        agent = make_agent(max_history_turns=3, retriever=None)
        agent._build_messages("q1")
        assert agent.last_prompt_stats["retrieval_seconds"] == 0.0

    def test_zero_rag_stats_with_no_retriever(self):
        agent = make_agent(max_history_turns=3, retriever=None)
        agent._build_messages("q1")
        assert agent.last_prompt_stats["rag_chunk_count"] == 0
        assert agent.last_prompt_stats["rag_context_chars"] == 0

    def test_rag_stats_reflect_the_retrieved_chunks(self):
        retriever = FakeRetriever([
            {"publisher_short": "EECA", "text": "some context text"},
            {"publisher_short": "MBIE", "text": "more context"},
        ])
        agent = make_agent(max_history_turns=3, retriever=retriever)
        agent._build_messages("q1")
        stats = agent.last_prompt_stats
        assert stats["rag_chunk_count"] == 2
        assert stats["rag_context_chars"] == len("some context text\nmore context")

    def test_history_turns_reflects_the_cap_not_raw_turn_count(self):
        agent = make_agent(max_history_turns=2)
        for i in range(5):
            finish_turn(agent, f"q{i}", f"a{i}")
        agent._build_messages("q5")
        # 2 prior turns survive the cap, plus the one just built.
        assert agent.last_prompt_stats["history_turns"] == 3

    def test_reset_clears_prompt_stats(self):
        agent = make_agent(max_history_turns=3)
        agent._build_messages("q1")
        agent.reset()
        assert agent.last_prompt_stats == {}


class TestEvalStats:
    """Ollama's server-side token accounting, taken off the final chunk. This
    is the measurement that distinguishes a reused KV prefix from a full
    re-prefill — turn timings alone can't, which is why the turn-5 cliff took
    four sessions to pin down."""

    def test_reads_counts_and_converts_nanoseconds_to_seconds(self):
        stats = _eval_stats({
            "prompt_eval_count": 3382,
            "prompt_eval_duration": 17_000_000_000,
            "eval_count": 95,
            "eval_duration": 4_000_000_000,
        })
        assert stats["prompt_eval_count"] == 3382
        assert stats["prompt_eval_seconds"] == 17.0
        assert stats["eval_count"] == 95
        assert stats["eval_seconds"] == 4.0

    def test_derives_the_prefill_rate_that_is_comparable_across_prompt_sizes(self):
        cold = _eval_stats({"prompt_eval_count": 2255, "prompt_eval_duration": 10_480_000_000})
        warm = _eval_stats({"prompt_eval_count": 2251, "prompt_eval_duration": 4_410_000_000})
        # Near-identical token counts; the rate is what separates them.
        assert round(cold["prompt_eval_tokens_per_second"]) == 215
        assert round(warm["prompt_eval_tokens_per_second"]) == 510

    def test_missing_or_zero_fields_do_not_raise(self):
        # A stream that errors mid-flight still gets recorded, and Ollama omits
        # these keys on some error paths.
        stats = _eval_stats({})
        assert stats["prompt_eval_count"] == 0
        assert stats["prompt_eval_seconds"] == 0.0
        assert stats["prompt_eval_tokens_per_second"] == 0.0

    def test_null_durations_are_treated_as_absent(self):
        stats = _eval_stats({"prompt_eval_count": 10, "prompt_eval_duration": None})
        assert stats["prompt_eval_tokens_per_second"] == 0.0

    def test_reset_clears_eval_stats(self):
        agent = make_agent()
        agent.last_eval_stats = _eval_stats({"prompt_eval_count": 1, "prompt_eval_duration": 1})
        agent.reset()
        assert agent.last_eval_stats == {}


class TestRequestOptions:
    def test_num_ctx_is_sent_so_ollama_does_not_fall_back_to_its_4096_default(self):
        agent = make_agent()
        assert agent._options() == {"num_ctx": 6144}

    def test_extra_options_merge_without_dropping_num_ctx(self):
        # warmup() passes num_predict but must still load the model at the real
        # context size, or the first question forces a reload.
        agent = make_agent()
        assert agent._options(num_predict=1) == {"num_ctx": 6144, "num_predict": 1}

    def test_zero_num_ctx_leaves_the_option_off_entirely(self):
        agent = Agent(model="m", url="http://x", system_prompt="SYS", num_ctx=0,
                      num_predict=0)
        assert agent._options() == {}

    def test_num_predict_is_sent_as_a_runaway_backstop(self):
        agent = make_agent(num_predict=260)
        assert agent._options() == {"num_ctx": 6144, "num_predict": 260}

    def test_zero_num_predict_leaves_ollamas_own_default_in_place(self):
        assert "num_predict" not in make_agent(num_predict=0)._options()

    def test_warmup_num_predict_wins_over_the_backstop(self):
        # warmup() wants exactly one token; the backstop must not override it.
        agent = make_agent(num_predict=260)
        assert agent._options(num_predict=1)["num_predict"] == 1


class TestContextWindowWarning:
    def test_warns_when_the_prompt_approaches_num_ctx(self, capsys):
        agent = make_agent(num_ctx=1000)
        agent._warn_if_near_ctx(850)
        assert "WARNING" in capsys.readouterr().out

    def test_silent_with_headroom(self, capsys):
        agent = make_agent(num_ctx=1000)
        agent._warn_if_near_ctx(500)
        assert capsys.readouterr().out == ""

    def test_silent_when_num_ctx_is_disabled(self, capsys):
        agent = make_agent(num_ctx=0)
        agent._warn_if_near_ctx(999999)
        assert capsys.readouterr().out == ""
