import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="TCAS Health Diagnostic Dashboard", layout="wide")

st.title("📡 TCAS Health Diagnostic Dashboard")
st.markdown("""
Analyze RF Communication health to distinguish between **Train TCAS** and **Station TCAS** issues.
- **Hardware Issue:** Usually zero or near-zero communication (Complete failure).
- **Software Issue:** Intermittent drops or lower percentage (Logic/Protocol failure).
""")

# --- Sidebar: File Uploads ---
st.sidebar.header("1. Upload Data")
rfcomm_file = st.sidebar.file_uploader("Upload RFCOMM CSV", type="csv")
trnmsnma_file = st.sidebar.file_uploader("Upload TRNMSNMA CSV", type="csv")

def load_data(rf_file, tr_file):
    # Load RFCOMM
    rf_df = pd.read_csv(rf_file)
    rf_df['Percentage'] = pd.to_numeric(rf_df['Percentage'], errors='coerce')
    
    # CRITICAL: Convert Loco Id to String to treat as a NAME/Label
    rf_df['Loco Id'] = rf_df['Loco Id'].astype(str).str.strip()
    rf_df['Station Id'] = rf_df['Station Id'].astype(str).str.strip()
    
    # Load TRNMSNMA
    tr_df = pd.read_csv(tr_file, low_memory=False)
    tr_df['Loco Id'] = tr_df['Loco Id'].astype(str).str.strip()
    
    return rf_df, tr_df

if rfcomm_file and trnmsnma_file:
    rf_df, tr_df = load_data(rfcomm_file, trnmsnma_file)
    
    # --- Filter Section ---
    st.sidebar.subheader("2. Filters")
    all_locos = sorted(rf_df['Loco Id'].unique())
    selected_locos = st.sidebar.multiselect("Select Train Nos", all_locos, default=all_locos)
    
    all_stations = sorted(rf_df['Station Id'].unique())
    selected_stations = st.sidebar.multiselect("Select Stations", all_stations, default=all_stations)
    
    # Filter Data
    filtered_rf = rf_df[rf_df['Loco Id'].isin(selected_locos) & rf_df['Station Id'].isin(selected_stations)]
    
    # --- Metrics Logic ---
    train_summary = filtered_rf.groupby('Loco Id')['Percentage'].mean().reset_index()
    station_summary = filtered_rf.groupby('Station Id')['Percentage'].mean().reset_index()

    # --- UI Tabs ---
    tab1, tab2, tab3 = st.tabs(["🚂 Train Context", "🏢 Station Context", "📊 Health Matrix"])

    with tab1:
        st.subheader("Train Health Analysis")
        # Treat Loco Id as categorical for the axis
        fig_train = px.bar(train_summary, x='Loco Id', y='Percentage', color='Percentage',
                           color_continuous_scale='RdYlGn', range_color=[0, 100],
                           title="Performance of Individual Trains across all Stations")
        fig_train.update_xaxes(type='category') # Ensures all 5 digits show as labels
        st.plotly_chart(fig_train, use_container_width=True)
        
        # Diagnostic Advice
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
                         color_continuous_scale='RdYlGn', range_color=[0, 100],
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
        # Pivot table for heatmap
        pivot_df = filtered_rf.pivot_table(index='Loco Id', columns='Station Id', values='Percentage', aggfunc='mean')
        
        # Heatmap with categorical axes
        fig_heat = px.imshow(pivot_df, text_auto=".1f", color_continuous_scale='RdYlGn',
                             labels=dict(x="Station ID", y="Train ID (Loco)", color="Health %"),
                             title="Detailed Health Matrix")
        
        # Explicitly setting y-axis to category to show all 5 digits clearly
        fig_heat.update_yaxes(type='category')
        fig_heat.update_xaxes(type='category')
        
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.markdown("""
        **How to Diagnose:**
        * **Horizontal Red Row:** This Train is failing at **all** stations. The problem is in the **Train TCAS Hardware/Software**.
        * **Vertical Red Column:** This Station is failing for **all** trains. The problem is in the **Station TCAS Hardware/Software**.
        * **Single Red Cell:** Likely a temporary environmental interference during that specific passage.
        """)

    # Data Table
    with st.expander("Show Raw Data Table"):
        st.write(filtered_rf)

else:
    st.info("Please upload both CSV files to generate the diagnostic dashboard.")
