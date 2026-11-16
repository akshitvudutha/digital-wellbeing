"""
scripts/capture/capture_batch2_showcase.py — Component showcase for Batch 2:
StatCard, StatusBadge, EntityRow, and SegmentedControl in Dark and Light themes.
"""

import sys
import os
from pathlib import Path

# Resolve project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from ui.theme import ThemeManager
from ui.widgets.stat_card import StatCard
from ui.widgets.status_badge import StatusBadge
from ui.widgets.entity_row import EntityRow
from ui.widgets.segmented_control import SegmentedControl


class ComponentShowcaseWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notch Batch 2 — Shared Component Library Showcase")
        self.resize(1080, 850)
        self.setObjectName("showcase_window")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)

        # Header
        hdr_layout = QVBoxLayout()
        hdr_layout.setSpacing(4)
        title = QLabel("Shared Component Library Showcase")
        title.setObjectName("showcase_title")
        title.setStyleSheet("font-size: 24px; font-weight: 800; letter-spacing: -0.5px;")
        subtitle = QLabel("Standardized StatCard, StatusBadge, EntityRow, and SegmentedControl")
        subtitle.setObjectName("showcase_subtitle")
        subtitle.setStyleSheet("font-size: 13px; font-weight: 500;")
        hdr_layout.addWidget(title)
        hdr_layout.addWidget(subtitle)
        main_layout.addLayout(hdr_layout)

        # Scroll Area for Components
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        # ── 1. Segmented Control Section ──────────────────────────────────────
        sec1 = self._make_section_header("1. SEGMENTED CONTROL (Accessible Keyboard & Themes)")
        layout.addWidget(sec1)

        seg_row = QHBoxLayout()
        seg_row.setSpacing(16)
        self._seg_time = SegmentedControl([("Today", 1), ("7 Days", 7), ("30 Days", 30)], default_index=0)
        self._seg_views = SegmentedControl(["Overview", "Applications", "Websites", "Schedules"], default_index=1)
        seg_row.addWidget(self._seg_time)
        seg_row.addWidget(self._seg_views)
        seg_row.addStretch()
        layout.addLayout(seg_row)

        # ── 2. Stat Cards Section ─────────────────────────────────────────────
        sec2 = self._make_section_header("2. STAT CARDS (Metrics, Icons, Subtext, & Trends)")
        layout.addWidget(sec2)

        card_row = QHBoxLayout()
        card_row.setSpacing(14)

        self._card1 = StatCard(
            label="Daily Screen Time",
            value="4h 57m",
            icon="clock",
            subtext="Productivity ratio 82%",
            trend="+12% vs avg",
            trend_direction="up",
        )
        self._card2 = StatCard(
            label="Deep Work Focus",
            value="2h 45m",
            icon="focus",
            subtext="Goal: 3h 00m",
            trend="↑ 45m today",
            trend_direction="up",
        )
        self._card3 = StatCard(
            label="App Interruptions",
            value="18",
            icon="shield",
            subtext="Blocked distractions",
            trend="-30% vs last week",
            trend_direction="down",
        )
        card_row.addWidget(self._card1)
        card_row.addWidget(self._card2)
        card_row.addWidget(self._card3)
        layout.addLayout(card_row)

        # ── 3. Status Badges Section ──────────────────────────────────────────
        sec3 = self._make_section_header("3. STATUS BADGES (Semantic Variants & Contrast)")
        layout.addWidget(sec3)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(12)
        badge_row.addWidget(StatusBadge("ACTIVE SESSION", variant="active", show_dot=True))
        badge_row.addWidget(StatusBadge("NEAR LIMIT", variant="warning", show_dot=True))
        badge_row.addWidget(StatusBadge("LIMIT EXCEEDED", variant="exceeded", show_dot=True))
        badge_row.addWidget(StatusBadge("PIN LOCKED", variant="locked", icon_name="lock"))
        badge_row.addWidget(StatusBadge("STANDBY", variant="neutral", show_dot=True))
        badge_row.addStretch()
        layout.addLayout(badge_row)

        # ── 4. Entity Rows Section ────────────────────────────────────────────
        sec4 = self._make_section_header("4. ENTITY ROWS (Icon, Typography, Badges, Progress, Actions)")
        layout.addWidget(sec4)

        rows_card = QFrame()
        rows_card.setObjectName("v2_card")
        rows_layout = QVBoxLayout(rows_card)
        rows_layout.setContentsMargins(12, 12, 12, 12)
        rows_layout.setSpacing(4)

        # Row 1: Active browser
        row1 = EntityRow(
            primary_text="Brave Browser",
            secondary_text="Productivity • 4 windows active",
            icon="browser",
            badge=StatusBadge("ACTIVE", variant="active", show_dot=True),
            progress=0.78,
            trailing_text="3h 10m",
            entity_id="brave.exe",
        )
        btn1 = QPushButton("Configure")
        btn1.setStyleSheet("padding: 4px 10px; font-size: 12px; font-weight: 600;")
        row1.add_action(btn1)
        rows_layout.addWidget(row1)

        # Row 2: Warning nearing limit
        row2 = EntityRow(
            primary_text="ChatGPT Desktop",
            secondary_text="Artificial Intelligence & Research",
            icon="apps",
            badge=StatusBadge("80% OF LIMIT", variant="warning", show_dot=True),
            progress=0.80,
            trailing_text="40m / 50m",
            entity_id="chatgpt.exe",
        )
        btn2 = QPushButton("Edit Limit")
        btn2.setStyleSheet("padding: 4px 10px; font-size: 12px; font-weight: 600;")
        row2.add_action(btn2)
        rows_layout.addWidget(row2)

        # Row 3: Locked app
        row3 = EntityRow(
            primary_text="Steam Client",
            secondary_text="Gaming & Entertainment",
            icon="lock",
            badge=StatusBadge("LOCKED", variant="locked", icon_name="lock"),
            progress=1.0,
            trailing_text="Locked",
            entity_id="steam.exe",
        )
        btn3 = QPushButton("Unlock")
        btn3.setStyleSheet("padding: 4px 10px; font-size: 12px; font-weight: 600;")
        row3.add_action(btn3)
        rows_layout.addWidget(row3)

        layout.addWidget(rows_card)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _make_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 11px; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase;")
        return lbl

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        bg = tm.color("bg")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")

        self.setStyleSheet(f"""
            QWidget#showcase_window {{
                background-color: {bg};
                color: {text_main};
            }}
            QLabel#showcase_title {{
                color: {text_main};
            }}
            QLabel#showcase_subtitle {{
                color: {text_sub};
            }}
            QFrame#v2_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
        """)


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    artifact_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\5b5c87fa-4527-4927-b157-cf16a0059107")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scratch_media_dir = project_root / "scratch" / "media"
    scratch_media_dir.mkdir(parents=True, exist_ok=True)

    tm = ThemeManager.instance()
    tm.set_theme("dark", app=app)

    window = ComponentShowcaseWindow()
    window.show()

    def capture_sequence():
        print("Capturing Batch 2 Component Showcase Screenshots...")
        QApplication.processEvents()

        # 1. Dark Theme Capture
        dark_pixmap = window.grab()
        dark_artifact = artifact_dir / "batch2_showcase_dark.png"
        dark_scratch = scratch_media_dir / "batch2_showcase_dark.png"
        dark_pixmap.save(str(dark_artifact))
        dark_pixmap.save(str(dark_scratch))
        print(f"Saved Dark Showcase: {dark_artifact}")

        # 2. Switch to Light Theme
        tm.set_theme("light", app=app)
        QApplication.processEvents()

        # 3. Light Theme Capture
        light_pixmap = window.grab()
        light_artifact = artifact_dir / "batch2_showcase_light.png"
        light_scratch = scratch_media_dir / "batch2_showcase_light.png"
        light_pixmap.save(str(light_artifact))
        light_pixmap.save(str(light_scratch))
        print(f"Saved Light Showcase: {light_artifact}")

        # 4. Switch back to Dark Theme
        tm.set_theme("dark", app=app)
        QApplication.processEvents()
        print("Successfully captured Batch 2 showcases!")

        window.close()
        app.quit()

    QTimer.singleShot(600, capture_sequence)
    app.exec()


if __name__ == "__main__":
    main()
