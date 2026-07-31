"""
charts.py — PyQtGraph high-DPI chart widgets for Hourly Screen Time Intensity and Daily Screen Time.
Ensures clean ticks, strict minimum heights, zero label overlaps, and strict yMin=0 limits (no -500 negative glitch).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget, QToolTip


class HourlyIntensityChart(QFrame):
    """24-Hour Screen Time Intensity Chart for Today View (Segment 0)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(320)
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Row
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self._title_lbl = QLabel("HOURLY SCREEN TIME INTENSITY")
        self._title_lbl.setObjectName("section_header")

        self._subtitle_lbl = QLabel("Active minutes per hour across the 24-hour day")
        self._subtitle_lbl.setObjectName("page_subtitle")

        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._subtitle_lbl)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # PyQtGraph PlotWidget
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(230)
        self._plot.setBackground(None)
        self._plot.getPlotItem().layout.setContentsMargins(12, 16, 16, 16)

        # Configure Grid & Axes
        self._plot.showGrid(x=False, y=True, alpha=0.18)
        self._plot.getPlotItem().setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)

        # Style Axes
        for axis_name in ("left", "bottom"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(pg.mkPen(color=QColor(255, 255, 255, 38), width=1))
            axis.setTextPen(pg.mkPen(color="#8B949E"))
            axis.setStyle(tickFont=QFont("Segoe UI", 9))

        self._plot.getPlotItem().setLabel("left", "Minutes", color="#8B949E", size="11pt")

        # Set clean 3-hour ticks on bottom axis without overlapping
        ticks = [(i, f"{i:02d}:00") for i in range(0, 24, 3)]
        self._plot.getPlotItem().getAxis("bottom").setTicks([ticks, []])

        # Enforce strict bottom limit (prevent negative Y zoom or -500 glitches)
        self._plot.getViewBox().setLimits(yMin=0, xMin=-1, xMax=24)
        self._plot.setXRange(-0.8, 23.8, padding=0)
        self._plot.setYRange(0, 10, padding=0)

        # Bar Graph Item
        self._bar_item = pg.BarGraphItem(
            x=list(range(24)),
            height=[0.0] * 24,
            width=0.65,
            brush=pg.mkBrush(QColor(47, 129, 247)),
            pen=pg.mkPen(QColor(255, 255, 255, 46), width=1),
        )
        self._plot.addItem(self._bar_item)
        layout.addWidget(self._plot)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#section_header {{ font-size: 14px; font-weight: 800; color: {tm.color('text_main')}; letter-spacing: 0.5px; }}
            QLabel#page_subtitle {{ font-size: 12px; color: {tm.color('text_sub')}; }}
        """)
        
        # Style Axes
        axis_pen = pg.mkPen(color=QColor(tm.color('border')), width=1)
        text_pen = pg.mkPen(color=QColor(tm.color('text_sub')))
        
        for axis_name in ("left", "bottom"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)

        # Only set label text, label color needs to be set properly
        self._plot.getPlotItem().setLabel("left", "Minutes", color=tm.color('text_sub'), size="11pt")
        
        self._bar_item.setOpts(
            brush=pg.mkBrush(QColor(tm.color('accent'))),
            pen=pg.mkPen(QColor(tm.color('border')), width=1)
        )

    def update_data(self, hourly_rows: List[dict]) -> None:
        """Update chart with list of 24 dicts containing 'hour' and 'total_s'."""
        if not hourly_rows or len(hourly_rows) != 24:
            return

        heights = [max(0.0, float(r.get("total_s", 0.0)) / 60.0) for r in hourly_rows]
        self._bar_item.setOpts(height=heights)

        max_val = max(heights) if heights else 0.0
        upper = max(10.0, max_val * 1.15)
        self._plot.setYRange(0, upper, padding=0)
        self._plot.getViewBox().setLimits(yMin=0, yMax=upper * 1.5)


class DailyScreenTimeChart(QFrame):
    """7-Day Screen Time Comparison Chart for Analytics View."""
    
    day_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(320)
        self._day_strings: List[str] = []
        self._raw_heights: List[float] = []
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Row
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self._title_lbl = QLabel("DAILY SCREEN TIME (PAST 7 DAYS)")
        self._title_lbl.setObjectName("section_header")

        self._subtitle_lbl = QLabel("Active screen time trend analysis")
        self._subtitle_lbl.setObjectName("page_subtitle")

        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._subtitle_lbl)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # PyQtGraph PlotWidget
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(230)
        self._plot.setBackground(None)
        self._plot.getPlotItem().layout.setContentsMargins(12, 16, 16, 16)

        # Configure Grid & Axes
        self._plot.showGrid(x=False, y=True, alpha=0.18)
        self._plot.getPlotItem().setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)

        for axis_name in ("left", "bottom"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(pg.mkPen(color=QColor(255, 255, 255, 38), width=1))
            axis.setTextPen(pg.mkPen(color="#8B949E"))
            axis.setStyle(tickFont=QFont("Segoe UI", 9))

        self._plot.getPlotItem().setLabel("left", "Hours", color="#8B949E", size="11pt")

        # Enforce strict bottom limit (prevent negative Y zoom or -500 glitches)
        self._plot.getViewBox().setLimits(yMin=0, xMin=-0.8, xMax=6.8)
        self._plot.setXRange(-0.6, 6.6, padding=0)
        self._plot.setYRange(0, 8.0, padding=0)

        # Bar Graph Item
        self._bar_item = pg.BarGraphItem(
            x=list(range(7)),
            height=[0.0] * 7,
            width=0.55,
            brush=pg.mkBrush(QColor(47, 129, 247)),
            pen=pg.mkPen(QColor(255, 255, 255, 46), width=1),
        )
        self._plot.addItem(self._bar_item)
        layout.addWidget(self._plot)
        
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self._plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#section_header {{ font-size: 14px; font-weight: 800; color: {tm.color('text_main')}; letter-spacing: 0.5px; }}
            QLabel#page_subtitle {{ font-size: 12px; color: {tm.color('text_sub')}; }}
        """)
        
        # Style Axes
        axis_pen = pg.mkPen(color=QColor(tm.color('border')), width=1)
        text_pen = pg.mkPen(color=QColor(tm.color('text_sub')))
        
        for axis_name in ("left", "bottom"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)

        # Just update the color parameter of the label
        self._plot.getPlotItem().getAxis("left").setLabel(color=tm.color('text_sub'))
        
        self._bar_item.setOpts(
            brush=pg.mkBrush(QColor(tm.color('accent'))),
            pen=pg.mkPen(QColor(tm.color('border')), width=1)
        )

    def _on_mouse_moved(self, pos) -> None:
        if not self._day_strings or not self._raw_heights:
            return
            
        mouse_point = self._plot.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        idx = int(round(x))
        
        if 0 <= idx < len(self._day_strings) and abs(x - idx) <= 0.35:
            # Check if hovered over the bar (Y check)
            h = self._bar_item.opts['height'][idx]
            if 0 <= mouse_point.y() <= h:
                day_str = self._day_strings[idx]
                total_s = self._raw_heights[idx]
                
                from analytics.engine import AnalyticsEngine
                engine = AnalyticsEngine()
                time_str = engine.format_duration(total_s)
                
                dt = datetime.strptime(day_str, "%Y-%m-%d")
                friendly_day = dt.strftime("%A, %b %d")
                
                from settings.manager import SettingsManager
                limit_s = SettingsManager().get_int("daily_limit_minutes", 480) * 60
                goal_status = "Over Goal" if total_s > limit_s else "Under Goal"
                
                tooltip_text = f"<b>{friendly_day}</b><br/>Time: {time_str}<br/>Status: {goal_status}"
                
                screen_pos = self._plot.mapToGlobal(self._plot.mapFromScene(pos))
                QToolTip.showText(screen_pos, tooltip_text, self._plot)
                return
                
        QToolTip.hideText()

    def _on_mouse_clicked(self, event) -> None:
        if not self._day_strings:
            return
        
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            mouse_point = self._plot.getViewBox().mapSceneToView(pos)
            x = mouse_point.x()
            idx = int(round(x))
            
            if 0 <= idx < len(self._day_strings) and abs(x - idx) <= 0.35:
                self.day_selected.emit(self._day_strings[idx])
                
                # Visual feedback
                from ui.theme import ThemeManager
                tm = ThemeManager.instance()
                
                brushes = [pg.mkBrush(QColor(tm.color('accent')))] * len(self._day_strings)
                brushes[idx] = pg.mkBrush(QColor(tm.color('accent_hover'))) 
                self._bar_item.setOpts(brushes=brushes)

    def update_data(self, daily_points: List[Any]) -> None:
        """Update chart with list of DailyPoint objects (or dicts) having 'day' and 'active_s'."""
        if not daily_points:
            return

        heights: List[float] = []
        ticks: List[tuple] = []
        max_active_s = 0.0

        for idx, pt in enumerate(daily_points):
            active_s = getattr(pt, "active_s", None)
            if active_s is None and isinstance(pt, dict):
                active_s = float(pt.get("active_s", 0.0))
            active_s = max(0.0, float(active_s or 0.0))
            max_active_s = max(max_active_s, active_s)

            day_str = getattr(pt, "day", None)
            if day_str is None and isinstance(pt, dict):
                day_str = pt.get("day", "")
            
            formatted_date = str(day_str)
            try:
                dt = datetime.strptime(str(day_str), "%Y-%m-%d")
                formatted_date = dt.strftime("%b %d")
            except (ValueError, TypeError):
                pass
            
            ticks.append((idx, formatted_date))
            heights.append(active_s)
            
        self._day_strings = [str(getattr(pt, "day", pt.get("day", ""))) if isinstance(pt, dict) else str(getattr(pt, "day", "")) for pt in daily_points]
        self._raw_heights = heights

        # Smart unit scaling
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if max_active_s >= 3600.0:
            heights_scaled = [h / 3600.0 for h in heights]
            self._plot.getPlotItem().setLabel("left", "Hours", color=tm.color('text_sub'), size="11pt")
        else:
            heights_scaled = [h / 60.0 for h in heights]
            self._plot.getPlotItem().setLabel("left", "Minutes", color=tm.color('text_sub'), size="11pt")

        self._bar_item.setOpts(x=list(range(len(heights_scaled))), height=heights_scaled)
        self._plot.getPlotItem().getAxis("bottom").setTicks([ticks, []])

        max_val = max(heights_scaled) if heights_scaled else 0.0
        upper = max(2.0, max_val * 1.15)
        self._plot.setYRange(0, upper, padding=0)
        self._plot.getViewBox().setLimits(yMin=0, xMin=-0.8, xMax=max(6.8, len(heights_scaled) - 0.2), yMax=upper * 1.5)
