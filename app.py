import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from streamlit_js_eval import get_geolocation
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
st.set_page_config(page_title="LPG Smart Finder", layout="wide")

# --- 1. DATA GENERATION (The 100 Members) ---
@st.cache_data
def get_lpg_data():
    np.random.seed(42)
    brands = ['Indane', 'HP Gas', 'Bharat Gas', 'Reliance']
    # Default Center: Hyderabad
    base_lat, base_lon = 17.3850, 78.4867
    
    data = {
        'ID': [f"LPG-{i:03d}" for i in range(1, 101)],
        'Agency_Name': [f"{brand} {np.random.choice(['Service', 'Point', 'Center'])} {i}" for i, brand in enumerate([np.random.choice(brands) for _ in range(100)], 1)],
        'Brand': [np.random.choice(brands) for _ in range(100)],
        'lat': base_lat + np.random.uniform(-0.1, 0.1, 100),
        'lon': base_lon + np.random.uniform(-0.1, 0.1, 100),
        'Stock': [np.random.randint(0, 50) for _ in range(100)],
    }
    return pd.DataFrame(data)

df = get_lpg_data()

# --- 2. USER LOCATION ---
st.title("⛽ LPG Smart Finder (Pure Python)")
loc = get_geolocation()

if loc:
    u_lat, u_lon = loc['coords']['latitude'], loc['coords']['longitude']
else:
    # Fallback to Hyderabad Center
    u_lat, u_lon = 17.3850, 78.4867
    st.info("Using default city location. Enable GPS for better accuracy.")

# Calculate real-time distance
df['Distance_km'] = np.round(np.sqrt((df['lat'] - u_lat)**2 + (df['lon'] - u_lon)**2) * 111, 2)

# --- 3. UI LAYOUT ---
sidebar = st.sidebar
brand_choice = sidebar.selectbox("Filter by Brand", ["All"] + list(df['Brand'].unique()))

# Filtered View
display_df = df if brand_choice == "All" else df[df['Brand'] == brand_choice]
display_df = display_df.sort_values('Distance_km').head(10)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Map of Nearest Stations")
    st.map(display_df[['lat', 'lon']])

with col2:
    st.subheader("Nearby Availability")
    for _, row in display_df.iterrows():
        status = "🟢 In Stock" if row['Stock'] > 5 else "🔴 Low/No Stock"
        st.markdown(f"**{row['Agency_Name']}** ({row['Distance_km']} km)")
        st.caption(f"Brand: {row['Brand']} | Stock: {row['Stock']} | {status}")
        st.divider()

# --- 4. THE AI AGENT (Direct LLM) ---
st.subheader("💬 Ask the LPG Assistant")
user_msg = st.text_input("e.g., 'Is there any Indane gas near me with more than 10 cylinders?'")

if user_msg:
    # Context Injection: We give the LLM the top 5 nearest results to 'see'
    context = display_df[['Agency_Name', 'Brand', 'Distance_km', 'Stock']].to_string()
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    You are an LPG assistant. Here is the current stock data near the user:
    {context}
    
    The user's question: {user_msg}
    Answer concisely based ONLY on the data provided above.
    """
    
    with st.spinner("AI is thinking..."):
        response = model.generate_content(prompt)
        st.write(f"**Assistant:** {response.text}")