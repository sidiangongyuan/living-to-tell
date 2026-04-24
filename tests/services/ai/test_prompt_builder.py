from writer.domain.enums import RewriteAction
from writer.services.ai.interfaces import RewriteRequest
from writer.services.ai.prompt_builder import PromptBuilder


def test_polish_messages_include_voice_and_text():
    builder = PromptBuilder()
    request = RewriteRequest(action=RewriteAction.POLISH, text="Hello world.")
    msgs = builder.build_messages(request)

    assert [m["role"] for m in msgs] == ["system", "user"]
    assert "polish" in msgs[0]["content"].lower()
    assert "preserve the author's voice" in msgs[0]["content"].lower()
    assert "Hello world." in msgs[1]["content"]


def test_continue_action_has_distinct_system_prompt():
    builder = PromptBuilder()
    polish = builder.system_prompt(RewriteAction.POLISH)
    cont = builder.system_prompt(RewriteAction.CONTINUE)
    assert polish != cont
    assert "continue" in cont.lower()


def test_references_are_included_but_marked_inspirational():
    builder = PromptBuilder()
    request = RewriteRequest(
        action=RewriteAction.EXPAND,
        text="A fragment.",
        references=["First ref.", "Second ref."],
    )
    msgs = builder.build_messages(request)
    user = msgs[1]["content"]
    assert "First ref." in user
    assert "Second ref." in user
    assert "tonal inspiration" in user.lower()


def test_max_output_chars_is_surfaced():
    builder = PromptBuilder()
    msgs = builder.build_messages(
        RewriteRequest(
            action=RewriteAction.POLISH, text="x", max_output_chars=500
        )
    )
    assert "500" in msgs[1]["content"]


def test_preserve_voice_false_drops_voice_clause():
    builder = PromptBuilder()
    msgs = builder.build_messages(
        RewriteRequest(action=RewriteAction.POLISH, text="x", preserve_voice=False)
    )
    assert "preserve the author's voice" not in msgs[0]["content"].lower()
