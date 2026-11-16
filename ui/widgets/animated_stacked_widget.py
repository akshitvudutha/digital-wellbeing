"""Immediate stacked-page switching with the legacy animation API preserved."""

from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """QStackedWidget that switches pages without a blank opacity transition."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def setCurrentIndexAnimated(self, index: int) -> None:
        if index < 0 or index >= self.count() or index == self.currentIndex():
            return
        # The former fade started the incoming page at opacity 0 and ignored
        # navigation requests until its animation finished. Switch immediately
        # so the page stays visible and the selected navigation item stays in sync.
        self.setCurrentIndex(index)
