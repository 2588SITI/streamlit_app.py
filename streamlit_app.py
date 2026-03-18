import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="TCAS Health Diagnostic Dashboard", layout="wide")

st.title("📡 TCAS Health Diagnostic Dashboard")
st.markdown("""
This dashboard analyzes RF Communication between Trains (Locos) and Stations to identify if faults lie in the 
**Train TCAS** or **Station TCAS** hardware/software.
""")

# --- Sidebar: File Uploads ---
st.sidebar.header("Upload Data")
rfcomm_file = st.sidebar.file_uploader("Upload RFCOMM CSV (e.g., ALL_RFCOMM_007.csv)", type="csv")
trnmsnma_file = st.sidebar.file_uploader("Upload TRNMSNMA CSV (e.g., ALL_TRNMSNMA_0007.csv)", type="csv")

def load_data(rf_file, tr_file):
    rf_df = pd.read_csv(rf_file)
    # Data Cleaning for RFCOMM
    rf_df['Percentage'] = pd.to_numeric(rf_df['Percentage'], errors='coerce')
    rf_df['Loco Id'] = rf_df['Loco Id'].astype(str)
    rf_df['Station Id'] = rf_df['Station Id'].astype(str)
    
    tr_df = pd.read_csv(tr_file, low_memory=False)
    tr_df['Loco Id'] = tr_df['Loco Id'].astype(str)
    tr_df['Station'] = tr_df['Station'].astype(str)
    
    return rf_df, tr_df

if rfcomm_file and trnmsnma_file:
    rf_df, tr_df = load_data(rfcomm_file, trnmsnma_file)
    
    # --- Filter Section ---
    st.sidebar.subheader("Filters")
    all_locos = sorted(rf_df['Loco Id'].unique())
    selected_locos = st.sidebar.multiselect("Select Train(s) [Loco Id]", all_locos, default=all_locos)
    
    all_stations = sorted(rf_df['Station Id'].unique())
    selected_stations = st.sidebar.multiselect("Select Station(s)", all_stations, default=all_stations)
    
    # Filtered Data
    mask = rf_df['Loco Id'].isin(selected_locos) & rf_df['Station Id'].isin(selected_stations)
    filtered_rf = rf_df[mask]
    
    # --- Metrics Calculation ---
    # Train Health (Average across all stations)
    train_health = filtered_rf.groupby('Loco Id')['Percentage'].mean().reset_index()
    # Station Health (Average across all trains)
    station_health = filtered_rf.groupby('Station Id')['Percentage'].mean().reset_index()

    # --- Layout: Main Tabs ---
    tab1, tab2, tab3 = st.tabs(["🚂 Train Analysis", "🏢 Station Analysis", "📊 Comparative Heatmap"])

    with tab1:
        st.subheader("Train TCAS Health Context")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_train = px.bar(train_health, x='Loco Id', y='Percentage', 
                               title="Average Communication Health per Train",
                               color='Percentage', color_continuous_scale='RdYlGn', range_color=[0, 100])
            st.plotly_chart(fig_train, use_container_width=True)
            
        with col2:
            st.write("**Train Diagnostics**")
            unhealthy_trains = train_health[train_health['Percentage'] < 95]
            if not unhealthy_trains.empty:
                for idx, row in unhealthy_trains.iterrows():
                    problem_type = "Hardware" if row['Percentage'] < 50 else "Software/Interference"
                    st.error(f"Loco {row['Loco Id']}: {row['Percentage']:.2f}% - Likely {problem_type} Issue")
            else:
                st.success("All selected trains performing well.")

    with tab2:
        st.subheader("Station TCAS Health Context")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_stn = px.bar(station_health, x='Station Id', y='Percentage', 
                             title="Average Communication Health per Station",
                             color='Percentage', color_continuous_scale='RdYlGn', range_color=[0, 100])
            st.plotly_chart(fig_stn, use_container_width=True)
            
        with col2:
            st.write("**Station Diagnostics**")
            unhealthy_stns = station_health[station_health['Percentage'] < 95]
            if not unhealthy_stns.empty:
                for idx, row in unhealthy_stns.iterrows():
                    problem_type = "Hardware" if row['Percentage'] < 50 else "Software/Interference"
                    st.warning(f"Station {row['Station Id']}: {row['Percentage']:.2f}% - Likely {problem_type} Issue")
            else:
                st.success("All selected stations performing well.")

    with tab3:
        st.subheader("Train vs. Station Communication Matrix")
        # Creating a pivot for the heatmap
        pivot_df = filtered_rf.pivot_table(index='Loco Id', columns='Station Id', values='Percentage', aggfunc='mean')
        fig_heat = px.imshow(pivot_df, text_auto=True, color_continuous_scale='RdYlGn', 
                             title="Health Matrix (%)", labels=dict(x="Station", y="Train", color="Health %"))
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.info("""
        **How to read this:**
        - A **Horizontal Red Line** indicates a specific Train failing at almost all stations (Train TCAS Issue).
        - A **Vertical Red Line** indicates a specific Station failing with almost all trains (Station TCAS Issue).
        """)

    # --- Detailed Packet Data (TRNMSNMA) ---
    with st.expander("View Detailed Transmission Packets (TRNMSNMA)"):
        st.dataframe(tr_df[tr_df['Loco Id'].isin(selected_locos)].head(100))

else:
    st.info("Please upload both RFCOMM and TRNMSNMA CSV files to begin the analysis.")
