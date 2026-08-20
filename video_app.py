import streamlit as st
import json
from google import genai
from google.genai import types
import os

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

# --- 1. Ο Σκηνοθέτης με Multimodal Υποστήριξη ---
def generate_script_with_vision(brand, model, colorway, image_bytes=None, mime_type="image/jpeg"):
    sys_instruction = """Είσαι ο βραβευμένος σκηνοθέτης διαφημίσεων του Sneakerness.eu. 
    Στόχος σου είναι να δημιουργείς φρέσκα, πρωτότυπα σενάρια 16 δευτερολέπτων για TikTok/Reels. 
    Αποφεύγεις τα κλισέ. Σκέφτεσαι 'out of the box'. 
    Επιστρέφεις πάντα ένα έγκυρο JSON."""
    
    prompt = f"""
    Δημιούργησε ένα δημιουργικό σενάριο 16 δευτερολέπτων για το sneaker: {brand} {model} ({colorway}).
    
    Κανόνες φαντασίας:
    1. Δώσε ένα μοναδικό 'Creative Concept' (π.χ. 'The Concrete Playground', 'Morning Zen', 'Midnight Runner').
    2. Πρότεινε 'Mood' (π.χ. Moody, Cinematic, High Energy, Minimalist).
    3. Χώρισε το βίντεο σε 3 σκηνές (0-5s, 5-11s, 11-16s) με αναλυτικές οδηγίες κίνησης κάμερας.
    4. Πρότεινε ένα κείμενο (Overlay Text) που να προκαλεί συναίσθημα.
    5. Πρότεινε το vibe της μουσικής.
    
    Επίστρεψε το αποτέλεσμα σε καθαρό JSON:
    {{
        "concept": "...",
        "mood": "...",
        "scenes": [
            {{"time": "0-5s", "camera": "...", "action": "..."}},
            {{"time": "5-11s", "camera": "...", "action": "..."}},
            {{"time": "11-16s", "camera": "...", "action": "..."}}
        ],
        "text_overlay": "...",
        "music_vibe": "..."
    }}
    """
    
    contents = [prompt]
    if image_bytes:
        contents.insert(0, types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

# --- 2. UI της εφαρμογής ---
uploaded_file = st.file_uploader("📷 Ανέβασε φωτογραφία παπουτσιού (Προαιρετικά για οπτική ανάλυση)", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file:
    st.image(uploaded_file, caption="Προεπισκόπηση Παπουτσιού", width=300)

col1, col2 = st.columns(2)
with col1:
    brand = st.text_input("Brand", placeholder="π.χ. Nike")
with col2:
    model = st.text_input("Model", placeholder="π.χ. Air Max")

colorway = st.text_input("Colorway / Χρώμα", placeholder="π.χ. Black/White")

if st.button("🚀 Σκηνοθέτησε το Βίντεο"):
    if not brand or not model:
        st.warning("⚠️ Συμπλήρωσε τουλάχιστον Brand και Model!")
    else:
        with st.spinner("Η φαντασία του Sneakerness δουλεύει..."):
            img_bytes = uploaded_file.getvalue() if uploaded_file else None
            mime = "image/jpeg"
            if uploaded_file and uploaded_file.name.lower().endswith(".png"): mime = "image/png"
            elif uploaded_file and uploaded_file.name.lower().endswith(".webp"): mime = "image/webp"

            script = generate_script_with_vision(brand, model, colorway, img_bytes, mime)
            st.session_state["script"] = script
            st.success("Το σενάριο ετοιμάστηκε!")

# --- 3. Προβολή Σεναρίου ---
if "script" in st.session_state:
    script = st.session_state["script"]
    st.markdown("---")
    st.success(f"💡 Concept: {script['concept']}")
    st.write(f"**Mood:** {script['mood']}")
    st.write(f"**Μουσική:** {script['music_vibe']}")
    st.write(f"**Κείμενο (Overlay):** {script['text_overlay']}")
    
    st.markdown("#### 🎬 Σκηνές Βίντεο (16s Timeline):")
    for scene in script['scenes']:
        st.info(f"**{scene['time']}** | Κίνηση: {scene['action']} *(Κάμερα: {scene['camera']})*")
        
    st.download_button("📥 Κατέβασμα JSON Σεναρίου", json.dumps(script, ensure_ascii=False, indent=2), file_name="video_script.json")
