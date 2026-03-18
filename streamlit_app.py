import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="KAVACH SENTINEL PRO", layout="wide")
st.title("🛡️ WR KAVACH RADIO DIAGNOSTIC & ROOT CAUSE SYSTEM")

# --- Sidebar ---
st.sidebar.header("📂 Data Input")
nms_file = st.sidebar.file_uploader("Upload TRNMSNMA (NMS Log)", type=['csv'])
rf_file = st.sidebar.file_uploader("Upload RFCOMM (Station Summary)", type=['csv'])

if nms_file and rf_file:
    # Load Data
    df_nms = pd.read_csv(nms_file, low_memory=False)
    df_rf = pd.read_csv(rf_file, low_memory=False)

    # Data Cleaning
    df_nms['Pkt Len'] = pd.to_numeric(df_nms['Pkt Len'], errors='coerce').fillna(0)
    df_nms['Pkt Len2'] = pd.to_numeric(df_nms['Pkt Len2'], errors='coerce').fillna(0)
    df_nms['Speed'] = pd.to_numeric(df_nms['Speed'], errors='coerce').fillna(0)
    df_rf['Percentage'] = pd.to_numeric(df_rf['Percentage'], errors='coerce')
    
    # Feature 1: Identify Downgrades
    df_nms['Prev_Mode'] = df_nms['Mode'].shift(1)
    downgrades = df_nms[(df_nms['Prev_Mode'] == 'FullSupervision') & (df_nms['Mode'] != 'FullSupervision')]
    
    # --- Metrics Section ---
    m1, m2, m3, m4 = st.columns(4)
    r1_fail = (df_nms['Pkt Len'] < 10).mean() * 100
    r2_fail = (df_nms['Pkt Len2'] < 10).mean() * 100
    
    m1.metric("FS Downgrades", len(downgrades))
    m2.metric("Radio 1 Health", f"{100-r1_fail:.1f}%")
    m3.metric("Radio 2 Health", f"{100-r2_fail:.1f}%")
    m4.metric("Avg. Station Health", f"{df_rf['Percentage'].mean():.1f}%")

    st.divider()

    # --- NEW IMPORTANT FEATURE: ROOT CAUSE DIAGNOSIS ---
    st.header("🔍 Intelligent Root Cause Diagnosis")
    
    col_diag, col_map = st.columns([1, 1])

    with col_diag:
        st.subheader("Automated Fault Labeling")
        # Logic to determine if Loco or Station is at fault
        diff = abs(r1_fail - r2_fail)
        low_stns = df_rf[df_rf['Percentage'] < 90]['Station Id'].unique()

        if diff > 15:
            st.error("🚩 **DIAGNOSIS: LOCO HARDWARE FAULT**")
            st.write(f"Radio 1 and Radio 2 show a performance gap of {diff:.1f}%. This usually indicates a loose RF cable, faulty antenna, or Radio module failure on the Locomotive.")
        elif len(low_stns) > 0:
            st.warning("🚩 **DIAGNOSIS: TRACKSIDE/STATION FAULT**")
            st.write(f"Both radios are failing similarly at stations: {', '.join(low_stns)}. The issue is likely the Station's TCC transmitter or signal shadowing.")
        else:
            st.success("✅ **DIAGNOSIS: SYSTEM HEALTHY**")
            st.write("No systemic hardware failures detected.")

    with col_map:
        st.subheader("Failure Heatmap (By Location)")
        # Identify where Packet Length was 0 (Packet Loss)
        loss_df = df_nms[df_nms['Pkt Len'] == 0]
        if not loss_df.empty:
            fig_loc = px.histogram(loss_df, x='Abs Loc', nbins=50, title="Packet Loss Frequency by Absolute Location",
                                  color_discrete_sequence=['#E74C3C'])
            st.plotly_chart(fig_loc, use_container_width=True)

    st.divider()

    # --- NEW IMPORTANT FEATURE: SPATIAL PERFORMANCE CORRELATION ---
    st.header("📈 Spatial Performance Correlation")
    st.write("This chart synchronizes Train Speed with Radio Reception to find the 'Dead Zones'.")
    
    # Creating a synchronized chart using Plotly
    fig = go.Figure()
    # Speed Line
    fig.add_trace(go.Scatter(x=df_nms.index, y=df_nms['Speed'], name="Speed (kmph)", line=dict(color='blue', width=1)))
    # Radio 1 Packets (Secondary Axis)
    fig.add_trace(go.Scatter(x=df_nms.index, y=df_nms['Pkt Len'], name="Radio 1 Pkt", line=dict(color='rgba(255, 0, 0, 0.3)', width=1), yaxis="y2"))
    
    fig.update_layout(
        xaxis_title="Log Timeline (Sequence)",
        yaxis=dict(title="Speed (kmph)"),
        yaxis2=dict(title="Packet Length", overlaying="y", side="right"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Filtered Table for Maintenance Audit ---
    st.subheader("📋 Maintenance Audit Checklist")
    audit_data = df_rf[df_rf['Percentage'] < 95][['Station Id', 'Loco Id', 'Percentage', 'Expected Count']]
    if not audit_data.empty:
        st.write("The following stations require **Immediate Antenna Alignment**:")
        st.table(audit_data.sort_values(by='Percentage'))
    else:
        st.success("No stations require immediate maintenance based on this log.")

else:
    st.info("Please upload both CSV files to unlock the Root Cause Diagnostic Engine.")
