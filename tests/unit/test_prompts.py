from __future__ import annotations

from story_engine.agent.prompts import build_opening_messages


def test_basic_message_contains_source_story():
    msgs = build_opening_messages("Hamlet by Shakespeare")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert "Hamlet by Shakespeare" in msgs[0]["content"]


def test_message_ends_with_begin():
    msgs = build_opening_messages("Hamlet by Shakespeare")
    assert msgs[0]["content"].endswith("Begin.")


def test_initial_plot_injected():
    msgs = build_opening_messages("Hamlet by Shakespeare", initial_plot="Hamlet discovers a ghost.")
    content = msgs[0]["content"]
    assert "Hamlet discovers a ghost." in content
    assert "Initial plot:" in content


def test_environment_injected():
    msgs = build_opening_messages("Hamlet by Shakespeare", environment="Elsinore Castle, medieval Denmark")
    content = msgs[0]["content"]
    assert "Elsinore Castle, medieval Denmark" in content
    assert "Environment:" in content


def test_both_fields_injected():
    msgs = build_opening_messages(
        "Hamlet by Shakespeare",
        initial_plot="Hamlet discovers a ghost.",
        environment="Elsinore Castle",
    )
    content = msgs[0]["content"]
    assert "Hamlet by Shakespeare" in content
    assert "Elsinore Castle" in content
    assert "Hamlet discovers a ghost." in content


def test_none_fields_not_injected():
    msgs = build_opening_messages("Hamlet by Shakespeare", initial_plot=None, environment=None)
    content = msgs[0]["content"]
    assert "Initial plot:" not in content
    assert "Environment:" not in content


def test_environment_appears_before_initial_plot():
    """Environment should come before initial_plot so plot builds on setting context."""
    msgs = build_opening_messages(
        "Hamlet by Shakespeare",
        initial_plot="The plot.",
        environment="The setting.",
    )
    content = msgs[0]["content"]
    assert content.index("Environment:") < content.index("Initial plot:")
