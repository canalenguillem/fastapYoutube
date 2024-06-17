from fastapi import APIRouter, HTTPException
from app.crud.fragment import get_fragment, update_fragment
from pydub import AudioSegment
import speech_recognition as sr
import os

router = APIRouter()


@router.get("/fragment/{fragment_id}")
async def read_fragment(fragment_id: int):
    fragment = await get_fragment(fragment_id)
    if not fragment:
        raise HTTPException(status_code=404, detail="Fragment not found")
    return fragment


@router.post("/process_fragment/")
async def process_fragment(fragment_id: int):
    fragment_record = await get_fragment(fragment_id)
    if not fragment_record:
        raise HTTPException(status_code=404, detail="Fragment not found")

    # Convertir MP3 a WAV antes de la transcripción
    mp3_file_path = fragment_record["file_path"]
    wav_file_path = mp3_file_path.replace(".mp3", ".wav")

    audio = AudioSegment.from_mp3(mp3_file_path)
    audio.export(wav_file_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_file_path) as source:
        audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="es-ES")

    # Eliminar archivo WAV después de la transcripción
    os.remove(wav_file_path)

    await update_fragment(fragment_id, text, "es-ES")

    return {"message": "Fragment processed", "transcription": text}
