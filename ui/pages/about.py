"""
about.py — V2 Brand Identity & About Page for Digital Wellbeing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from core.constants import APP_NAME, APP_VERSION


class AboutPage(QWidget):
    """V2 Brand Identity & About Page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._spec_labels = []
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("About Digital Wellbeing")
        title.setObjectName("page_title")
        subtitle = QLabel("Product mission, version specifications, and platform identity")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Main Brand Card
        card = QFrame()
        card.setObjectName("v2_card")
        c_l = QVBoxLayout(card)
        c_l.setContentsMargins(36, 32, 36, 32)
        c_l.setSpacing(16)
        c_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_lbl = QLabel()
        from pathlib import Path
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(icon_path))
        if not pix.isNull():
            logo_lbl.setPixmap(pix.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_l.addWidget(logo_lbl)

        self._app_lbl = QLabel(APP_NAME)
        self._app_lbl.setObjectName("app_lbl")
        self._app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._ver_lbl = QLabel(f"Version {APP_VERSION} Commercial — Build 2026.07")
        self._ver_lbl.setObjectName("ver_lbl")
        self._ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._desc_lbl = QLabel(
            "Digital Wellbeing V2 is an intelligent desktop activity monitor and health protection engine.\n"
            "Engineered to help you understand screen habits, boost deep focus, and maintain bedtime discipline."
        )
        self._desc_lbl.setObjectName("desc_lbl")
        self._desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_lbl.setWordWrap(True)

        c_l.addWidget(self._app_lbl)
        c_l.addWidget(self._ver_lbl)
        c_l.addWidget(self._desc_lbl)

        inner_layout.addWidget(card)

        # Specifications Card
        spec_card = QFrame()
        spec_card.setObjectName("v2_card")
        sp_l = QVBoxLayout(spec_card)
        sp_l.setContentsMargins(24, 20, 24, 20)
        sp_l.setSpacing(10)

        s_hdr = QLabel("Platform Specifications & Status")
        s_hdr.setObjectName("section_header")
        sp_l.addWidget(s_hdr)

        specs = [
            ("Tracking Engine", "Toolhelp32 Multi-Tier Win32 API Process Engine"),
            ("Bedtime Guard", "SleepGuard Media Detection Engine"),
            ("Database Engine", "SQLite3 WAL Mode with Auto-Heartbeats"),
            ("UI Framework", "PySide6 Qt 6.8 Fluent 2 Custom Glass"),
            ("Developer", "Akshit Labs"),
            ("Website", "https://digitalwellbeing.akshitlabs.com"),
            ("GitHub", "https://github.com/akshitlabs/digitalwellbeing"),
            ("Copyright", "© 2026 Akshit Labs. All rights reserved."),
            ("License", "Commercial Edition"),
        ]

        for k, v in specs:
            r = QHBoxLayout()
            kl = QLabel(k)
            kl.setObjectName("spec_key")
            vl = QLabel(v)
            vl.setObjectName("spec_val")
            r.addWidget(kl)
            r.addStretch()
            r.addWidget(vl)
            sp_l.addLayout(r)
            self._spec_labels.append((kl, vl))

        inner_layout.addWidget(spec_card)
        inner_layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 800; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#app_lbl {{ font-size: 28px; font-weight: 900; color: {tm.color('text_main')}; letter-spacing: -0.5px; }}
            QLabel#ver_lbl {{ font-size: 13px; font-weight: 700; color: {tm.color('info_text')}; background-color: {tm.color('info_bg')}; padding: 4px 12px; border-radius: 12px; border: 1px solid {tm.color('info_border')}; }}
            QLabel#desc_lbl {{ font-size: 13px; color: {tm.color('text_sub')}; line-height: 1.5; }}
            QLabel#spec_key {{ font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#spec_val {{ color: {tm.color('text_sub')}; font-size: 12px; }}
        """)
