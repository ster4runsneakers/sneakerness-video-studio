# video_app.py - Dedicated Video Studio (With English AI Voiceover & Subtitles)
import os
import time
import shutil
import textwrap
import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

import streamlit as st
from google import genai
from google.genai import types

# Fix για συμβατότητα Pillow 10+ με MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from moviepy.audio.AudioClip import CompositeAudioClip

st.set_page_config(page_title="Sneakerness Video Studio", page_icon="🎬", layout="centered")

st.title("🎬 Sneakerness Video Studio")
st.subheader("Video Editor with English AI Voiceover, Music & Subtitles")

api_key = os.getenv("GEMINI_API_KEY")
hf_token = os.getenv("HF_TOKEN")

if not api_key:
    st.error("❌ Δεν βρέθηκε το GEMINI_API_KEY στα Secrets / .env!")
    st.stop()

client = genai.Client(api_key=api_key)

# 1. CLEAN TEMP DIRECTORY
def reset_temp_dir():
    if os.path.exists("temp"):
        try:
            shutil.rmtree("temp")
        except Exception:
            pass
    os.makedirs("temp", exist_ok=True)

# 2. HELPER: TOP BRANDING OVERLAY
def create_text_overlay_image(text, width, height):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    aspect_ratio = width / height
    top_margin_ratio = 0.10 if aspect_ratio < 0.8 else 0.06
    max_text_width = int(width * 0.70)
    min_dim = min(width, height)
    font_size = int(min_dim * 0.038)
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    avg_char_width = font_size * 0.55
    chars_per_line = max(6, int(max_text_width / avg_char_width))
    wrapped_lines = textwrap.wrap(text, width=chars_per_line)

    line_padding = int(font_size * 0.20)
    current_y = int(height * top_margin_ratio)
    stroke_w = max(2, int(font_size * 0.08))

    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        x = (width - lw) // 2
        for offset_x in range(-stroke_w, stroke_w + 1):
            for offset_y in range(-stroke_w, stroke_w + 1):
                draw.text((x + offset_x, current_y + offset_y), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, current_y), line, font=font, fill=(255, 255, 255, 255))
        current_y += lh + line_padding
    
    os.makedirs("temp", exist_ok=True)
    overlay_path = f"temp/text_overlay_{int(time.time())}.png"
    img.save(overlay_path)
    return overlay_path

# 3. HELPER: SUBTITLES OVERLAY GENERATOR (BOTTOM SAFE AREA)
def create_subtitles_overlay_image(text, width, height):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    aspect_ratio = width / height
    bottom_margin_ratio = 0.80 if aspect_ratio < 0.8 else 0.85
    max_text_width = int(width * 0.80)
    min_dim = min(width, height)
    font_size = int(min_dim * 0.035)
    
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    avg_char_width = font_size * 0.55
    chars_per_line = max(8, int(max_text_width / avg_char_width))
    wrapped_lines = textwrap.wrap(text, width=chars_per_line)

    line_padding = int(font_size * 0.15)
    current_y = int(height * bottom_margin_ratio)
    stroke_w = max(2, int(font_size * 0.08))

    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        x = (width - lw) // 2
        
        # Yellow Subtitles with Black Stroke
        for offset_x in range(-stroke_w, stroke_w + 1):
            for offset_y in range(-stroke_w, stroke_w + 1):
                draw.text((x + offset_x, current_y + offset_y), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, current_y), line, font=font, fill=(255, 223, 0, 255)) # Warm Yellow Text
        current_y += lh + line_padding
    
    os.makedirs("temp", exist_ok=True)
    sub_path = f"temp/sub_overlay_{int(time.time())}.png"
    img.save(sub_path)
    return sub_path

# 4. HELPER: AI MUSIC GENERATOR (META MUSICGEN)
def generate_ai_music_hf(music_prompt):
    if not hf_token:
        return None

    os.makedirs("temp", exist_ok=True)
    out_music_path = f"temp/generated_ai_music_{int(time.time())}.wav"
    
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

# 5. HELPER: ENGLISH AI VOICEOVER GENERATOR (GEMINI API)
def generate_ai_voiceover(text_prompt):
    try:
        os.makedirs("temp", exist_ok=True)
        out_audio_path = f"temp/ai_voiceover_{int(time.time())}.mp3"
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Read the following commercial ad script in a natural, energetic male narrator voice (English): '{text_prompt}'",
            config=types.GenerateContentConfig(
                response_mime_type="audio/mp3"
            )
        )
        
        if response and response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    with open(out_audio_path, "wb") as f:
                        f.write(part.inline_data.data)
                    return out_audio_path
        return None
    except Exception:
        return None

# 6. UI INPUTS FOR VIDEO PROCESSING
st.markdown("---")
grok_video_files = st.file_uploader(
    "📥 Ανέβασε τα καθαρά βίντεο-κλιπ σου (.mp4)", 
    type=["mp4", "mov"], 
    accept_multiple_files=True
)

col_v1, col_v2 = st.columns(2)
with col_v1:
    target_aspect_choice = st.selectbox(
        "📐 Επιλογή Aspect Ratio", 
        ["9:16 Vertical (TikTok / Reels)", "16:9 Landscape (YouTube)", "1:1 Square (Instagram)"]
    )
with col_v2:
    custom_overlay_text = st.text_input("✍️ Top Branding Text", value="SNEAKERNESS.EU")

