import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(page_title="KAVACH SENTINEL PRO", layout="wide", initial_sidebar_state="expanded")

# --- Custom Vivid Styling ---
st.markdown("""
    <style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #ffffff;
    }
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.3);
    }
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px 10px 0px 0px;
        padding: 10px 20px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4facfe !important;
        border-bottom: 2px solid #00f2fe !important;
    }
    h1, h2, h3 {
        color: #00f2fe !important;
        font-family: 'Trebuchet MS', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Header Section ---
col_head, col_logo = st.columns([4, 1])
with col_head:
    st.title("🛡️ KAVACH SENTINEL: COMMAND CENTER")
    st.write("Real-time RF Diagnostic & Network Health Monitor")

# --- Sidebar: File Uploads ---
with st.sidebar:
    st.header("📂 Data Source")
    rfcomm_file = st.file_uploader("Upload RFCOMM CSV", type="csv")
    trnmsnma_file = st.file_uploader("Upload TRNMSNMA CSV", type="csv")
    st.divider()
    st.info("System Status: **ACTIVE**" if rfcomm_file else "System Status: **AWAITING DATA**")

def load_data(rf_file, tr_file):
    rf_df = pd.read_csv(rf_file)
    rf_df['Percentage'] = pd.to_numeric(rf_df['Percentage'], errors='coerce')
    rf_df['Loco Id'] = rf_df['Loco Id'].astype(str).str.strip()
    rf_df['Station Id'] = rf_df['Station Id'].astype(str).str.strip()
    
    tr_df = pd.read_csv(tr_file, low_memory=False)
    tr_df['Loco Id'] = tr_df['Loco Id'].astype(str).str.strip()
    return rf_df, tr_df

if rfcomm_file and trnmsnma_file:
    rf_df, tr_df = load_data(rfcomm_file, trnmsnma_file)
    
    # --- Filter Section (Sidebar) ---
    st.sidebar.subheader("🎯 Diagnostic Filters")
    all_locos = sorted(rf_df['Loco Id'].unique())
    selected_locos = st.sidebar.multiselect("Select Loco IDs", all_locos, default=all_locos)
    
    all_stations = sorted(rf_df['Station Id'].unique())
    selected_stations = st.sidebar.multiselect("Select Stations", all_stations, default=all_stations)
    
    # Filter Data
    filtered_rf = rf_df[rf_df['Loco Id'].isin(selected_locos) & rf_df['Station Id'].isin(selected_stations)]
    
    # --- Top KPI Row ---
    avg_health = filtered_rf['Percentage'].mean()
    total_trains = len(selected_locos)
    total_stns = len(selected_stations)
    critical_issues = len(filtered_rf[filtered_rf['Percentage'] < 80])

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Network Health", f"{avg_health:.1f}%", delta=f"{avg_health-90:.1f}% vs Target")
    kpi2.metric("Active Locos", total_trains)
    kpi3.metric("Stations Monitored", total_stns)
    kpi4.metric("Critical Gaps", critical_issues, delta_color="inverse")

    st.markdown("---")

    # --- UI Tabs with Vivid Visuals ---
    tab1, tab2, tab3 = st.tabs(["⚡ Train Performance", "📡 Station Analysis", "🧬 Diagnostic Matrix"])

    with tab1:
        st.subheader("Locomotive Communication Profiles")
        train_summary = filtered_rf.groupby('Loco Id')['Percentage'].mean().reset_index()
        fig_train = px.bar(train_summary, x='Loco Id', y='Percentage', 
                           color='Percentage', color_continuous_scale='Turbo',
                           template="plotly_dark", title="Avg Health by Loco ID")
        fig_train.update_xaxes(type='category')
        st.plotly_chart(fig_train, use_container_width=True)
        
        # Diagnostic Error Cards
        bad_trains = train_summary[train_summary['Percentage'] < 90]
        if not bad_trains.empty:
            cols = st.columns(len(bad_trains))
            for i, row in enumerate(bad_trains.itertuples()):
                with cols[i % 3]:
                    st.error(f"**Loco {row._1}**\n\nHealth: {row.Percentage:.1f}%")

    with tab2:
        st.subheader("Trackside Station Reliability")
        station_summary = filtered_rf.groupby('Station Id')['Percentage'].mean().reset_index()
        fig_stn = px.line(station_summary, x='Station Id', y='Percentage', markers=True,
                          template="plotly_dark", title="Network Coverage Consistency")
        fig_stn.update_traces(line_color='#00f2fe', marker=dict(size=10, color="#fbc2eb"))
        fig_stn.update_xaxes(type='category')
        st.plotly_chart(fig_stn, use_container_width=True)

    with tab3:
        st.subheader("System Interconnectivity Matrix")
        pivot_df = filtered_rf.pivot_table(index='Loco Id', columns='Station Id', values='Percentage', aggfunc='mean')
        
        fig_heat = px.imshow(pivot_df, text_auto=".1f", 
                             color_continuous_scale='RdYlGn',
                             template="plotly_dark",
                             aspect="auto")
        
        fig_heat.update_yaxes(type='category', title="Train ID")
        fig_heat.update_xaxes(type='category', title="Station ID")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.info("💡 **Sentinel Tip:** Look for solid vertical red lines to identify faulty Trackside TCCs.")

    # Data Table Styling
    with st.expander("📝 View Detailed Audit Logs"):
        st.dataframe(filtered_rf.style.background_gradient(cmap='RdYlGn', subset=['Percentage']))

else:
    st.warning("⚡ **Sentinel System Offline:** Please upload the NMS and RFCOMM logs in the sidebar to begin diagnostic scan.")
