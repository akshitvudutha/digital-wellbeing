"""
animated_stacked_widget.py — PySide6 Custom Stacked Widget with Cross-Fade Transitions.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that animates page switches with a smooth cross-fade effect."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_animating: bool = False
        self._duration: int = 150

    def setCurrentIndexAnimated(self, index: int) -> None:
        if index == self.currentIndex() or self._is_animating or index < 0 or index >= self.count():
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(index)

        if not current_widget or not next_widget:
            self.setCurrentIndex(index)
            return

        self._is_animating = True

        # Setup opacity effect on next widget
        opacity_effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)

        # Show next widget
        self.setCurrentIndex(index)

        # Fade in animation
        anim = QPropertyAnimation(opacity_effect, b"opacity", self)
        anim.setDuration(self._duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def on_finished():
            next_widget.setGraphicsEffect(None)
            self._is_animating = False

        anim.finished.connect(on_finished)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
