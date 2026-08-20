import streamlit as st
import json
from google import genai
from google.genai import types
import os
import time

# Robust MoviePy Imports (Handles v1.x and v2.x compatibility)
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.VideoClip import TextClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# Ρύθμιση σελίδας
st.set_page_config(page_title="Sneakerness Video Studio", layout="centered")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Category-Aware Archetype Engine & Grok Prompt Director")

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

# 3. CATEGORY-AWARE SCRIPT GENERATION FUNCTION
def generate_category_script(image_bytes, mime_type):
    sys_instruction = """You are an expert commercial fashion director and video scriptwriter for Sneakerness.eu.
    Your job is to analyze the sneaker image, determine its exact FOOTWEAR CATEGORY, and construct a hyper-targeted 16-second video script for Grok AI.
    
    STRICT CATEGORY & STYLING MAPPING RULES:
    1. BASKETBALL (e.g. Kobe, Kyrie, Jordan, LeBron):
       - Outfit: Oversized streetwear jersey/mesh shorts, compression tights, athletic socks.
       - Environment: Hardwood court, outdoor concrete playground with chain-link fences.
       - Action: Crossover dribble, jump shot, tied laces before entering court, casual walking with ball under arm.
    2. PERFORMANCE RUNNING (e.g. HOKA, Brooks, Asics Gel-Nimbus, Nike Pegasus):
       - Outfit: Technical running shorts, sweat-wicking athletic hoodie or tank, modern running socks.
       - Environment: Wet asphalt street at dawn, urban park path, running track.
       - Action: Morning stretch, dynamic footwork pace, walking after a long shift/run touching aching feet.
    3. RETRO / LIFESTYLE (e.g. Adidas Samba, New Balance 550/2002R, Puma Suede):
       - Outfit: Relaxed fit denim jeans or cargo trousers, oversized clean hoodie/t-shirt, tote bag.
       - Environment: Urban coffee shop entrance, Metro stairs, minimalist concrete sidewalk.
       - Action: Walking down city steps, sitting on outdoor bench tying shoe, casual street navigation.
    4. OUTDOOR / TRAIL (e.g. Salomon XT-6, HOKA Speedgoat, Nike ACG):
       - Outfit: GORE-TEX jacket, utility cargo pants, outdoor crew socks.
       - Environment: Gravel trail, wet rock path, urban rainy street.
       - Action: Walking over rough terrain, stepping through shallow puddle showing water resistance.

    Return ONLY a valid JSON object."""
    
    prompt = """Examine the provided sneaker image and generate a script based on its archetype.

    Return strict JSON matching this schema:
    {
        "brand": "Detected Brand",
        "model": "Detected Model",
        "colorway": "Detected Colorway",
        "category": "Detected Category (Basketball / Running / Lifestyle / Trail)",
        "outfit_style": "Detailed outfit description (clothing, socks, pants)",
        "concept": "Creative concept title",
        "mood": "Lighting and aesthetic vibe",
        "grok_prompts": [
            {
                "time": "0-5s (Action & Styling)", 
                "grok_prompt": "Cinematic shot: A person wearing [exact outfit] and [Brand Model] performing [category action] in [category environment]..."
            },
            {
                "time": "5-11s (Lifestyle Context)", 
                "grok_prompt": "Tracking shot: Close-up on feet moving naturally in [category environment], showing [outfit details] and sneaker flexibility..."
            },
            {
                "time": "11-16s (Climax & Footwork)", 
                "grok_prompt": "Dynamic low-angle camera: Detailed footwork movement showing [Brand Model] in action..."
            }
        ],
        "text_overlay": "Short high-converting text overlay",
        "music_vibe": "Category-matched audio style (e.g., Hip-hop beat, Lofi, Synthwave, Energetic rock)"
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
            
    raise Exception("Model failed to generate category script.")

if st.button("🚀 Δημιουργία Category-Aware Script", type="primary"):
    if not uploaded_file:
        st.warning("⚠️ Παρακαλώ ανέβασε πρώτα μια φωτογραφία παπουτσιού!")
    else:
        with st.spinner("Ο σκηνοθέτης αναλύει την κατηγορία, το ντύσιμο και το στυλ..."):
            try:
                img_bytes = uploaded_file.getvalue()
                mime = "image/jpeg"
                if uploaded_file.name.lower().endswith(".png"): mime = "image/png"
                elif uploaded_file.name.lower().endswith(".webp"): mime = "image/webp"

                script = generate_category_script(img_bytes, mime)
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

# 5. SCRIPT DISPLAY & POST-PRODUCTION
if "script" in st.session_state:
    script = st.session_state["script"]
    st.markdown("---")
    
    col_cat, col_outfit = st.columns(2)
    with col_cat:
        st.info(f"🏷️ **Κατηγορία:** {script.get('category', 'Lifestyle')}")
    with col_outfit:
        st.info(f"👕 **Προτεινόμενο Outfit:** {script.get('outfit_style', '')}")

    st.success(f"💡 **Concept:** {script.get('concept', '')}")
    st.write(f"**Mood:** {script.get('mood', '')}")
    st.write(f"**Προτεινόμενο Overlay Text:** {script.get('text_overlay', '')}")
    st.write(f"**Μουσικό Vibe:** {script.get('music_vibe', '')}")
    
    st.markdown("#### 🤖 Prompts για το Grok (Εξειδικευμένο Outfit & Δράση):")
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
                    txt_clip = txt_clip.set_position(('center', 'top')).set_start(0).set_duration(video_clip.duration)

                    final_clip = CompositeVideoClip([video_clip, txt_clip])
                    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium", logger=None)

                    st.session_state["rendered_video"] = output_path
                    st.success("🎉 Το βίντεο ολοκληρώθηκε!")

                except Exception as e:
                    st.error(f"❌ Σφάλμα rendering: {str(e)}")

    if "rendered_video" in st.session_state and os.path.exists(st.session_state["rendered_video"]):
        st.video(st.session_state["rendered_video"])
        with open(st.session_state["rendered_video"], "rb") as file:
            st.download_button(
                label="📥 Κατέβασμα Τελικού MP4 (Sneakerness Ready)",
                data=file,
                file_name="sneakerness_grok_final.mp4",
                mime="video/mp4"
            )
