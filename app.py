import streamlit as st
import numpy as np
import requests
import math
import pandas as pd
import plotly.graph_objects as go

# --- Fetch Hourly Weather Data ---
def get_hourly_weather(lat, lon, hours):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=windspeed_10m,winddirection_10m&windspeed_unit=ms&forecast_days=14"
        response = requests.get(url)
        data = response.json()
        
        wind_speeds = data['hourly']['windspeed_10m'][:hours]
        wind_dirs = data['hourly']['winddirection_10m'][:hours]
        
        wind_x = np.zeros(hours)
        wind_y = np.zeros(hours)
        
        for i in range(hours):
            speed = wind_speeds[i]
            direction = wind_dirs[i]
            rad = math.radians(direction)
            wind_x[i] = -speed * math.sin(rad)
            wind_y[i] = -speed * math.cos(rad)
            
        return wind_x, wind_y, wind_speeds, wind_dirs
    except Exception as e:
        st.error("⚠️ Error fetching weather data. Using zero wind values.")
        return np.zeros(hours), np.zeros(hours), np.zeros(hours), np.zeros(hours)

# --- UI Setup ---
st.set_page_config(page_title="Oil Spill Trajectory Model", layout="wide")
st.title("🌊 Dynamic Oil Spill Trajectory Model")
st.markdown("Simulate oil spill trajectories using real-time hourly meteorological data on an interactive geographic map.")

# --- Sidebar Inputs ---
st.sidebar.header("📍 Spill Location")
# Default coordinates set to the sea off the coast of Kuwait
lat = st.sidebar.number_input("Latitude", value=29.1500, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=48.2500, format="%.4f")

st.sidebar.markdown("---")
st.sidebar.header("🛢️ Spill Characteristics")

oil_types = {
    "Light Oil (e.g., Diesel)": {"diffusion": 200.0, "color": "orange"},
    "Medium Oil (Crude Oil)": {"diffusion": 100.0, "color": "saddlebrown"},
    "Heavy Oil (Bunker C)": {"diffusion": 30.0, "color": "black"}
}

selected_oil = st.sidebar.selectbox("Select Oil Type:", list(oil_types.keys()))
diffusion_rate = oil_types[selected_oil]["diffusion"]
oil_color = oil_types[selected_oil]["color"]

# New Volume Input
spill_volume = st.sidebar.number_input("Spill Volume (Barrels)", min_value=10, max_value=100000, value=1000, step=100)
# Scale particles based on volume (min 200, max 3000 for visual performance)
num_particles = min(3000, max(200, int(spill_volume / 2)))

st.sidebar.markdown("---")
st.sidebar.header("🌊 Ocean Currents")
current_x = st.sidebar.slider("Current Speed (East/West m/s)", -2.0, 2.0, 0.5)
current_y = st.sidebar.slider("Current Speed (North/South m/s)", -2.0, 2.0, 0.1)

time_steps = st.sidebar.slider("Simulation Duration (Hours)", 10, 300, 100)

# --- Fetch Weather ---
wind_x_arr, wind_y_arr, speeds_arr, dirs_arr = get_hourly_weather(lat, lon, time_steps)
avg_speed = np.mean(speeds_arr)

st.info(f"📊 *Average Expected Wind Speed over {time_steps} hours:* {avg_speed:.2f} m/s. (Model reads hour-by-hour dynamic changes)")

# --- Physics & Math Simulation ---
dt = 3600 # seconds in an hour
wind_factor = 0.03 # 3% wind drift factor

v_current = np.array([current_x, current_y])
positions = np.zeros((time_steps, num_particles, 2))

# Calculate movement
for t in range(1, time_steps):
    current_wind_v = np.array([wind_x_arr[t], wind_y_arr[t]])
    v_advection = v_current + (wind_factor * current_wind_v)
    random_walk = np.random.normal(0, np.sqrt(2 * diffusion_rate * dt), (num_particles, 2))
    positions[t] = positions[t-1] + (v_advection * dt) + random_walk

# --- Convert Coordinates (Meters to Lat/Lon) ---
lat_factor = 111320.0
lon_factor = 111320.0 * math.cos(math.radians(lat))

# Calculate Center of Mass (The main trajectory line)
com_x = np.mean(positions[:, :, 0], axis=1)
com_y = np.mean(positions[:, :, 1], axis=1)
com_lons = lon + (com_x / lon_factor)
com_lats = lat + (com_y / lat_factor)

# Calculate Final Position of all particles (The spill spread)
final_x = positions[-1, :, 0]
final_y = positions[-1, :, 1]
final_lons = lon + (final_x / lon_factor)
final_lats = lat + (final_y / lat_factor)

# --- Interactive Map Plotting (Plotly) ---
fig = go.Figure()

# 1. Final Oil Spread (Particles)
fig.add_trace(go.Scattermapbox(
    mode="markers",
    lon=final_lons,
    lat=final_lats,
    marker=dict(size=4, color=oil_color, opacity=0.6),
    name=f"Final Spread ({spill_volume} bbl)"
))

# 2. Trajectory Line (Center of Mass)
fig.add_trace(go.Scattermapbox(
    mode="lines",
    lon=com_lons,
    lat=com_lats,
    line=dict(width=3, color='red'),
    name="Trajectory Path"
))

# 3. Spill Origin Point
fig.add_trace(go.Scattermapbox(
    mode="markers",
    lon=[lon],
    lat=[lat],
    marker=dict(size=12, color='red', symbol='circle'),
    name="Spill Origin"
))

# Map Layout Options
fig.update_layout(
    mapbox=dict(
        style="open-street-map", # Real geographic map
        center=dict(lon=lon, lat=lat),
        zoom=9
    ),
    margin=dict(l=0, r=0, b=0, t=40),
    title="Interactive Geospatial Spill Map"
)

st.plotly_chart(fig, use_container_width=True)