st.markdown("##### 🎵 Ρυθμίσεις AI Ήχου & Υπότιτλων")
col_a1, col_a2 = st.columns(2)

with col_a1:
    use_ai_music = st.checkbox("🎵 Προσθήκη AI Μουσικής", value=True)
    custom_music_prompt = st.text_input("Prompt Μουσικής", value="energetic basketball commercial background beat, 115 bpm")

with col_a2:
    use_ai_vo = st.checkbox("🗣️ Προσθήκη English Voiceover & Υπότιτλων", value=True)
    custom_vo_script = st.text_area("Σενάριο Ομιλίας (English Script)", value="Unleash your potential with the latest release at Sneakerness.eu")

# 7. PROCESSING BUTTON
if st.button("⚙️ Σύνθεση, Crop & Render Βίντεο", type="primary"):
    if not grok_video_files or len(grok_video_files) == 0:
        st.warning("⚠️ Παρακαλώ ανέβασε τουλάχιστον ένα βίντεο-κλιπ!")
    else:
        with st.spinner("Επεξεργασία βίντεο, παραγωγή ομιλίας, υπότιτλων & AI μουσικής..."):
            try:
                reset_temp_dir()
                loaded_clips = []

                if "9:16" in target_aspect_choice: target_w, target_h = 1080, 1920
                elif "16:9" in target_aspect_choice: target_w, target_h = 1920, 1080
                else: target_w, target_h = 1080, 1080

                target_aspect = target_w / target_h

                for idx, vfile in enumerate(grok_video_files):
                    vpath = f"temp/input_clip_{idx}_{int(time.time())}.mp4"
                    with open(vpath, "wb") as f: f.write(vfile.getbuffer())
                    clip = VideoFileClip(vpath)

                    clip_aspect = clip.w / clip.h

                    if abs(clip_aspect - target_aspect) > 0.01:
                        if clip_aspect > target_aspect:
                            new_w = int(clip.h * target_aspect)
                            crop_x1 = int((clip.w - new_w) / 2)
                            clip = clip.crop(x1=crop_x1, width=new_w, height=clip.h)
                        else:
                            new_h = int(clip.w / target_aspect)
                            crop_y1 = int((clip.h - new_h) / 2)
                            clip = clip.crop(y1=crop_y1, width=clip.w, height=new_h)

                    clip_resized = clip.resize(newsize=(target_w, target_h))
                    loaded_clips.append(clip_resized)

                merged_video = concatenate_videoclips(loaded_clips, method="compose")

                # ΗΧΟΣ & ΥΠΟΤΙΤΛΟΙ
                audio_tracks = []
                overlays_list = [merged_video]
                vo_duration = 0

                if use_ai_vo and custom_vo_script.strip():
                    vo_path = generate_ai_voiceover(custom_vo_script.strip())
                    if vo_path and os.path.exists(vo_path):
                        vo_clip = AudioFileClip(vo_path)
                        vo_duration = vo_clip.duration
                        audio_tracks.append(vo_clip)

                        # Δημιουργία Υπότιτλων
                        sub_img_path = create_subtitles_overlay_image(custom_vo_script.strip(), target_w, target_h)
                        sub_clip = ImageClip(sub_img_path).set_start(0).set_duration(min(vo_duration, merged_video.duration))
                        overlays_list.append(sub_clip)

                if use_ai_music and custom_music_prompt.strip():
                    music_path = generate_ai_music_hf(custom_music_prompt.strip())
                    if music_path and os.path.exists(music_path):
                        music_clip = AudioFileClip(music_path)
                        if music_clip.duration < merged_video.duration:
                            music_clip = music_clip.loop(duration=merged_video.duration)
                        else:
                            music_clip = music_clip.subclip(0, merged_video.duration)
                        
                        # Audio Ducking: Χαμηλώνουμε τη μουσική όταν υπάρχει Voiceover
                        if use_ai_vo and len(audio_tracks) > 0:
                            music_clip = music_clip.volumex(0.25)
                        
                        audio_tracks.append(music_clip)

                if len(audio_tracks) > 0:
                    final_audio = CompositeAudioClip(audio_tracks)
                    merged_video = merged_video.set_audio(final_audio)

                # Top Branding Overlay
                if custom_overlay_text.strip():
                    overlay_img_path = create_text_overlay_image(custom_overlay_text.strip(), target_w, target_h)
                    txt_clip = ImageClip(overlay_img_path).set_start(0).set_duration(merged_video.duration)
                    overlays_list.append(txt_clip)

                final_clip = CompositeVideoClip(overlays_list, size=(target_w, target_h))
                output_path = f"temp/final_sneakerness_ad_{int(time.time())}.mp4"

                final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="medium", logger=None)

                for c in loaded_clips: c.close()
                merged_video.close()

                st.session_state["v_rendered_video"] = output_path
                st.success("🎉 Το βίντεο με αγγλικό Voiceover & Υπότιτλους ολοκληρώθηκε!")

            except Exception as e:
                st.error(f"❌ Σφάλμα rendering: {str(e)}")

if "v_rendered_video" in st.session_state and os.path.exists(st.session_state["v_rendered_video"]):
    st.video(st.session_state["v_rendered_video"])
    with open(st.session_state["v_rendered_video"], "rb") as file:
        st.download_button(
            label="📥 Κατέβασμα Τελικού MP4",
            data=file,
            file_name="sneakerness_english_video_ad.mp4",
            mime="video/mp4"
        )
