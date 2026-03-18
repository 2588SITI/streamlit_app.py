import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- Page Configuration ---
st.set_page_config(page_title="KAVACH SENTINEL DASHBOARD", layout="wide")
st.markdown("<style>.block-container { padding-top: 2rem; padding-bottom: 2rem; }</style>", unsafe_allow_html=True)

st.title("🛡️ WR KAVACH RADIO DIAGNOSTIC DASHBOARD")
st.markdown("### Locomotive Analysis & Maintenance Audit System")

# --- Sidebar: Data Input ---
st.sidebar.header("📂 Data Input")
nms_file = st.sidebar.file_uploader("Upload TRNMSNMA (NMS Log)", type=['csv'])
rf_file = st.sidebar.file_uploader("Upload RFCOMM (Station Summary)", type=['csv'])

if nms_file and rf_file:
    # 1. Load Data
    df_nms = pd.read_csv(nms_file, low_memory=False)
    df_rf = pd.read_csv(rf_file, low_memory=False)

    # 2. Data Cleaning & Type Casting
    # Convert Train Nos to 5-digit strings for Y-axis naming
    df_nms['Loco Id'] = df_nms['Loco Id'].astype(str).str.strip()
    df_rf['Loco Id'] = df_rf['Loco Id'].astype(str).str.strip()
    
    # Numeric conversions
    df_nms['Pkt Len'] = pd.to_numeric(df_nms['Pkt Len'], errors='coerce').fillna(0)
    df_nms['Pkt Len2'] = pd.to_numeric(df_nms['Pkt Len2'], errors='coerce').fillna(0)
    df_nms['Speed'] = pd.to_numeric(df_nms.get('Speed', 0), errors='coerce').fillna(0)
    df_rf['Percentage'] = pd.to_numeric(df_rf['Percentage'], errors='coerce').fillna(0)

    # 3. Logic: Mode Downgrades
    if 'Mode' in df_nms.columns:
        df_nms['Prev_Mode'] = df_nms['Mode'].shift(1)
        downgrade_events = df_nms[(df_nms['Prev_Mode'] == 'FullSupervision') & (df_nms['Mode'] != 'FullSupervision')]
        total_downgrades = len(downgrade_events)
    else:
        downgrade_events = pd.DataFrame()
        total_downgrades = 0

    # 4. Logic: Emergency & Radio Fail Rates
    emergency_logs = df_nms[df_nms['Emr Status'] != 'Nominal'] if 'Emr Status' in df_nms.columns else []
    r1_fail_rate = (df_nms['Pkt Len'] < 10).mean() * 100
    r2_fail_rate = (df_nms['Pkt Len2'] < 10).mean() * 100

    # --- TOP METRICS SECTION ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mode Downgrades", total_downgrades, delta="-232 Events", delta_color="inverse")
    m2.metric("Radio 1 Fail Rate", f"{r1_fail_rate:.2f}%")
    m3.metric("Radio 2 Fail Rate", f"{r2_fail_rate:.2f}%")
    m4.metric("Emergency Logs", len(emergency_logs))
    st.divider()

    # --- STATION HEALTH & PIE CHART ---
    col_stn, col_pie = st.columns(2)
    
    with col_stn:
        st.subheader("📍 Station Communication Health")
        # Ensure Station Id is treated as categorical
        unique_stn = df_rf.drop_duplicates(subset=['Station Id']).sort_values('Percentage')
        fig_stn, ax_stn = plt.subplots()
        bar_colors = ['#EF9A9A' if x < 90 else '#A5D6A7' for x in unique_stn['Percentage']]
        ax_stn.bar(unique_stn['Station Id'], unique_stn['Percentage'], color=bar_colors)
        ax_stn.axhline(y=90, color='#37474F', linestyle='--', label='Target (90%)')
        plt.xticks(rotation=45)
        st.pyplot(fig_stn)
        st.caption("🔴 Red indicates trackside signal gaps (<90%). 🟢 Green is healthy.")

    with col_pie:
        st.subheader("📉 Downgrades by Station")
        if not downgrade_events.empty and 'Station' in downgrade_events.columns:
            stn_counts = downgrade_events['Station'].value_counts()
            fig_pie, ax_pie = plt.subplots()
            stn_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax_pie, startangle=90, colors=['#FFB3BA', '#FFDFBA', '#BAFFC9'])
            ax_pie.set_ylabel('')
            st.pyplot(fig_pie)
        else:
            st.write("✅ No Full Supervision (FS) downgrades detected.")

    # --- TRAIN VS STATION MATRIX (CATEGORICAL Y-AXIS) ---
    st.divider()
    st.subheader("📊 Train vs. Station Communication Matrix")
    pivot_df = df_rf.pivot_table(index='Loco Id', columns='Station Id', values='Percentage', aggfunc='mean')
    fig_heat = px.imshow(pivot_df, text_auto=".1f", color_continuous_scale='RdYlGn', 
                         labels=dict(x="Station", y="Loco ID (Train Name)", color="Health %"))
    # Force Y-axis to show all 5 digits as labels
    fig_heat.update_yaxes(type='category')
    fig_heat.update_xaxes(type='category')
    st.plotly_chart(fig_heat, use_container_width=True)

    # --- TECHNICAL AUDIT SECTION ---
    st.divider()
    st.header("📋 Technical Audit & Maintenance Actions")
    audit1, audit2 = st.columns(2)
    
    with audit1:
        st.subheader("1. Radio Diagnosis")
        if abs(r1_fail_rate - r2_fail_rate) < 10:
            st.success("✅ **Loco Health:** Onboard hardware (Antennas/Cables) performing consistently.")
        else:
            st.warning("⚠️ **Loco Health:** Radio performance imbalance detected. Check Antenna 1 vs Antenna 2.")
            
        low_stns = df_rf[df_rf['Percentage'] < 90]['Station Id'].tolist()
        if low_stns:
            st.error(f"❌ **Trackside Health:** Signal gaps confirmed at: {', '.join(set(low_stns))}")

    with audit2:
        st.subheader("2. Operational Safety")
        st.write(f"**Total FS Downgrades:** {total_downgrades}")
        st.write(f"**Emergency State Duration:** {len(emergency_logs)} log entries")
        if total_downgrades > 0:
            st.info(f"💡 **Cause Analysis:** High downgrades correlate with radio packet loss at specific locations.")

    # --- DEFINITIONS & LOGIC ---
    st.divider()
    st.header("📖 Technical Definitions & Audit Logic")
    with st.expander("🚨 Understanding Emergency Status Logs"):
        st.write(f"**What is the '{len(emergency_logs)}' Count?** It represents the total rows recorded in a non-nominal state. It indicates **duration**, not individual brake applications.")
    
    with st.expander("📉 What are 'Downgrades by Station'?"):
        st.write("Tracks where the train lost **Full Supervision (FS)**. Pinpointing this helps trackside teams fix the exact radio tower failing.")

    with st.expander("📡 Understanding Radio Fail Rates"):
        st.write("If Radio 1 fails more than Radio 2, it's a **Loco Fault**. If both fail at the same station, it's a **Station Fault**.")

else:
    st.info("👋 Welcome. Please upload **NMS Log** and **RFCOMM** files in the sidebar.")
