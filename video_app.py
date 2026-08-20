import streamlit as st
import json
from google import genai
from google.genai import types
import os
import time

# Ρύθμιση σελίδας
st.set_page_config(page_title="Sneakerness Video Studio", layout="centered")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Αυτόνομη γεννήτρια σεναρίων & video-composition οδηγιών")

# API Key check
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ Δεν βρέθηκε το GEMINI_API_KEY στα Secrets / .env!")
    st.stop()

client = genai.Client(api_key=api_key)

# 1. INITIALIZE SESSION STATE
if "brand_val" not in st.session_state: st.session_state["brand_val"] = ""
if "model_val" not in st.session_state: st.session_state["model_val"] = ""
if "colorway_val" not in st.session_state: st.session_state["colorway_val"] = ""
if "uploader_key" not in st.session_state: st.session_state["uploader_key"] = 0

def clear_all_fields():
    st.session_state["brand_val"] = ""
    st.session_state["model_val"] = ""
    st.session_state["colorway_val"] = ""
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1
    if "script" in st.session_state: del st.session_state["script"]

# 2. UI & ACTIONS
col_header, col_reset = st.columns([3, 1])
with col_reset:
    st.write("")
    if st.button("🧹 Νέο Παπούτσι / Clear"):
        clear_all_fields()
        st.rerun()

col_up, col_preview = st.columns([2, 1])
with col_up:
    uploaded_file = st.file_uploader(
        "📷 Ανέβασε φωτογραφία παπουτσιού", 
        type=["jpg", "jpeg", "png", "webp"],
        key=f"uploader_{st.session_state['uploader_key']}"
    )
with col_preview:
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Προεπισκόπηση", use_container_width=True)

# 3. AUTO-ANALYZE & SCRIPT GENERATION FUNCTION
def generate_video_script_from_image(image_bytes, mime_type):
    sys_instruction = """Είσαι ο βραβευμένος σκηνοθέτης διαφημίσεων του Sneakerness.eu. 
    Αναλύεις τη φωτογραφία του παπουτσιού και δημιουργείς ένα πρωτότυπο, κινηματογραφικό σενάριο 16 δευτερολέπτων για TikTok/Reels. 
    Επιστρέφεις αποκλειστικά έγκυρο JSON."""
    
    prompt = """Examine the provided sneaker image. Identify the brand, model, and colorway, and create a 16-second cinematic video script.
    
    Return strict JSON matching this schema:
    {
        "brand": "Detected Brand",
        "model": "Detected Model",
        "colorway": "Detected Colorway",
        "concept": "Unique creative concept name",
        "mood": "Visual mood/lighting description",
        "scenes": [
            {"time": "0-5s", "camera": "...", "action": "..."},
            {"time": "5-11s", "camera": "...", "action": "..."},
            {"time": "11-16s", "camera": "...", "action": "..."}
        ],
        "text_overlay": "Engaging short text for video",
        "music_vibe": "Audio style description"
    }"""
    
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt
    ]

    models_to_try = ["gemini-2.5-flash", "gemini-3.6-flash"]
    
    for model_item in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_item,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                clean_txt = response.text.strip()
                if clean_txt.startswith("```json"): clean_txt = clean_txt[7:]
                if clean_txt.startswith("```"): clean_txt = clean_txt[3:]
                if clean_txt.endswith("```"): clean_txt = clean_txt[:-3]
                return json.loads(clean_txt.strip())
        except Exception as e:
            time.sleep(1)
            
    raise Exception("All models failed to generate response.")

# Κουμπί Αυτοματισμού
if st.button("🚀 Αυτόματη Ανίχνευση & Σκηνοθεσία Βίντεο", type="primary"):
    if not uploaded_file:
        st.warning("⚠️ Παρακαλώ ανέβασε πρώτα μια φωτογραφία παπουτσιού!")
    else:
        with st.spinner("Ο σκηνοθέτης αναλύει το παπούτσι και σκέφτεται το σενάριο..."):
            try:
                img_bytes = uploaded_file.getvalue()
                mime = "image/jpeg"
                if uploaded_file.name.lower().endswith(".png"): mime = "image/png"
                elif uploaded_file.name.lower().endswith(".webp"): mime = "image/webp"

                script = generate_video_script_from_image(img_bytes, mime)
                st.session_state["script"] = script
                st.session_state["brand_val"] = script.get("brand", "")
                st.session_state["model_val"] = script.get("model", "")
                st.session_state["colorway_val"] = script.get("colorway", "")
                st.rerun()
            except Exception as err:
                st.error(st.error(f"❌ Σφάλμα ανάλυσης: {str(err)}"))

# 4. INPUT FIELDS
col1, col2, col3 = st.columns(3)
with col1: 
    brand = st.text_input("Brand", value=st.session_state["brand_val"])
with col2: 
    model_name = st.text_input("Model", value=st.session_state["model_val"])
with col3: 
    colorway = st.text_input("Colorway", value=st.session_state["colorway_val"])

# 5. ΠΡΟΒΟΛΗ ΣΕΝΑΡΙΟΥ
if "script" in st.session_state:
    script = st.session_state["script"]
    st.markdown("---")
    st.success(f"💡 **Concept:** {script.get('concept', '')}")
    st.write(f"**Mood:** {script.get('mood', '')}")
    st.write(f"**Μουσική:** {script.get('music_vibe', '')}")
    st.write(f"**Κείμενο (Overlay):** {script.get('text_overlay', '')}")
    
    st.markdown("#### 🎬 Σκηνές Βίντεο (16s Timeline):")
    for scene in script.get('scenes', []):
        st.info(f"**{scene.get('time')}** | Κίνηση: {scene.get('action')} *(Κάμερα: {scene.get('camera')})*")
        
    st.download_button("📥 Κατέβασμα JSON Σεναρίου", json.dumps(script, ensure_ascii=False, indent=2), file_name="video_script.json")
