"""
report_exporter.py — Local offline report exporter for Notch v3.6.3.
Exports Weekly Wellbeing Reports to clean Markdown (.md) and self-contained,
printable modern HTML (.html) with zero external dependencies.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from analytics.weekly_report import WeeklyReportData, format_duration, format_delta_time


class ReportExporter:
    """Exports weekly wellbeing reports to Markdown and HTML."""

    @staticmethod
    def export_markdown(data: WeeklyReportData, dest_path: Optional[Path] = None) -> str:
        date_range_str = f"{data.start_date.strftime('%b %d, %Y')} – {data.end_date.strftime('%b %d, %Y')}"
        prior_range_str = f"{data.prior_start_date.strftime('%b %d, %Y')} – {data.prior_end_date.strftime('%b %d, %Y')}"

        delta_pct_str = f"{data.active_delta_pct:+.1f}%" if data.active_delta_pct is not None else "N/A"
        delta_dur_str = format_delta_time(data.active_delta_s)

        md_lines = [
            "# Notch — Weekly Wellbeing Report",
            f"**Reporting Period:** {date_range_str} *(Prior: {prior_range_str})*",
            "",
            "---",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | This Week | Prior Week | Change |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Active Screen Time** | {format_duration(data.curr_active_s)} | {format_duration(data.prior_active_s)} | {delta_dur_str} ({delta_pct_str}) |",
            f"| **Idle Time** | {format_duration(data.curr_idle_s)} | {format_duration(data.prior_idle_s)} | {format_delta_time(data.curr_idle_s - data.prior_idle_s)} |",
            f"| **Daily Average** | {format_duration(data.daily_avg_active_s)} / day | {format_duration(data.prior_active_s / 7.0)} / day | — |",
            f"| **Peak Activity Day** | {data.peak_day_name} ({format_duration(data.peak_day_active_s)}) | — | — |",
            "",
            "## 2. Key Factual Insights",
            "",
        ]

        for insight in data.insights:
            md_lines.append(f"- {insight}")

        md_lines.extend([
            "",
            "## 3. Daily Activity Breakdown",
            "",
            "| Date | Day | Active Screen Time | Idle Time |",
            "| :--- | :--- | :--- | :--- |",
        ])

        for day in data.daily_breakdown:
            md_lines.append(
                f"| {day['date_str']} | {day['full_day_name']} | {format_duration(day['active_s'])} | {format_duration(day['idle_s'])} |"
            )

        md_lines.extend([
            "",
            "## 4. Top Applications & Shifts",
            "",
            "| Application | Category | This Week | Prior Week | Change |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ])

        if data.top_apps_shifts:
            for app in data.top_apps_shifts:
                md_lines.append(
                    f"| **{app['display_name']}** | {app['category']} | {format_duration(app['curr_s'])} | {format_duration(app['prior_s'])} | {app['delta_formatted']} |"
                )
        else:
            md_lines.append("| *No applications recorded* | — | — | — | — |")

        md_lines.extend([
            "",
            "## 5. Category Allocation",
            "",
            "| Category | Time Spent | Share of Total |",
            "| :--- | :--- | :--- |",
        ])

        if data.category_breakdown:
            for cat in data.category_breakdown:
                md_lines.append(
                    f"| **{cat['category']}** | {format_duration(cat['total_s'])} | {cat['percentage']:.1f}% |"
                )
        else:
            md_lines.append("| *No category usage recorded* | — | — |")

        # Deep work section
        dw = data.deep_work_stats
        md_lines.extend([
            "",
            "## 6. Deep Work & Focus Sessions",
            "",
            f"- **Total Sessions Initiated:** {dw.get('total_sessions', 0)}",
            f"- **Sessions Completed:** {dw.get('completed_sessions', 0)} ({dw.get('completion_rate', 0):.0f}% completion rate)",
            f"- **Dedicated Work Time:** {format_duration(dw.get('total_work_s', 0.0))}",
            f"- **Dedicated Break Time:** {format_duration(dw.get('total_break_s', 0.0))}",
            "",
            "---",
            "*Generated 100% locally and privately by Notch Digital Wellbeing on Windows. Zero cloud telemetry.*",
        ])

        content = "\n".join(md_lines)
        if dest_path:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(content, encoding="utf-8")
        return content

    @staticmethod
    def export_html(data: WeeklyReportData, dest_path: Optional[Path] = None) -> str:
        date_range_str = f"{data.start_date.strftime('%b %d, %Y')} – {data.end_date.strftime('%b %d, %Y')}"
        delta_pct_str = f"{data.active_delta_pct:+.1f}%" if data.active_delta_pct is not None else "N/A"
        delta_dur_str = format_delta_time(data.active_delta_s)

        # Build insights list HTML
        insights_html = "".join(f"<li>{item}</li>" for item in data.insights)

        # Build daily rows HTML
        daily_rows_html = "".join(
            f"<tr><td>{day['date_str']}</td><td><strong>{day['full_day_name']}</strong></td><td>{format_duration(day['active_s'])}</td><td>{format_duration(day['idle_s'])}</td></tr>"
            for day in data.daily_breakdown
        )

        # Build apps rows HTML
        apps_rows_html = ""
        for app in data.top_apps_shifts:
            delta_color = "#10B981" if app["delta_s"] <= 0 else "#F59E0B"
            apps_rows_html += (
                f"<tr><td><strong>{app['display_name']}</strong></td>"
                f"<td><span class='badge'>{app['category']}</span></td>"
                f"<td>{format_duration(app['curr_s'])}</td>"
                f"<td>{format_duration(app['prior_s'])}</td>"
                f"<td style='color: {delta_color}; font-weight: 700;'>{app['delta_formatted']}</td></tr>"
            )

        # Build categories rows HTML
        cats_rows_html = "".join(
            f"<tr><td><strong>{cat['category']}</strong></td><td>{format_duration(cat['total_s'])}</td><td>{cat['percentage']:.1f}%</td></tr>"
            for cat in data.category_breakdown
        )

        dw = data.deep_work_stats

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Notch Weekly Wellbeing Report — {date_range_str}</title>
    <style>
        :root {{
            --bg: #0F172A;
            --surface: #1E293B;
            --surface-elevated: #334155;
            --border: #334155;
            --text-main: #F8FAFC;
            --text-sub: #94A3B8;
            --accent: #10B981;
            --accent-bg: rgba(16, 185, 129, 0.12);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.6;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            margin-bottom: 32px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
        }}
        .badge-brand {{
            display: inline-block;
            background: var(--accent-bg);
            color: var(--accent);
            border: 1px solid var(--accent);
            border-radius: 6px;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 10px;
            letter-spacing: 0.8px;
            margin-bottom: 12px;
        }}
        h1 {{
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.5px;
            margin-bottom: 6px;
        }}
        .date-range {{
            color: var(--text-sub);
            font-size: 14px;
            font-weight: 500;
        }}
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        .card-label {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-sub);
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .card-val {{
            font-size: 24px;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.5px;
        }}
        .card-sub {{
            font-size: 12px;
            font-weight: 600;
            color: var(--accent);
            margin-top: 4px;
        }}
        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            letter-spacing: -0.2px;
        }}
        ul.insights-list {{
            list-style: none;
        }}
        ul.insights-list li {{
            position: relative;
            padding-left: 24px;
            margin-bottom: 10px;
            font-size: 14px;
            color: var(--text-main);
        }}
        ul.insights-list li::before {{
            content: "•";
            position: absolute;
            left: 8px;
            color: var(--accent);
            font-size: 18px;
            line-height: 1;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            text-align: left;
            padding: 10px 14px;
            color: var(--text-sub);
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            border-bottom: 1px solid var(--border);
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid rgba(51, 65, 85, 0.4);
            color: var(--text-main);
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .badge {{
            background: var(--surface-elevated);
            color: var(--text-sub);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }}
        .footer {{
            text-align: center;
            font-size: 12px;
            color: var(--text-sub);
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}
        @media print {{
            body {{ background: #FFFFFF; color: #000000; padding: 0; }}
            .card, .section {{ background: #FFFFFF; border: 1px solid #CBD5E1; color: #000000; }}
            .card-val, h1, h2, td strong {{ color: #000000; }}
            .badge-brand {{ border-color: #000000; color: #000000; background: none; }}
            th {{ color: #475569; border-bottom: 1px solid #000000; }}
            td {{ border-bottom: 1px solid #E2E8F0; color: #000000; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge-brand">NOTCH DIGITAL WELLBEING</span>
            <h1>Weekly Wellbeing Report</h1>
            <div class="date-range">{date_range_str}</div>
        </div>

        <div class="cards-grid">
            <div class="card">
                <div class="card-label">Active Screen Time</div>
                <div class="card-val">{format_duration(data.curr_active_s)}</div>
                <div class="card-sub">{delta_dur_str} ({delta_pct_str}) vs prior week</div>
            </div>
            <div class="card">
                <div class="card-label">Daily Average</div>
                <div class="card-val">{format_duration(data.daily_avg_active_s)}</div>
                <div class="card-sub">per active day</div>
            </div>
            <div class="card">
                <div class="card-label">Peak Focus Day</div>
                <div class="card-val">{data.peak_day_name}</div>
                <div class="card-sub">{format_duration(data.peak_day_active_s)} active</div>
            </div>
            <div class="card">
                <div class="card-label">Deep Work Sessions</div>
                <div class="card-val">{dw.get('completed_sessions', 0)} / {dw.get('total_sessions', 0)}</div>
                <div class="card-sub">{dw.get('completion_rate', 0):.0f}% completion rate</div>
            </div>
        </div>

        <div class="section">
            <h2>Key Factual Insights</h2>
            <ul class="insights-list">
                {insights_html}
            </ul>
        </div>

        <div class="section">
            <h2>Daily Activity Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Day</th>
                        <th>Active Time</th>
                        <th>Idle Time</th>
                    </tr>
                </thead>
                <tbody>
                    {daily_rows_html}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Top Applications & Shifts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Application</th>
                        <th>Category</th>
                        <th>This Week</th>
                        <th>Prior Week</th>
                        <th>Change</th>
                    </tr>
                </thead>
                <tbody>
                    {apps_rows_html}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Category Allocation</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Time Spent</th>
                        <th>Share of Total</th>
                    </tr>
                </thead>
                <tbody>
                    {cats_rows_html}
                </tbody>
            </table>
        </div>

        <div class="footer">
            Generated locally and securely by Notch Digital Wellbeing on Windows. Zero cloud telemetry.
        </div>
    </div>
</body>
</html>
"""
        if dest_path:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(html, encoding="utf-8")
        return html
