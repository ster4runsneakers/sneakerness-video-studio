# video_app.py - Sneakerness Video Studio & Multi-Clip Engine (2026 Edition)
import os
import json
import time
import textwrap
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
st.subheader("Category-Aware Archetype Engine & Multi-Clip Video Merger (2026)")

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

# 2. HELPER FUNCTION: AUTO-WRAPPING & DYNAMICALLY SCALED TEXT OVERLAY
def create_text_overlay_image(text, width, height):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Καθορισμός μέγιστου πλάτους κειμένου (80% του πλάτους του βίντεο)
    max_text_width = int(width * 0.80)
    
    # 2. Δυναμικό μέγεθος γραμματοσειράς βάσει προσανατολισμού
    font_size = int(height * 0.035) if height > width else int(height * 0.05)
    
    try:
        # Ψάχνουμε τη γραμματοσειρά τοπικά στο repo
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # 3. Αναδίπλωση κειμένου (Word Wrapping)
    avg_char_width = font_size * 0.55
    chars_per_line = max(10, int(max_text_width / avg_char_width))
    wrapped_lines = textwrap.wrap(text, width=chars_per_line)
    
    # 4. Υπολογισμός συνολικού ύψους κειμένου
    line_padding = 10
    total_text_height = 0
    line_metrics = []
    
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_metrics.append((line, lw, lh))
        total_text_height += lh + line_padding

    # 5. Τοποθέτηση στο πάνω μέρος (Top Safe Area)
    current_y = int(height * 0.08)
    stroke_w = 3

    for line, lw, lh in line_metrics:
        x = (width - lw) // 2
        
        # Stroke effect (Μαύρο περίγραμμα για αναγνωσιμότητα)
        for offset_x in range(-stroke_w, stroke_w + 1):
            for offset_y in range(-stroke_w, stroke_w + 1):
                draw.text((x + offset_x, current_y + offset_y), line, font=font, fill=(0, 0, 0, 255))

        # Λευκό κύριο κείμενο
        draw.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += lh + line_padding
    
    os.makedirs("temp", exist_ok=True)
    overlay_path = "temp/text_overlay.png"
    img.save(overlay_path)
    return overlay_path

# 3. UI & UPLOADS
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

# 4. CATEGORY-AWARE SCRIPT GENERATION FUNCTION
def generate_category_script(image_bytes, mime_type, target_aspect_ratio="9:16 Vertical (TikTok/Reels)"):
    sys_instruction = f"""You are an expert commercial fashion director and video scriptwriter for Sneakerness.eu.
    Your job is to analyze the sneaker image, determine its exact FOOTWEAR CATEGORY, and construct a hyper-targeted 16-second video script for Grok AI.
    The current target video format is: {target_aspect_ratio}. Ensure camera directions reflect this orientation.
    Keep 'text_overlay' SHORT and IMPACTFUL (maximum 4 to 7 words) so it fits perfectly on video screens.
    
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
        "music_vibe": "Category-matched audio style"
    }"""
    
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt
    ]

    # ΔΙΟΡΘΩΣΗ: Σύγχρονα μοντέλα API για το 2026
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
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

# 5. ASPECT RATIO SELECTOR
aspect_choice = st.selectbox(
    "📐 Επιλογή Aspect Ratio (Διάσταση Βίντεο)", 
    ["9:16 Vertical (TikTok / Reels / Shorts)", "16:9 Landscape (YouTube / Banner)", "1:1 Square (Instagram Post)"]
)

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

                script = generate_category_script(img_bytes, mime, aspect_choice)
                st.session_state["script"] = script
                st.session_state["brand_val"] = script.get("brand", "")
                st.session_state["model_val"] = script.get("model", "")
                st.session_state["colorway_val"] = script.get("colorway", "")
                st.rerun()
            except Exception as err:
                st.error(f"❌ Σφάλμα: {str(err)}")

# 6. EDITABLE FIELDS
col1, col2, col3 = st.columns(3)
with col1: brand = st.text_input("Brand", value=st.session_state["brand_val"])
with col2: model_name = st.text_input("Model", value=st.session_state["model_val"])
with col3: colorway = st.text_input("Colorway", value=st.session_state["colorway_val"])

