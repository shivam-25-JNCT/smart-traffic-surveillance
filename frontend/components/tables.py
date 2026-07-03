import html
import textwrap
import pandas as pd
import streamlit as st

def license_plate_chip(plate):
    if isinstance(plate, str) and plate.strip():
        return f'<span class="plate-chip">{html.escape(plate.strip().upper())}</span>'
    return '<span class="chip chip-none">UNREADABLE</span>'

def confidence_chip(score):
    if score is None or (isinstance(score, float) and pd.isna(score)):
        return '<span class="chip chip-none">N/A</span>'
    pct = score * 100 if score <= 1 else score
    cls = "chip-low" if pct >= 90 else ("chip-med" if pct >= 75 else "chip-high")
    return f'<span class="chip {cls}">{pct:.1f}%</span>'

def evidence_link(url, label, api_base):
    if isinstance(url, str) and url:
        full_url = url if url.startswith("http") else f"{api_base}{url}"
        return f'<a class="evidence-link" href="{html.escape(full_url)}" target="_blank">{label}</a>'
    return '<span class="evidence-dash">—</span>'

def render_detection_table(df: pd.DataFrame, api_base: str):
    rows_html = []
    for _, row in df.iterrows():
        ts = html.escape(str(row.get("timestamp", "—")))
        alert_id = html.escape(str(row.get("id", "—")))
        cam_id = html.escape(str(row.get("camera_id", "—")))
        category = html.escape(str(row.get("alert_category", "—")))
        
        row_html = f"""<tr>
            <td class="mono">{ts}</td>
            <td class="mono">#{alert_id}</td>
            <td class="mono">{cam_id}</td>
            <td>{category}</td>
            <td>{license_plate_chip(row.get("license_plate"))}</td>
            <td>{confidence_chip(row.get("confidence_score"))}</td>
            <td>{evidence_link(row.get("snapshot_url"), "🖼️ Snapshot", api_base)}</td>
            <td>{evidence_link(row.get("clip_url"), "🎬 Clip", api_base)}</td>
        </tr>"""
        rows_html.append(row_html)

    table_html = textwrap.dedent(f"""\
        <div class="aegis-table-wrap">
        <table class="aegis-table">
        <thead>
        <tr>
            <th>Time Detected</th>
            <th>Alert ID</th>
            <th>Cam ID</th>
            <th>Violation Details</th>
            <th>License Plate</th>
            <th>AI Confidence</th>
            <th>Snapshot</th>
            <th>Clip</th>
        </tr>
        </thead>
        <tbody>
        {''.join(rows_html)}
        </tbody>
        </table>
        </div>
    """)
    st.markdown(table_html, unsafe_allow_html=True)