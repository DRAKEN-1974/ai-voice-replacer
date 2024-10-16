import streamlit as st
from moviepy.editor import VideoFileClip, AudioFileClip
import speech_recognition as sr
import pyttsx3
import tempfile
from pydub import AudioSegment
import requests
import json

# Azure OpenAI API details
AZURE_OPENAI_API_KEY = "22ec84421ec24230a3638d1b51e3a7dc"
AZURE_OPENAI_ENDPOINT = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"

# Initialize pyttsx3 for TTS
engine = pyttsx3.init()

def main():
    st.title("AI Voice Replacement for Video")

    video_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi"])

    if video_file:
        st.video(video_file)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
            temp_video_file.write(video_file.read())
            temp_video_file_path = temp_video_file.name

        # Step 1: Extract audio from video
        video_clip = VideoFileClip(temp_video_file_path)
        audio_file = video_clip.audio
        audio_file.write_audiofile("extracted_audio.wav")
        
        video_duration = video_clip.duration  # Get video duration in seconds

        # Step 2: Transcribe audio
        transcription = transcribe_audio("extracted_audio.wav")
        st.write("Original Transcription:", transcription)

        # Step 3: Correct transcription using GPT-4 from Azure
        corrected_transcription = correct_transcription_azure(transcription)
        st.write("Corrected Transcription:", corrected_transcription)

        # Step 4: Generate AI voice using pyttsx3
        generate_ai_audio(corrected_transcription)

        # Step 5: Adjust the speed of the AI-generated audio to make it more smooth and natural
        adjusted_audio_path = adjust_audio_speed("generated_audio.wav")

        # Step 6: Trim the video length to match the audio duration with smoother transition
        trim_video_to_audio(temp_video_file_path, adjusted_audio_path)

        st.success("Audio replaced successfully! You can download the final video now.")
        st.video("final_output.mp4")


# Step 2: Transcribe the audio using SpeechRecognition
def transcribe_audio(audio_file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            st.error("Could not understand the audio.")
            return ""
        except sr.RequestError as e:
            st.error(f"Error: {e}")
            return ""


# Step 3: Correct transcription using Azure OpenAI GPT-4
def correct_transcription_azure(transcription):
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY
    }

    data = {
        "messages": [
            {"role": "system", "content": "Correct this transcription by removing grammatical errors, 'umms', and 'hmms'."},
            {"role": "user", "content": transcription}
        ]
    }

    try:
        response = requests.post(AZURE_OPENAI_ENDPOINT, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with Azure OpenAI: {e}")
        return transcription


# Step 4: Generate AI voice using pyttsx3 (offline TTS)
def generate_ai_audio(text):
    engine.setProperty('rate', 140)  # Slightly slower for smoother speech
    engine.setProperty('volume', 1)  # Maximum volume
    
    # Save the generated speech to a WAV file
    engine.save_to_file(text, 'generated_audio.wav')
    engine.runAndWait()


# Step 5: Adjust audio speed to make it smoother and more natural
def adjust_audio_speed(audio_file_path, target_speed=1.1):
    """Adjust the speed of the AI-generated audio more smoothly for a natural sound."""
    audio = AudioSegment.from_wav(audio_file_path)
    
    # Apply a small speed adjustment to keep the audio smooth and natural (1.1x speed)
    adjusted_audio = audio.speedup(playback_speed=target_speed)
    
    # Export adjusted audio
    adjusted_audio_path = "adjusted_audio.wav"
    adjusted_audio.export(adjusted_audio_path, format="wav")
    
    return adjusted_audio_path


# Step 6: Trim the video to match the new audio duration with smoother transitions
def trim_video_to_audio(video_file_path, audio_file_path):
    # Load the video and audio files
    video = VideoFileClip(video_file_path)
    new_audio = AudioFileClip(audio_file_path)

    # Get the duration of the adjusted audio
    audio_duration = new_audio.duration

    # Ensure the video starts and ends smoothly by trimming excess video and adding small fade-out
    trimmed_video = video.subclip(0, audio_duration).fadeout(1)  # Apply 1-second fade-out

    # Replace the original audio with the new one
    final_video = trimmed_video.set_audio(new_audio)
    
    # Export the final video with smoother transitions
    final_video.write_videofile("final_output.mp4", codec="libx264", audio_codec="aac")


if __name__ == "__main__":
    main()
