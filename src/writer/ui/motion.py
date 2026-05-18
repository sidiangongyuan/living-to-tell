"""Small motion helpers for restrained UI transitions."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


FADE_MS = 140
SCROLL_MS = 150
_SHORT_SCROLL_MS = 16


def _keep_animation_alive(widget: QWidget, animation: QPropertyAnimation) -> None:
    old = getattr(widget, "_writer_motion_animation", None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass
    setattr(widget, "_writer_motion_animation", animation)

    def _clear() -> None:
        if getattr(widget, "_writer_motion_animation", None) is animation:
            setattr(widget, "_writer_motion_animation", None)

    animation.finished.connect(_clear)


def _bump_scrollbar_generation(scrollbar) -> int:
    generation = int(getattr(scrollbar, "_writer_scroll_generation", 0)) + 1
    setattr(scrollbar, "_writer_scroll_generation", generation)
    return generation


def cancel_scrollbar_animation(scrollbar) -> None:
    """Stop any in-flight smooth scrollbar animation and clear its handle."""
    _bump_scrollbar_generation(scrollbar)
    animation = getattr(scrollbar, "_writer_scroll_animation", None)
    if animation is None:
        return
    setattr(scrollbar, "_writer_scroll_animation", None)
    try:
        animation.stop()
    except RuntimeError:
        pass


def fade_in(widget: QWidget, *, duration_ms: int = FADE_MS, reduced: bool = False) -> None:
    """Fade a widget in after its content has already switched."""
    if reduced or duration_ms <= 0:
        widget.setGraphicsEffect(None)
        return

    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.01)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration_ms)
    animation.setStartValue(0.01)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _cleanup() -> None:
        widget.setGraphicsEffect(None)

    animation.finished.connect(_cleanup)
    _keep_animation_alive(widget, animation)
    animation.start()


def set_stack_index(
    stack: QStackedWidget,
    index: int,
    *,
    reduced: bool = False,
    duration_ms: int = FADE_MS,
) -> None:
    """Switch a stack immediately, then apply a short content fade."""
    if stack.currentIndex() == index:
        return
    stack.setCurrentIndex(index)
    fade_in(stack.currentWidget(), duration_ms=duration_ms, reduced=reduced)


def smooth_scrollbar_to(
    scrollbar,
    target: int,
    *,
    duration_ms: int = SCROLL_MS,
    reduced: bool = False,
) -> None:
    """Animate a scrollbar to target, interrupting any in-flight scroll."""
    target = max(scrollbar.minimum(), min(scrollbar.maximum(), int(target)))
    cancel_scrollbar_animation(scrollbar)
    if reduced or duration_ms <= 0 or scrollbar.value() == target:
        scrollbar.setValue(target)
        return

    generation = _bump_scrollbar_generation(scrollbar)
    animation = QPropertyAnimation(scrollbar, b"value", scrollbar)
    animation.setDuration(duration_ms)
    animation.setStartValue(scrollbar.value())
    animation.setEndValue(target)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    setattr(scrollbar, "_writer_scroll_animation", animation)

    if duration_ms <= _SHORT_SCROLL_MS:
        scrollbar.setValue(target)

        def _clear_short() -> None:
            try:
                if getattr(scrollbar, "_writer_scroll_generation", None) != generation:
                    return
                if getattr(scrollbar, "_writer_scroll_animation", None) is animation:
                    setattr(scrollbar, "_writer_scroll_animation", None)
            except RuntimeError:
                return

        QTimer.singleShot(0, _clear_short)
        return

    def _finish() -> None:
        try:
            if getattr(scrollbar, "_writer_scroll_generation", None) != generation:
                return
            scrollbar.setValue(target)
        except RuntimeError:
            return
        if getattr(scrollbar, "_writer_scroll_animation", None) is animation:
            setattr(scrollbar, "_writer_scroll_animation", None)

    animation.finished.connect(_finish)
    animation.start()
