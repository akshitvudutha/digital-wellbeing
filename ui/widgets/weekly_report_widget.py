"""
weekly_report_widget.py — Visual dashboard for the 7-day Weekly Wellbeing Report in Notch v3.6.3.
Displays comparative weekly metrics, top application shifts, category distribution,
deep work completion rates, factual insights, and 1-click Markdown/HTML export.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QFileDialog, QMessageBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)

from analytics.weekly_report import WeeklyReportGenerator, WeeklyReportData, format_duration
from analytics.report_exporter import ReportExporter
from database.repository import Repository
from ui.theme import ThemeManager


class WeeklyReportWidget(QWidget):
    """Interactive visual dashboard for reviewing and exporting 7-day wellbeing reports."""

    def __init__(self, repo: Optional[Repository] = None, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo or Repository()
        self._generator = WeeklyReportGenerator(self._repo)
        self._current_data: Optional[WeeklyReportData] = None

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)
        self.refresh()

    def _on_theme_changed(self, _is_dark: bool) -> None:
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # ── Controls Header Bar: Week Selector & Export Buttons ──────────────
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(12)

        lbl_select = QLabel("PERIOD:")
        lbl_select.setObjectName("section_tag")
        ctrl_bar.addWidget(lbl_select)

        self._period_combo = QComboBox()
        self._period_combo.setObjectName("period_combo")
        self._period_combo.addItem("This Week (Last 7 Days)", 0)
        self._period_combo.addItem("Prior Week (8–14 Days Ago)", 7)
        self._period_combo.addItem("2 Weeks Ago (15–21 Days Ago)", 14)
        self._period_combo.currentIndexChanged.connect(lambda _: self.refresh())
        ctrl_bar.addWidget(self._period_combo)

        ctrl_bar.addStretch()

        self._btn_export_md = QPushButton("Export Markdown")
        self._btn_export_md.setObjectName("btn_export_secondary")
        self._btn_export_md.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export_md.clicked.connect(self._on_export_markdown)
        ctrl_bar.addWidget(self._btn_export_md)

        self._btn_export_html = QPushButton("Export HTML")
        self._btn_export_html.setObjectName("btn_export_primary")
        self._btn_export_html.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_export_html.clicked.connect(self._on_export_html)
        ctrl_bar.addWidget(self._btn_export_html)

        layout.addLayout(ctrl_bar)

        # ── Executive KPI Cards (4 Cards) ────────────────────────────────────
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(14)

        self._card_active = self._create_kpi_card("ACTIVE SCREEN TIME")
        self._card_avg = self._create_kpi_card("DAILY AVERAGE")
        self._card_peak = self._create_kpi_card("PEAK FOCUS DAY")
        self._card_dw = self._create_kpi_card("DEEP WORK SESSIONS")

        self._cards_grid.addWidget(self._card_active["frame"], 0, 0)
        self._cards_grid.addWidget(self._card_avg["frame"], 0, 1)
        self._cards_grid.addWidget(self._card_peak["frame"], 0, 2)
        self._cards_grid.addWidget(self._card_dw["frame"], 0, 3)
        layout.addLayout(self._cards_grid)

        # ── Key Factual Insights Card ────────────────────────────────────────
        self._insights_frame = QFrame()
        self._insights_frame.setObjectName("report_section_frame")
        self._insights_layout = QVBoxLayout(self._insights_frame)
        self._insights_layout.setContentsMargins(24, 20, 24, 20)
        self._insights_layout.setSpacing(10)

        lbl_ins_title = QLabel("KEY FACTUAL OBSERVATIONS")
        lbl_ins_title.setObjectName("section_heading")
        self._insights_layout.addWidget(lbl_ins_title)

        self._insights_container = QVBoxLayout()
        self._insights_container.setSpacing(8)
        self._insights_layout.addLayout(self._insights_container)
        layout.addWidget(self._insights_frame)

        # ── Top Application Shifts Section ───────────────────────────────────
        self._apps_frame = QFrame()
        self._apps_frame.setObjectName("report_section_frame")
        apps_layout = QVBoxLayout(self._apps_frame)
        apps_layout.setContentsMargins(24, 20, 24, 20)
        apps_layout.setSpacing(12)

        lbl_apps_title = QLabel("TOP APPLICATION VOLUME & SHIFTS")
        lbl_apps_title.setObjectName("section_heading")
        apps_layout.addWidget(lbl_apps_title)

        self._apps_table = QTableWidget()
        self._apps_table.setObjectName("report_table")
        self._apps_table.setColumnCount(5)
        self._apps_table.setHorizontalHeaderLabels(["APPLICATION", "CATEGORY", "THIS WEEK", "PRIOR WEEK", "CHANGE"])
        self._apps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._apps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._apps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._apps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._apps_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._apps_table.verticalHeader().setVisible(False)
        self._apps_table.setShowGrid(False)
        self._apps_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        apps_layout.addWidget(self._apps_table)
        layout.addWidget(self._apps_frame)

        # ── Category Allocation Section ──────────────────────────────────────
        self._cats_frame = QFrame()
        self._cats_frame.setObjectName("report_section_frame")
        self._cats_layout = QVBoxLayout(self._cats_frame)
        self._cats_layout.setContentsMargins(24, 20, 24, 20)
        self._cats_layout.setSpacing(10)

        lbl_cats_title = QLabel("CATEGORY ALLOCATION")
        lbl_cats_title.setObjectName("section_heading")
        self._cats_layout.addWidget(lbl_cats_title)

        self._cats_container = QVBoxLayout()
        self._cats_container.setSpacing(8)
        self._cats_layout.addLayout(self._cats_container)
        layout.addWidget(self._cats_frame)

    def _create_kpi_card(self, title: str) -> dict:
        frame = QFrame()
        frame.setObjectName("report_kpi_card")
        l = QVBoxLayout(frame)
        l.setContentsMargins(20, 16, 20, 16)
        l.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("kpi_title")
        l.addWidget(lbl_title)

        lbl_val = QLabel("-")
        lbl_val.setObjectName("kpi_val")
        l.addWidget(lbl_val)

        lbl_sub = QLabel("-")
        lbl_sub.setObjectName("kpi_sub")
        l.addWidget(lbl_sub)

        return {"frame": frame, "title": lbl_title, "val": lbl_val, "sub": lbl_sub}

    def refresh(self) -> None:
        """Regenerate the report based on the active period selection."""
        days_offset = self._period_combo.currentData() or 0
        end_d = date.today() - timedelta(days=days_offset)
        self._current_data = self._generator.generate_report(end_date=end_d)

        data = self._current_data

        # 1. Update KPI Cards
        self._card_active["val"].setText(format_duration(data.curr_active_s))
        if data.active_delta_pct is not None:
            sign = "+" if data.active_delta_pct >= 0 else ""
            self._card_active["sub"].setText(f"{sign}{data.active_delta_pct:.1f}% vs prior week")
        else:
            self._card_active["sub"].setText("Baseline week")

        self._card_avg["val"].setText(format_duration(data.daily_avg_active_s))
        self._card_avg["sub"].setText("per day")

        self._card_peak["val"].setText(data.peak_day_name)
        self._card_peak["sub"].setText(f"{format_duration(data.peak_day_active_s)} active")

        dw = data.deep_work_stats
        self._card_dw["val"].setText(f"{dw.get('completed_sessions', 0)} / {dw.get('total_sessions', 0)}")
        self._card_dw["sub"].setText(f"{dw.get('completion_rate', 0):.0f}% completion rate")

        # 2. Update Insights
        self._clear_layout(self._insights_container)

        for ins in data.insights:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel("•")
            dot.setObjectName("bullet_dot")
            text = QLabel(ins)
            text.setObjectName("insight_text")
            text.setWordWrap(True)
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self._insights_container.addLayout(row)

        # 3. Update Apps Table
        self._apps_table.setRowCount(len(data.top_apps_shifts))
        for row_idx, app in enumerate(data.top_apps_shifts):
            item_name = QTableWidgetItem(app["display_name"])
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled)

            item_cat = QTableWidgetItem(app["category"])
            item_cat.setFlags(Qt.ItemFlag.ItemIsEnabled)

            item_curr = QTableWidgetItem(format_duration(app["curr_s"]))
            item_curr.setFlags(Qt.ItemFlag.ItemIsEnabled)

            item_prior = QTableWidgetItem(format_duration(app["prior_s"]))
            item_prior.setFlags(Qt.ItemFlag.ItemIsEnabled)

            item_delta = QTableWidgetItem(app["delta_formatted"])
            item_delta.setFlags(Qt.ItemFlag.ItemIsEnabled)

            self._apps_table.setItem(row_idx, 0, item_name)
            self._apps_table.setItem(row_idx, 1, item_cat)
            self._apps_table.setItem(row_idx, 2, item_curr)
            self._apps_table.setItem(row_idx, 3, item_prior)
            self._apps_table.setItem(row_idx, 4, item_delta)

        self._apps_table.setFixedHeight(max(100, min(360, (len(data.top_apps_shifts) + 1) * 38)))

        # 4. Update Categories
        self._clear_layout(self._cats_container)

        if not data.category_breakdown:
            lbl_empty_cat = QLabel("No category data recorded for this period.")
            lbl_empty_cat.setObjectName("insight_text")
            self._cats_container.addWidget(lbl_empty_cat)
        else:
            for cat in data.category_breakdown:
                c_row = QHBoxLayout()
                c_row.setSpacing(12)
                lbl_c_name = QLabel(f"{cat['category']}")
                lbl_c_name.setObjectName("cat_name")
                lbl_c_dur = QLabel(f"{format_duration(cat['total_s'])}  ({cat['percentage']:.1f}%)")
                lbl_c_dur.setObjectName("cat_dur")
                c_row.addWidget(lbl_c_name)
                c_row.addStretch()
                c_row.addWidget(lbl_c_dur)
                self._cats_container.addLayout(c_row)

    @staticmethod
    def _clear_layout(layout) -> None:
        """Remove widgets and nested rows from a layout before rebuilding it."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                WeeklyReportWidget._clear_layout(child_layout)
                child_layout.deleteLater()

    def _on_export_markdown(self) -> None:
        if not self._current_data:
            return
        default_name = f"Notch_Weekly_Report_{self._current_data.start_date}_{self._current_data.end_date}.md"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Weekly Report to Markdown",
            str(Path.home() / "Desktop" / default_name),
            "Markdown Files (*.md)",
        )
        if path:
            ReportExporter.export_markdown(self._current_data, dest_path=Path(path))
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{path}")

    def _on_export_html(self) -> None:
        if not self._current_data:
            return
        default_name = f"Notch_Weekly_Report_{self._current_data.start_date}_{self._current_data.end_date}.html"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Weekly Report to HTML",
            str(Path.home() / "Desktop" / default_name),
            "HTML Files (*.html)",
        )
        if path:
            ReportExporter.export_html(self._current_data, dest_path=Path(path))
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{path}")

    def _apply_theme(self) -> None:
        tm = ThemeManager.instance()
        bg_card = tm.color("surface_card")
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        accent_bg = tm.color("accent_primary_bg")

        self.setStyleSheet(f"""
            QLabel#section_tag {{
                font-size: 11px;
                font-weight: 800;
                color: {text_sub};
                letter-spacing: 1px;
            }}
            QComboBox#period_combo {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 8px;
                color: {text_main};
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#btn_export_primary {{
                background: {tm.color('primary_btn_gradient')};
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton#btn_export_secondary {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 8px;
                padding: 7px 18px;
                color: {text_main};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#btn_export_secondary:hover {{
                background-color: {tm.color('surface_hover')};
            }}
            QFrame#report_kpi_card {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#kpi_title {{
                font-size: 11px;
                font-weight: 700;
                color: {text_sub};
                letter-spacing: 0.8px;
            }}
            QLabel#kpi_val {{
                font-size: 20px;
                font-weight: 800;
                color: {text_main};
                letter-spacing: -0.4px;
            }}
            QLabel#kpi_sub {{
                font-size: 12px;
                font-weight: 600;
                color: {accent};
            }}
            QFrame#report_section_frame {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#section_heading {{
                font-size: 11px;
                font-weight: 800;
                color: {text_sub};
                letter-spacing: 1.2px;
                margin-bottom: 4px;
            }}
            QLabel#bullet_dot {{
                color: {accent};
                font-size: 16px;
                font-weight: 800;
            }}
            QLabel#insight_text {{
                font-size: 13px;
                font-weight: 500;
                color: {text_main};
                line-height: 1.4;
            }}
            QTableWidget#report_table {{
                background: transparent;
                border: none;
                gridline-color: transparent;
                color: {text_main};
                font-size: 13px;
            }}
            QTableWidget#report_table QHeaderView::section {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {border};
                color: {text_sub};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.6px;
                padding: 6px 10px;
            }}
            QLabel#cat_name {{
                font-size: 13px;
                font-weight: 600;
                color: {text_main};
            }}
            QLabel#cat_dur {{
                font-size: 13px;
                font-weight: 700;
                color: {text_sub};
                font-family: monospace;
            }}
        """)
