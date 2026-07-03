import streamlit as st
import pandas as pd
import requests
from components.tables import render_detection_table
from components.cards import render_kpi_metrics_cards  # 👈 YEH LINE TOP PAR ADD HUI HAI
from utils.formatters import clean_ist_timestamp

def query_backend_api(api_base: str, endpoint: str, file_payload, is_video: bool = False):
    target_url = f"{api_base}/api/v1/{endpoint}"
    headers = {"ngrok-skip-browser-warning": "true"}
    
    if endpoint == "alerts/trigger":
        payload = {
            "camera_id": 1,
            "alert_category": "Traffic Violation Upload",
            "severity_level": 3,
            "confidence_score": 0.92,
            "frame_path": file_payload.name
        }
        try:
            response = requests.post(target_url, json=payload, headers=headers, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"🔌 Failed to communicate with API server: {e}")
            return None

    elif endpoint == "telemetry/log":
        payload = {
            "camera_id": 2,
            "metric_type": "Crowd Density stream",
            "measured_value": 45,
            "status": "NORMAL"
        }
        try:
            response = requests.post(target_url, json=payload, headers=headers, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"🔌 Failed to communicate with API server: {e}")
            return None

def fetch_real_logs(api_base: str):
    target_url = f"{api_base}/api/v1/detections"
    headers = {"ngrok-skip-browser-warning": "true"}
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data) if data and len(data) > 0 else None
        return None
    except Exception as e:
        st.error(f"🔌 Failed to connect to log server: {e}")
        return None

def render_executive_dashboard_view(api_base: str):
    st.markdown("<div class='soc-title'>🏠 System Executive Dashboard</div>", unsafe_allow_html=True)
    
    if st.button("🔄 Fetch Live Sat-Link Data"):
        st.rerun()

    with st.spinner("🔄 Streaming live relational logs from PostgreSQL pool..."):
        live_df = fetch_real_logs(api_base)

    if live_df is not None:
        live_df = clean_ist_timestamp(live_df)

        # 🚀 👈 HARDCODED HTML KO IS SINGLE LINE FUNCTION CALL SE REPLACE KAR DIYA HAI
        render_kpi_metrics_cards(total_entries=len(live_df), processing_speed="142ms")
        
        # Table rendering framework call
        render_detection_table(live_df, api_base)
    else:
        st.info("🛡️ System Nominal: No active violations detected in the current stream.")

    st.line_chart(pd.DataFrame({"Traffic Volume": [0, 0, 0]}))

def render_traffic_hub_view(api_base: str):
    st.markdown("<div class='soc-title'>🏍️ Traffic Enforcement Hub</div>", unsafe_allow_html=True)
    st.caption("Upload photos or video media files directly into the data matrix pipeline.")

    target_endpoint = st.selectbox("🎯 Target Detection Route", ["alerts/trigger", "telemetry/log"])
    st.divider()

    file_payload = st.file_uploader("Drop Traffic Photo or Video File Here", type=["jpg", "jpeg", "png", "mp4", "avi", "mov"])

    if file_payload is not None:
        file_extension = file_payload.name.split(".")[-1].lower()
        is_video_format = file_extension in ["mp4", "avi", "mov"]

        with st.spinner("⏳ Transmitting data metrics package to external database pool..."):
            api_response = query_backend_api(api_base, target_endpoint, file_payload, is_video=is_video_format)

        if api_response:
            col_left, col_right = st.columns([3, 2])
            with col_left:
                if not is_video_format:
                    st.image(file_payload, caption="Source Media Stream Target", use_container_width=True)
                else:
                    st.video(file_payload, start_time=0)
            with col_right:
                st.markdown("### 📊 Live API Inference Metrics")
                st.success("Entry successfully written to remote database!")
                st.json(api_response)