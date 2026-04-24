from pathlib import Path

import pytest

from writer.app.container import build_container
from writer.domain.enums import RewriteAction, VersionType
from writer.services.ai.interfaces import (
    AiError,
    AiProvider,
    RewriteRequest,
    RewriteResponse,
)
from writer.services.ai.rewrite_service import RewriteService


class _FakeProvider(AiProvider):
    name = "fake"

    def __init__(self, text: str = "POLISHED"):
        self._text = text
        self.calls: list[RewriteRequest] = []

    def rewrite(self, request):
        self.calls.append(request)
        return RewriteResponse(
            content=self._text, model="fake-model", provider=self.name
        )


class _BoomProvider(AiProvider):
    name = "boom"

    def rewrite(self, request):
        raise AiError("network down")


@pytest.fixture()
def container(isolated_data_dir: Path):
    c = build_container()
    yield c
    c.close()


def test_generate_does_not_mutate_entry(container):
    entry = container.entry_repository.create(title="t", body="hello world")
    fake = _FakeProvider("POLISHED")
    service = RewriteService(
        container.entry_repository, container.version_repository, lambda: fake
    )

    response = service.generate(
        RewriteRequest(action=RewriteAction.POLISH, text="hello world")
    )

    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "hello world"  # untouched
    assert response.content == "POLISHED"
    assert container.version_repository.list_for_entry(entry.id) == []


def test_apply_acceptance_full_body_replaces_and_records_versions(container):
    entry = container.entry_repository.create(title="t", body="hello world")
    fake = _FakeProvider("POLISHED")
    service = RewriteService(
        container.entry_repository, container.version_repository, lambda: fake
    )

    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.POLISH,
        original_full_body="hello world",
        selection_start=None,
        selection_end=None,
        generated_text="POLISHED",
        title="t",
        provider="fake",
        model="fake-model",
    )

    assert outcome.new_body == "POLISHED"
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "POLISHED"

    versions = container.version_repository.list_for_entry(entry.id)
    types = sorted(v.version_type for v in versions)
    assert types == sorted([VersionType.ORIGINAL.value, VersionType.AI_POLISH.value])
    original = next(v for v in versions if v.version_type == VersionType.ORIGINAL.value)
    assert original.content == "hello world"
    ai = next(v for v in versions if v.version_type == VersionType.AI_POLISH.value)
    assert ai.content == "POLISHED"
    assert ai.provider == "fake"
    assert ai.model == "fake-model"


def test_apply_acceptance_with_selection_replaces_only_span(container):
    entry = container.entry_repository.create(title="t", body="abcdef")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider("XYZ"),
    )

    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.POLISH,
        original_full_body="abcdef",
        selection_start=2,
        selection_end=4,
        generated_text="XYZ",
        title="t",
        provider="fake",
        model="fake-model",
    )

    assert outcome.new_body == "abXYZef"
    reloaded = container.entry_repository.get(entry.id)
    assert reloaded.body == "abXYZef"


def test_continue_without_selection_appends(container):
    entry = container.entry_repository.create(title="t", body="Once upon a time")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider(", there was."),
    )

    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.CONTINUE,
        original_full_body="Once upon a time",
        selection_start=None,
        selection_end=None,
        generated_text=", there was.",
        title="t",
        provider="fake",
        model="fake-model",
    )

    assert outcome.new_body == "Once upon a time, there was."


def test_provider_failure_propagates(container):
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _BoomProvider(),
    )
    with pytest.raises(AiError):
        service.generate(RewriteRequest(action=RewriteAction.POLISH, text="x"))


# ---------------------------------------------------------------------------
# M6A: Partial accept — service tests
# (The service receives the already-resolved accepted_text; tests verify the
#  body assembly and version history content for each scenario.)
# ---------------------------------------------------------------------------

def test_partial_accept_selection_rewrite_replaces_only_span(container):
    """Partial accept on a selection rewrite: only the accepted sub-text
    replaces the original selection span."""
    entry = container.entry_repository.create(title="t", body="abcdef")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider("FULL_GEN"),
    )
    # User selected "cd" (positions 2-4) for rewrite; AI returned "FULL_GEN".
    # User then selects only "FULL" from the generated pane → accepted_text = "FULL"
    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.POLISH,
        original_full_body="abcdef",
        selection_start=2,
        selection_end=4,
        generated_text="FULL",   # partial selection from generated pane
        title="t",
        provider="fake",
        model="fake-model",
    )
    assert outcome.new_body == "abFULLef"
    assert container.entry_repository.get(entry.id).body == "abFULLef"


def test_partial_accept_whole_body_rewrite_uses_accepted_fragment(container):
    """Partial accept on a whole-body rewrite: accepted sub-text becomes the
    entire new body."""
    entry = container.entry_repository.create(title="t", body="original body")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider("LONG GENERATED TEXT"),
    )
    # User accepts only "LONG" from the generated pane
    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.POLISH,
        original_full_body="original body",
        selection_start=None,
        selection_end=None,
        generated_text="LONG",
        title="t",
        provider="fake",
        model="fake-model",
    )
    assert outcome.new_body == "LONG"
    assert container.entry_repository.get(entry.id).body == "LONG"


def test_partial_accept_continue_appends_only_selected(container):
    """Partial accept on CONTINUE: only the selected continuation is appended."""
    entry = container.entry_repository.create(title="t", body="Intro.")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider(" Full continuation text."),
    )
    # User accepts only " Short" from the generated pane
    outcome = service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.CONTINUE,
        original_full_body="Intro.",
        selection_start=None,
        selection_end=None,
        generated_text=" Short",
        title="t",
        provider="fake",
        model="fake-model",
    )
    assert outcome.new_body == "Intro. Short"


def test_partial_accept_ai_version_content_is_accepted_text(container):
    """The AI version stored in history must contain only the accepted
    (partial) text, not the full generated pane content."""
    entry = container.entry_repository.create(title="t", body="original")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider("full AI result"),
    )
    service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.EXPAND,
        original_full_body="original",
        selection_start=None,
        selection_end=None,
        generated_text="partial",   # only this portion was accepted
        title="t",
        provider="fake",
        model="fake-model",
    )
    versions = container.version_repository.list_for_entry(entry.id)
    ai_v = next(v for v in versions if v.version_type == VersionType.AI_EXPAND.value)
    assert ai_v.content == "partial"


def test_acceptance_always_writes_original_snapshot(container):
    """Every acceptance (full or partial) must store an ORIGINAL snapshot
    of the body before applying the change."""
    entry = container.entry_repository.create(title="t", body="before")
    service = RewriteService(
        container.entry_repository,
        container.version_repository,
        lambda: _FakeProvider("after"),
    )
    service.apply_acceptance(
        entry_id=entry.id,
        action=RewriteAction.POLISH,
        original_full_body="before",
        selection_start=None,
        selection_end=None,
        generated_text="after",
        title="t",
        provider="fake",
        model="fake-model",
    )
    versions = container.version_repository.list_for_entry(entry.id)
    orig = next(v for v in versions if v.version_type == VersionType.ORIGINAL.value)
    assert orig.content == "before"
