from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollBar, QStackedWidget


def test_set_stack_index_switches_immediately_when_reduced(qtbot):
    from writer.ui.motion import set_stack_index

    stack = QStackedWidget()
    qtbot.addWidget(stack)
    first = QLabel("one")
    second = QLabel("two")
    stack.addWidget(first)
    stack.addWidget(second)

    set_stack_index(stack, 1, reduced=True)

    assert stack.currentIndex() == 1
    assert second.graphicsEffect() is None


def test_smooth_scrollbar_to_reduced_sets_value_immediately(qtbot):
    from writer.ui.motion import smooth_scrollbar_to

    scrollbar = QScrollBar()
    qtbot.addWidget(scrollbar)
    scrollbar.setRange(0, 100)
    scrollbar.setValue(5)

    smooth_scrollbar_to(scrollbar, 75, reduced=True)

    assert scrollbar.value() == 75
    assert getattr(scrollbar, "_writer_scroll_animation", None) is None


def test_smooth_scrollbar_to_interrupts_previous_animation(qtbot):
    from writer.ui.motion import smooth_scrollbar_to

    scrollbar = QScrollBar()
    qtbot.addWidget(scrollbar)
    scrollbar.setRange(0, 100)
    scrollbar.setValue(0)

    smooth_scrollbar_to(scrollbar, 80, duration_ms=500)
    first = getattr(scrollbar, "_writer_scroll_animation", None)
    assert first is not None

    smooth_scrollbar_to(scrollbar, 30, duration_ms=10)
    second = getattr(scrollbar, "_writer_scroll_animation", None)

    assert second is not None
    assert second is not first
    qtbot.waitUntil(lambda: scrollbar.value() == 30, timeout=1000)


def test_cancel_scrollbar_animation_stops_in_flight_scroll(qtbot):
    from writer.ui.motion import cancel_scrollbar_animation, smooth_scrollbar_to

    scrollbar = QScrollBar()
    qtbot.addWidget(scrollbar)
    scrollbar.setRange(0, 100)
    scrollbar.setValue(0)

    smooth_scrollbar_to(scrollbar, 90, duration_ms=500)
    animation = getattr(scrollbar, "_writer_scroll_animation", None)

    assert animation is not None

    cancel_scrollbar_animation(scrollbar)

    assert getattr(scrollbar, "_writer_scroll_animation", None) is None
    assert animation.state() == animation.State.Stopped
