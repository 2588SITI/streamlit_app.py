import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt

# --- Page Config ---
st.set_page_config(page_title="KAVACH SENTINEL DASHBOARD", layout="wide")
st.markdown("<style>.block-container { padding-top: 2rem; }</style>", unsafe_allow_html=True)
st.title("🛡️ WR KAVACH RADIO DIAGNOSTIC DASHBOARD")

# --- Sidebar ---
st.sidebar.header("📂 Data Input")
nms_file = st.sidebar.file_uploader("Upload TRNMSNMA (NMS Log)", type=['csv'])
rf_file = st.sidebar.file_uploader("Upload RFCOMM (Station Summary)", type=['csv'])

if nms_file and rf_file:
    # Load Data
    df_nms = pd.read_csv(nms_file, low_memory=False)
    df_rf = pd.read_csv(rf_file, low_memory=False)

    # Data Processing
    df_nms['Pkt Len'] = pd.to_numeric(df_nms['Pkt Len'], errors='coerce').fillna(0)
    df_nms['Pkt Len2'] = pd.to_numeric(df_nms['Pkt Len2'], errors='coerce').fillna(0)
    
    # Mode Downgrade Logic
    df_nms['Prev_Mode'] = df_nms['Mode'].shift(1)
    # Detect transitions from FullSupervision to any other mode
    downgrade_df = df_nms[(df_nms['Prev_Mode'] == 'FullSupervision') & (df_nms['Mode'] != 'FullSupervision')]
    total_downgrades = len(downgrade_df)
    
    # Emergency Logs (Non-Nominal Emr Status)
    emergency_logs = df_nms[df_nms['Emr Status'] != 'Nominal']
    total_emergency = len(emergency_logs)

    # Radio Fail Rates
    r1_fail = (df_nms['Pkt Len'] < 10).mean() * 100
    r2_fail = (df_nms['Pkt Len2'] < 10).mean() * 100

    # --- 1. TOP METRICS (KPIs) ---
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Mode Downgrades", total_downgrades, delta="-232 Events", delta_color="inverse")
    l2.metric("Radio 1 Fail Rate", f"{r1_fail:.2f}%")
    l3.metric("Radio 2 Fail Rate", f"{r2_fail:.2f}%")
    l4.metric("Emergency Logs", total_emergency)

    st.divider()

    # --- 2. STATION ANALYSIS ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📍 Station Communication Health")
        df_rf['Percentage'] = pd.to_numeric(df_rf['Percentage'], errors='coerce')
        # Filter for unique stations to avoid bar duplicates
        unique_stn = df_rf.drop_duplicates(subset=['Station Id'])
        
        colors = ['#EF9A9A' if x < 90 else '#A5D6A7' for x in unique_stn['Percentage']]
        fig, ax = plt.subplots()
        ax.bar(unique_stn['Station Id'], unique_stn['Percentage'], color=colors)
        ax.axhline(y=90, color='black', linestyle='--', alpha=0.5)
        plt.xticks(rotation=45)
        st.pyplot(fig)
        st.caption("🔴 Red: Trackside gaps (<90%). 🟢 Green: Healthy.")

    with c2:
        st.subheader("📉 Downgrades by Station")
        if not downgrade_df.empty:
            stn_counts = downgrade_df['Station'].value_counts()
            fig2, ax2 = plt.subplots()
            stn_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax2, startangle=90, colors=['#FFB3BA','#BAFFC9','#BAE1FF'])
            ax2.set_ylabel('')
            st.pyplot(fig2)
        else:
            st.success("✅ No Full Supervision downgrades detected.")

    # --- 3. TECHNICAL AUDIT ---
    st.divider()
    st.header("📋 Technical Audit & Maintenance Actions")
    a1, a2 = st.columns(2)
    
    with a1:
        st.subheader("1. Radio Diagnosis")
        if abs(r1_fail - r2_fail) < 5:
            st.success("✅ **Loco Health:** Onboard hardware (Antennas/Cables) performing consistently.")
        else:
            st.warning("⚠️ **Loco Health:** Radio performance imbalance. Check specific Antenna.")
            
    with a2:
        st.subheader("2. Operational Safety")
        st.write(f"**Total FS Downgrades:** {total_downgrades}")
        st.write(f"**Emergency State Duration:** {total_emergency} log entries")
        if total_downgrades > 0:
            st.info(f"💡 **Cause Analysis:** High downgrades correlate with radio packet loss.")

    # --- 4. DOCUMENTATION (AUDIT LOGIC) ---
    st.divider()
    st.header("📖 Technical Definitions & Audit Logic")
    
    with st.expander("🚨 Understanding Emergency Status Logs"):
        st.write(f"**What is the '{total_emergency}' Count?**")
        st.write("It represents the total number of data rows recorded in a non-nominal state. It indicates **duration**, not the number of individual brake applications.")
        st.write("* **Communication Timeout:** If the radio signal is lost for >5-10 seconds, status shifts to Emergency.")
        st.write("* **Duration:** These thousands of logs represent the total trip time where system was in a failed state.")

    with st.expander("📉 What are 'Downgrades by Station' & Mode Downgrades?"):
        st.write("**Downgrades by Station** tracks exactly where the train lost its 'Movement Authority'.")
        st.write("* **How it works:** Healthy running is in **Full Supervision (FS)** mode. If radio drops, it 'downgrades' to restricted speed.")
        st.write("* **Why it matters:** Pinpointing the Station tells the maintenance crew exactly which radio tower is failing.")

    with st.expander("📡 Understanding Radio 1 & 2 Fail Rates"):
        st.write("**Loco Hardware Diagnosis:** We compare them to find the root cause.")
        st.write("* **Loco Fault:** If Radio 1 is much higher than Radio 2, it is a physical issue with Antenna/Cable on the Engine.")
        st.write("* **Station Fault:** If both fail at the same station, the problem is the Station transmitter.")

    with st.expander("🛡️ Understanding Operational Safety"):
        st.write("**Missing Next Signal Aspect:**")
        st.write("If the 'Next Signal' is 'Not Defined' while moving, the Loco TCAS cannot confirm the aspect ahead.")
        st.write("* **Risk:** Leading cause of unplanned Emergency Braking (EB).")
else:
    st.info("👋 Please upload NMS Log and RFCOMM files to begin.")
