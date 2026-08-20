import streamlit as st
import json
from google import genai
from google.genai import types
import os

# Ρύθμιση σελίδας
st.set_page_config(page_title="Sneakerness Video Studio", layout="wide")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Αυτόνομη γεννήτρια σεναρίων & video-composition οδηγιών")

# API Key check
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# --- 1. Ο Σκηνοθέτης (Creative Engine) ---
def generate_script(brand, model, colorway):
    prompt = f"""Είσαι ο σκηνοθέτης του Sneakerness.eu. Φτιάξε ένα σενάριο 16 δευτερολέπτων για {brand} {model} σε {colorway}.
    Θέλω φαντασία! Πρότεινε concepts που θυμίζουν κινηματογραφικό μοντάζ από κινητό.
    Επίστρεψε JSON με: "concept", "mood", "scenes" (λίστα με 3 σκηνές), "music_vibe", "overlay_text"."""
    
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

# --- 2. UI της εφαρμογής ---
col1, col2 = st.columns([1, 1])

with col1:
    brand = st.text_input("Brand")
    model = st.text_input("Model")
    colorway = st.text_input("Colorway")
    
    if st.button("🚀 Σκηνοθέτησε το Βίντεο"):
        if brand and model:
            with st.spinner("Η φαντασία του Sneakerness δουλεύει..."):
                script = generate_script(brand, model, colorway)
                st.session_state["script"] = script
                st.rerun()

# --- 3. Προβολή Σεναρίου ---
if "script" in st.session_state:
    script = st.session_state["script"]
    with col2:
        st.success(f"Concept: {script['concept']}")
        st.write(f"**Mood:** {script['mood']}")
        st.write(f"**Μουσική:** {script['music_vibe']}")
        st.write(f"**Κείμενο:** {script['overlay_text']}")
        
        for scene in script['scenes']:
            st.info(f"Σκηνή {scene['time']}: {scene['action']} (Κάμερα: {scene['camera']})")
            
        st.download_button("📥 Κατέβασμα JSON Σεναρίου", json.dumps(script), file_name="script.json")
