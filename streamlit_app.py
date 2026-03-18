import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="TCAS Health Diagnostic Dashboard", layout="wide")

# 2. BEAUTIFUL CUSTOM CSS
st.markdown("""
    <style>
    /* Styling the top Toolbar area (Share, Star, Edit, etc.) */
    header[data-testid="stHeader"] {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
    }
    
    /* Main Background of the App */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1e2a38;
        color: white;
    }
    
    /* Metrics / Alert Boxes styling */
    .stAlert {
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Titles and text colors */
    h1, h2, h3 {
        color: #1e2a38;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
    }

    /* Styling Tabs to be colorful */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #4b6cb7 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. HEADER
st.title("📡 TCAS Health Diagnostic Dashboard")
st.markdown("""
<div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid #4b6cb7; margin-bottom: 20px;">
    Analyze RF Communication health to distinguish between <b>Train TCAS</b> and <b>Station TCAS</b> issues.<br>
    - <span style="color: red; font-weight: bold;">Hardware Issue:</span> Usually zero or near-zero communication.<br>
    - <span style="color: orange; font-weight: bold;">Software Issue:</span> Intermittent drops or lower percentage.
</div>
""", unsafe_allow_html=True)

# --- Sidebar: File Uploads ---
st.sidebar.header("📂 1. Upload Data")
rfcomm_file = st.sidebar.file_uploader("Upload RFCOMM CSV", type="csv")
trnmsnma_file = st.sidebar.file_uploader("Upload TRNMSNMA CSV", type="csv")

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
    
    st.sidebar.subheader("🎯 2. Filters")
    all_locos = sorted(rf_df['Loco Id'].unique())
    selected_locos = st.sidebar.multiselect("Select Train Nos", all_locos, default=all_locos)
    
    all_stations = sorted(rf_df['Station Id'].unique())
    selected_stations = st.sidebar.multiselect("Select Stations", all_stations, default=all_stations)
    
    filtered_rf = rf_df[rf_df['Loco Id'].isin(selected_locos) & rf_df['Station Id'].isin(selected_stations)]
    
    train_summary = filtered_rf.groupby('Loco Id')['Percentage'].mean().reset_index()
    station_summary = filtered_rf.groupby('Station Id')['Percentage'].mean().reset_index()

    tab1, tab2, tab3 = st.tabs(["🚂 Train Context", "🏢 Station Context", "📊 Health Matrix"])

    with tab1:
        st.subheader("Train Health Analysis")
        fig_train = px.bar(train_summary, x='Loco Id', y='Percentage', color='Percentage',
                           color_continuous_scale='Turbo', range_color=[0, 100],
                           title="Performance of Individual Trains across all Stations")
        fig_train.update_xaxes(type='category')
        st.plotly_chart(fig_train, use_container_width=True)
        
        bad_trains = train_summary[train_summary['Percentage'] < 90]
        if not bad_trains.empty:
            for _, row in bad_trains.iterrows():
                fault = "HARDWARE" if row['Percentage'] < 30 else "SOFTWARE/SIGNAL"
                st.error(f"⚠️ Train {row['Loco Id']} failing! Health: {row['Percentage']:.1f}%. Possible {fault} fault.")
        else:
            st.success("All trains show healthy communication (>90%).")

    with tab2:
        st.subheader("Station Health Analysis")
        fig_stn = px.bar(station_summary, x='Station Id', y='Percentage', color='Percentage',
                         color_continuous_scale='Viridis', range_color=[0, 100],
                         title="Performance of Stations across all Trains")
        fig_stn.update_xaxes(type='category')
        st.plotly_chart(fig_stn, use_container_width=True)

        bad_stns = station_summary[station_summary['Percentage'] < 90]
        if not bad_stns.empty:
            for _, row in bad_stns.iterrows():
                fault = "HARDWARE" if row['Percentage'] < 30 else "SOFTWARE/SIGNAL"
                st.warning(f"🚨 Station {row['Station Id']} failing! Health: {row['Percentage']:.1f}%. Possible {fault} fault.")
        else:
            st.success("All stations show healthy communication.")

    with tab3:
        st.subheader("Train vs. Station Communication Matrix")
        pivot_df = filtered_rf.pivot_table(index='Loco Id', columns='Station Id', values='Percentage', aggfunc='mean')
        
        fig_heat = px.imshow(pivot_df, text_auto=".1f", color_continuous_scale='RdYlGn',
                             labels=dict(x="Station ID", y="Train ID (Loco)", color="Health %"),
                             title="Detailed Health Matrix")
        
        fig_heat.update_yaxes(type='category')
        fig_heat.update_xaxes(type='category')
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.info("""
        **How to Diagnose:**
        * **Horizontal Red Row:** This Train is failing everywhere (Train TCAS issue).
        * **Vertical Red Column:** This Station is failing for everyone (Station TCAS issue).
        """)

    with st.expander("📁 View Detailed Raw Data Table"):
        st.dataframe(filtered_rf.style.background_gradient(cmap='RdYlGn', subset=['Percentage']))

else:
    st.info("👋 Welcome! Please upload your CSV files in the sidebar to generate the diagnostic visuals.")
