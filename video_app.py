# video_app.py - Sneakerness Video Studio & Pure AI Music (Meta MusicGen)
import os
import json
import time
import textwrap
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

import streamlit as st
from google import genai
from google.genai import types

# FIX FOR PILLOW 10+ COMPATIBILITY WITH MOVIEPY
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Robust MoviePy Imports
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips

# Ρύθμιση σελίδας
st.set_page_config(page_title="Sneakerness Video Studio", page_icon="🎬", layout="centered")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Category-Aware Engine with Meta MusicGen AI & Multi-Clip Merger")

# API Keys Check
api_key = os.getenv("GEMINI_API_KEY")
hf_token = os.getenv("HF_TOKEN")

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

# 2. HELPER FUNCTION: UNIVERSAL TEXT OVERLAY IMAGE
def create_text_overlay_image(text, width, height):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    aspect_ratio = width / height
    
    if aspect_ratio < 0.8: # 9:16 Vertical
        top_margin_ratio = 0.12
        max_width_ratio = 0.75
        base_font_scale = 0.040
    elif aspect_ratio > 1.2: # 16:9 Landscape
        top_margin_ratio = 0.07
        max_width_ratio = 0.65
        base_font_scale = 0.045
    else: # 1:1 Square
        top_margin_ratio = 0.08
        max_width_ratio = 0.70
        base_font_scale = 0.042

    max_text_width = int(width * max_width_ratio)
    min_dim = min(width, height)
    font_size = int(min_dim * base_font_scale)
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    avg_char_width = font_size * 0.55
    chars_per_line = max(8, int(max_text_width / avg_char_width))
    wrapped_lines = textwrap.wrap(text, width=chars_per_line)

    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        while line_w > max_text_width and font_size > 12:
            font_size -= 2
            try:
                font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]

    avg_char_width = font_size * 0.55
    chars_per_line = max(8, int(max_text_width / avg_char_width))
    wrapped_lines = textwrap.wrap(text, width=chars_per_line)

    line_padding = int(font_size * 0.25)
    line_metrics = []
    
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_metrics.append((line, lw, lh))

    current_y = int(height * top_margin_ratio)
    stroke_w = max(2, int(font_size * 0.08))

    for line, lw, lh in line_metrics:
        x = (width - lw) // 2
        for offset_x in range(-stroke_w, stroke_w + 1):
            for offset_y in range(-stroke_w, stroke_w + 1):
                draw.text((x + offset_x, current_y + offset_y), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += lh + line_padding
    
    os.makedirs("temp", exist_ok=True)
    overlay_path = "temp/text_overlay.png"
    img.save(overlay_path)
    return overlay_path

# 3. HELPER FUNCTION: GENERATE AI MUSIC VIA HUGGING FACE
def generate_ai_music_hf(music_prompt):
    if not hf_token:
        st.warning("⚠️ Δεν βρέθηκε το HF_TOKEN στα Secrets. Παράλειψη δημιουργίας AI Μουσικής.")
        return None

    os.makedirs("temp", exist_ok=True)
    out_music_path = "temp/generated_ai_music.wav"
    
    API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": music_prompt}

    try:
        for attempt in range(3):
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                with open(out_music_path, "wb") as f:
                    f.write(response.content)
                return out_music_path
            elif response.status_code == 503:
                time.sleep(10)
            else:
                break
        return None
    except Exception:
        return None

# 4. UI & UPLOADS
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

# 5. CATEGORY-AWARE SCRIPT GENERATION FUNCTION
def generate_category_script(image_bytes, mime_type, target_aspect_ratio):
    sys_instruction = f"""You are an expert commercial fashion director and video scriptwriter for Sneakerness.eu.
    Your job is to analyze the sneaker image, determine its exact FOOTWEAR CATEGORY, and construct a hyper-targeted 16-second video script.
    Format: {target_aspect_ratio}.
    Keep 'text_overlay' SHORT and IMPACTFUL (maximum 4 to 7 words).
    Provide a 'music_prompt' (in English) optimized for Meta MusicGen (e.g., 'energetic hip hop beat, 115 bpm, punchy kick').
    
    STRICT CATEGORY & STYLING MAPPING RULES:
    1. BASKETBALL: Oversized streetwear jersey, hardwood court, crossover dribble.
    2. PERFORMANCE RUNNING: Technical shorts, wet asphalt at dawn, dynamic pace.
    3. RETRO / LIFESTYLE: Cargo denim, coffee shop entrance, casual street navigation.
    4. OUTDOOR / TRAIL: GORE-TEX jacket, gravel trail, stepping through shallow puddle.

    Return ONLY a valid JSON object."""
    
    prompt = """Examine the sneaker image and generate a script.

    Return strict JSON matching this schema:
    {
        "brand": "Detected Brand",
        "model": "Detected Model",
        "colorway": "Detected Colorway",
        "category": "Detected Category",
        "outfit_style": "Detailed outfit description",
        "concept": "Creative concept title",
        "mood": "Lighting and aesthetic vibe",
        "music_prompt": "Specific music prompt for Meta MusicGen AI",
        "grok_prompts": [
            {"time": "0-5s", "grok_prompt": "Cinematic shot... (no text)"},
            {"time": "5-11s", "grok_prompt": "Tracking shot... (no text)"},
            {"time": "11-16s", "grok_prompt": "Dynamic low-angle camera... (no text)"}
        ],
        "text_overlay": "Short text overlay"
    }"""
    
    contents = [types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt]
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
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

# 6. ASPECT RATIO SELECTOR
aspect_choice = st.selectbox(
    "📐 Επιλογή Aspect Ratio (Διάσταση Βίντεο)", 
    ["9:16 Vertical (TikTok / Reels / Shorts)", "16:9 Landscape (YouTube / Banner)", "1:1 Square (Instagram Post)"]
)

if st.button("🚀 Δημιουργία Category-Aware Script", type="primary"):
    if not uploaded_file:
        st.warning("⚠️ Παρακαλώ ανέβασε πρώτα μια φωτογραφία παπουτσιού!")
    else:
        with st.spinner("Ανάλυση κατηγορίας & παραγωγή σεναρίου..."):
            try:
                img_bytes = uploaded_file.getvalue()
                mime = "image/jpeg"
                if uploaded_file.name.lower().endswith(".png"): mime = "image/png"
                elif uploaded_file.name.lower().endswith(".webp"): mime = "image/webp"

                script = generate_category_script(img_bytes, mime, aspect_choice)
                st.session_state["script"] = script
                st.session_state["selected_aspect"] = aspect_choice
                st.session_state["brand_val"] = script.get("brand", "")
                st.session_state["model_val"] = script.get("model", "")
                st.session_state["colorway_val"] = script.get("colorway", "")
                st.rerun()
            except Exception as err:
                st.error(f"❌ Σφάλμα: {str(err)}")

# 7. EDITABLE FIELDS
col1, col2, col3 = st.columns(3)
with col1: brand = st.text_input("Brand", value=st.session_state["brand_val"])
with col2: model_name = st.text_input("Model", value=st.session_state["model_val"])
with col3: colorway = st.text_input("Colorway", value=st.session_state["colorway_val"])

# 8. SCRIPT DISPLAY & MULTI-CLIP POST-PRODUCTION
if "script" in st.session_state:
    script = st.session_state["script"]
    
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🏷️ Category & Outfit", "💡 Concept & AI Music Vibe", "🤖 AI Video Prompts"])

    with tab1:
        col_cat, col_outfit = st.columns(2)
        col_cat.metric("🏷️ Κατηγορία", script.get('category', 'Lifestyle'))
        col_outfit.info(f"👕 **Outfit:** {script.get('outfit_style', '')}")

    with tab2:
        st.success(f"💡 **Concept:** {script.get('concept', '')}")
        st.write(f"🎵 **Meta MusicGen Prompt:** {script.get('music_prompt', '')}")

    with tab3:
        st.write(f"**Προτεινόμενο Overlay Text:** {script.get('text_overlay', '')}")
        for item in script.get('grok_prompts', []):
            st.write(f"**{item.get('time')}**")
            st.code(item.get('grok_prompt'), language="text")
        
    st.markdown("---")
    st.markdown("### 🎬 Multi-Clip Merger & AI Audio Post-Production")
    
    grok_video_files = st.file_uploader(
        "📥 Ανέβασε έως 6 βίντεο-κλιπ (.mp4)", 
        type=["mp4", "mov"], 
        accept_multiple_files=True
    )
    
    use_ai_music = st.checkbox("🎵 Αυτόματη Δημιουργία AI Background Music (Meta MusicGen)", value=True)

    if st.button("⚙️ Σύνθεση Κλιπ, AI Μουσικής & Branding", type="primary"):
        if not grok_video_files or len(grok_video_files) == 0:
            st.warning("⚠️ Ανέβασε τουλάχιστον ένα βίντεο-κλιπ!")
        else:
            with st.spinner("Η Python μοντάρει το βίντεο και προσαρμόζει τις διαστάσεις..."):
                try:
                    os.makedirs("temp", exist_ok=True)
                    loaded_clips = []

                    # Χρήση του τρέχοντος επιλεγμένου Aspect Ratio
                    current_aspect = aspect_choice

                    if "9:16" in current_aspect:
                        target_w, target_h = 1080, 1920
                    elif "16:9" in current_aspect:
                        target_w, target_h = 1920, 1080
                    else: # 1:1
                        target_w, target_h = 1080, 1080

                    target_aspect = target_w / target_h

                    for idx, vfile in enumerate(grok_video_files):
                        vpath = f"temp/input_clip_{idx}.mp4"
                        with open(vpath, "wb") as f: f.write(vfile.getbuffer())
                        clip = VideoFileClip(vpath)

                        clip_aspect = clip.w / clip.h

                        # ΑΥΣΤΗΡΟ SMART CROP & RESIZE
                        if abs(clip_aspect - target_aspect) > 0.01:
                            if clip_aspect > target_aspect:
                                new_w = int(clip.h * target_aspect)
                                crop_x1 = int((clip.w - new_w) / 2)
                                clip = clip.crop(x1=crop_x1, width=new_w, height=clip.h)
                            else:
                                new_h = int(clip.w / target_aspect)
                                crop_y1 = int((clip.h - new_h) / 2)
                                clip = clip.crop(y1=crop_y1, width=clip.w, height=new_h)

                        # Επιβολή τελικών διαστάσεων
                        clip_resized = clip.resize(newsize=(target_w, target_h))
                        loaded_clips.append(clip_resized)

                    merged_video = concatenate_videoclips(loaded_clips, method="compose")

                    # ΗΧΟΣ: Meta MusicGen Background Music
                    if use_ai_music:
                        m_prompt = script.get("music_prompt", "energetic viral commercial background beat, 115 bpm")
                        music_path = generate_ai_music_hf(m_prompt)
                        if music_path and os.path.exists(music_path):
                            music_clip = AudioFileClip(music_path)
                            if music_clip.duration < merged_video.duration:
                                music_clip = music_clip.loop(duration=merged_video.duration)
                            else:
                                music_clip = music_clip.subclip(0, merged_video.duration)
                            
                            merged_video = merged_video.set_audio(music_clip)

                    output_path = f"temp/final_sneakerness_ad_{int(time.time())}.mp4"
                    text_content = script.get('text_overlay', 'SNEAKERNESS.EU')
                    overlay_img_path = create_text_overlay_image(text_content, target_w, target_h)
                    
                    txt_clip = ImageClip(overlay_img_path).set_start(0).set_duration(merged_video.duration)

                    final_clip = CompositeVideoClip([merged_video, txt_clip], size=(target_w, target_h))
                    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium", logger=None)

                    for c in loaded_clips: c.close()
                    merged_video.close()

                    st.session_state["rendered_video"] = output_path
                    st.success(f"🎉 Το βίντεο προσαρμόστηκε επιτυχώς σε διαστάσεις {target_w}x{target_h}!")

                except Exception as e:
                    st.error(f"❌ Σφάλμα rendering: {str(e)}")

    if "rendered_video" in st.session_state and os.path.exists(st.session_state["rendered_video"]):
        st.video(st.session_state["rendered_video"])
        with open(st.session_state["rendered_video"], "rb") as file:
            st.download_button(
                label="📥 Κατέβασμα Τελικού MP4",
                data=file,
                file_name="sneakerness_ad.mp4",
                mime="video/mp4"
            )