# 7. SCRIPT DISPLAY & MULTI-CLIP POST-PRODUCTION
if "script" in st.session_state:
    script = st.session_state["script"]
    
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🏷️ Category & Outfit", "💡 Concept & Mood", "🤖 AI Video Prompts"])

    with tab1:
        col_cat, col_outfit = st.columns(2)
        col_cat.metric("🏷️ Κατηγορία", script.get('category', 'Lifestyle'))
        col_outfit.info(f"👕 **Outfit:** {script.get('outfit_style', '')}")

    with tab2:
        st.success(f"💡 **Concept:** {script.get('concept', '')}")
        st.write(f"** Mood:** {script.get('mood', '')}")
        st.write(f"** Μουσικό Vibe:** {script.get('music_vibe', '')}")

    with tab3:
        st.write(f"**Προτεινόμενο Overlay Text:** {script.get('text_overlay', '')}")
        for item in script.get('grok_prompts', []):
            st.write(f"**{item.get('time')}**")
            st.code(item.get('grok_prompt'), language="text")
        
    st.markdown("---")
    st.markdown("### 🎬 Multi-Clip Merger & Aspect Ratio Crop (MoviePy)")
    grok_video_files = st.file_uploader(
        "📥 Ανέβασε έως 6 βίντεο-κλιπ (.mp4)", 
        type=["mp4", "mov"], 
        accept_multiple_files=True
    )
    bg_audio_file = st.file_uploader("🎵 Ανέβασε κομμάτι Μουσικής (.mp3)", type=["mp3"])

    if st.button("⚙️ Σύνθεση Κλιπ, Resize & Branding", type="primary"):
        if not grok_video_files or len(grok_video_files) == 0:
            st.warning("⚠️ Ανέβασε τουλάχιστον ένα βίντεο-κλιπ!")
        elif len(grok_video_files) > 6:
            st.error("❌ Παρακαλώ ανέβασε μέχρι 6 βίντεο-κλιπ.")
        else:
            with st.spinner("Η Python προσαρμόζει τις διαστάσεις και μοντάρει το τελικό βίντεο... Αυτό μπορεί να πάρει έως 1 λεπτό."):
                try:
                    os.makedirs("temp", exist_ok=True)
                    loaded_clips = []

                    # 1. Υπολογισμός Διαστάσεων βάσει Aspect Ratio
                    if "9:16" in aspect_choice:
                        target_w, target_h = 1080, 1920
                    elif "16:9" in aspect_choice:
                        target_w, target_h = 1920, 1080
                    else:  # 1:1
                        target_w, target_h = 1080, 1080

                    # 2. Φόρτωση, Auto-Crop & Resize κάθε κλιπ
                    for idx, vfile in enumerate(grok_video_files):
                        vpath = f"temp/input_clip_{idx}.mp4"
                        with open(vpath, "wb") as f:
                            f.write(vfile.getbuffer())
                        clip = VideoFileClip(vpath)

                        # Smart Crop / Resize στο επιλεγμένο Aspect Ratio
                        clip_aspect = clip.w / clip.h
                        target_aspect = target_w / target_h

                        if clip_aspect > target_aspect:
                            new_w = int(clip.h * target_aspect)
                            clip_cropped = clip.crop(x1=(clip.w - new_w) / 2, width=new_w, height=clip.h)
                        else:
                            new_h = int(clip.w / target_aspect)
                            clip_cropped = clip.crop(y1=(clip.h - new_h) / 2, width=clip.w, height=new_h)

                        clip_resized = clip_cropped.resize((target_w, target_h))
                        loaded_clips.append(clip_resized)

                    # 3. Ένωση των βίντεο στη σειρά
                    merged_video = concatenate_videoclips(loaded_clips, method="compose")

                    # 4. Φόρτωση ήχου
                    if bg_audio_file:
                        audio_input_path = "temp/bg_audio.mp3"
                        with open(audio_input_path, "wb") as f:
                            f.write(bg_audio_file.getbuffer())
                        audio_clip = AudioFileClip(audio_input_path).subclip(0, min(merged_video.duration, AudioFileClip(audio_input_path).duration))
                        merged_video = merged_video.set_audio(audio_clip)

                    # 5. Δημιουργία overlay μέσω PIL με αυτόματο Wrapping & Scaling
                    output_path = "temp/final_sneakerness_ad.mp4"
                    text_content = script.get('text_overlay', 'SNEAKERNESS.EU')
                    overlay_img_path = create_text_overlay_image(text_content, merged_video.w, merged_video.h)
                    
                    txt_clip = ImageClip(overlay_img_path).set_start(0).set_duration(merged_video.duration)

                    # 6. Τελική σύνθεση & Export
                    final_clip = CompositeVideoClip([merged_video, txt_clip])
                    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium", logger=None)

                    # Κλείσιμο clips για αποδέσμευση πόρων
                    for c in loaded_clips: c.close()
                    merged_video.close()
                    txt_clip.close()
                    if bg_audio_file: audio_clip.close()

                    st.session_state["rendered_video"] = output_path
                    st.success("🎉 Το βίντεο προσαρμόστηκε στις επιλεγμένες διαστάσεις και ολοκληρώθηκε!")

                except Exception as e:
                    st.error(f"❌ Σφάλμα rendering: {str(e)}")

    if "rendered_video" in st.session_state and os.path.exists(st.session_state["rendered_video"]):
        st.video(st.session_state["rendered_video"])
        with open(st.session_state["rendered_video"], "rb") as file:
            st.download_button(
                label="📥 Κατέβασμα Τελικού MP4 (Sneakerness Ready)",
                data=file,
                file_name="sneakerness_final_aspect.mp4",
                mime="video/mp4"
            )
