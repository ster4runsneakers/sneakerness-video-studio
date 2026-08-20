import streamlit as st
import json
from google import genai
from google.genai import types
import os
import time
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# Ρύθμιση σελίδας
st.set_page_config(page_title="Sneakerness Video Studio", layout="centered")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Grok Action-Prompt Engine & Video Post-Production")

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
    if "rendered_video" in st.session_state: del st.session_state["rendered_video"]

# 2. UI & UPLOADS
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

# 3. ACTION & LIFESTYLE SCRIPT GENERATION FUNCTION (GROK OPTIMIZED)
def generate_video_script_from_image(image_bytes, mime_type):
    sys_instruction = """You are an elite commercial video director for Sneakerness.eu. 
    Your goal is to write dynamic, cinematic 16-second TikTok/Reels video prompts optimized for Grok AI Video Generator.
    FOCUS ON REAL HUMAN MOVEMENT, LIFESTYLE, AND ACTION SCENES: street basketball, urban walking, daily shifts, athletes, and realistic foot movements wearing the sneakers.
    ALWAYS include prompt templates tailored for direct copy-pasting into Grok AI. Return strictly JSON."""
    
    prompt = """Examine the provided sneaker image. Identify the brand, model, and colorway, and create a 16-second cinematic video script featuring real people in dynamic action scenes.

    Return strict JSON matching this schema:
    {
        "brand": "Detected Brand",
        "model": "Detected Model",
        "colorway": "Detected Colorway",
        "concept": "Creative concept name (e.g. Street Culture, Game Day, Urban Shift)",
        "mood": "Lighting and emotional mood description",
        "grok_prompts": [
            {
                "time": "0-5s (Hook / Action)", 
                "grok_prompt": "Cinematic action shot: A person wearing the [Brand Model] sneakers performing an athletic move or walking on concrete, low angle camera tracking feet..."
            },
            {
                "time": "5-11s (Lifestyle / Motion)", 
                "grok_prompt": "Lifestyle shot: Person sitting or moving naturally in an urban setting wearing [Brand Model], detailed focus on posture and sneaker flexibility..."
            },
            {
                "time": "11-16s (Close-up / Climax)", 
                "grok_prompt": "Close-up macro tracking shot: Fast footwork transition on basketball court floor showing sole grip and cushioning..."
            }
        ],
        "text_overlay": "Engaging short text overlay",
        "music_vibe": "Recommended audio track genre"
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
        except Exception:
            time.sleep(1)
            
    raise Exception("Model failed to generate action script.")

if st.button("🚀 Δημιουργία Action Prompts για Grok", type="primary"):
    if not uploaded_file:
        st.warning("⚠️ Παρακαλώ ανέβασε πρώτα μια φωτογραφία παπουτσιού!")
    else:
        with st.spinner("Ο σκηνοθέτης δημιουργεί prompts με ανθρώπους & κίνηση..."):
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
                st.error(f"❌ Σφάλμα: {str(err)}")

# 4. EDITABLE FIELDS
col1, col2, col3 = st.columns(3)
with col1: brand = st.text_input("Brand", value=st.session_state["brand_val"])
with col2: model_name = st.text_input("Model", value=st.session_state["model_val"])
with col3: colorway = st.text_input("Colorway", value=st.session_state["colorway_val"])

# 5. GROK PROMPTS DISPLAY & MOVIEPY POST-PRODUCTION
if "script" in st.session_state:
    script = st.session_state["script"]
    st.markdown("---")
    st.success(f"💡 **Concept:** {script.get('concept', '')}")
    st.write(f"**Mood:** {script.get('mood', '')}")
    st.write(f"**Προτεινόμενο Overlay Text:** {script.get('text_overlay', '')}")
    
    st.markdown("#### 🤖 Prompts για το Grok (Ανθρώπινη Κίνηση & Δράση):")
    for item in script.get('grok_prompts', []):
        st.write(f"**{item.get('time')}**")
        st.code(item.get('grok_prompt'), language="text")
        
    st.markdown("---")
    st.markdown("### 🎬 Grok Video Polishing & Branding (MoviePy)")
    grok_video_file = st.file_uploader("📥 Ανέβασε το τελικό βίντεο από το Grok (.mp4)", type=["mp4", "mov"])
    bg_audio_file = st.file_uploader("🎵 Ανέβασε κομμάτι Μουσικής (.mp3)", type=["mp3"])

    if st.button("⚙️ Προσθήκη Μουσικής & Branding", type="primary"):
        if not grok_video_file:
            st.warning("⚠️ Ανέβασε πρώτα το βίντεο από το Grok!")
        else:
            with st.spinner("Η Python μοντάρει το τελικό βίντεο..."):
                try:
                    os.makedirs("temp", exist_ok=True)
                    video_input_path = "temp/grok_video.mp4"
                    with open(video_input_path, "wb") as f:
                        f.write(grok_video_file.getbuffer())

                    audio_input_path = None
                    if bg_audio_file:
                        audio_input_path = "temp/bg_audio.mp3"
                        with open(audio_input_path, "wb") as f:
                            f.write(bg_audio_file.getbuffer())

                    output_path = "temp/final_sneakerness_ad.mp4"

                    video_clip = VideoFileClip(video_input_path)

                    if audio_input_path:
                        audio_clip = AudioFileClip(audio_input_path).subclip(0, min(video_clip.duration, AudioFileClip(audio_input_path).duration))
                        video_clip = video_clip.set_audio(audio_clip)

                    text_content = script.get('text_overlay', 'SNEAKERNESS.EU')
                    txt_clip = TextClip(text_content, fontsize=45, color='white', stroke_color='black', stroke_width=2, method='caption', size=(video_clip.w * 0.85, None))
                    txt_clip = txt_clip.set_position(('center', 'top')).set_start(0).
