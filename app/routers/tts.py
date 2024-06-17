from fastapi import APIRouter, HTTPException
from app.crud.translation import get_translation
from app.crud.tts import insert_tts_conversion
from libraries.elevenlabs_tts import convert_text_to_speech
import os

router = APIRouter()


@router.post("/elevenlabs_translated_tts/")
async def elevenlabs_translated_tts(fragment_id: int, target_language: str = "en"):
    translation_record = await get_translation(fragment_id, target_language)

    if not translation_record:
        raise HTTPException(
            status_code=404, detail="Translated fragment not found")

    audio_content = convert_text_to_speech(
        translation_record['translated_text'])

    if audio_content is None:
        raise HTTPException(
            status_code=500, detail="Error converting text to speech with ElevenLabs")

    if not os.path.exists("tts"):
        os.makedirs("tts")

    output_file = f"tts/{fragment_id}_tts_elevenlabs_{target_language}.mp3"
    with open(output_file, "wb") as f:
        f.write(audio_content)

    await insert_tts_conversion(
        video_id=translation_record['video_id'],
        fragment_id=fragment_id,
        path=output_file,
        language=target_language,
        voice="Rachel",
        start_time=translation_record['start_time'],
        end_time=translation_record['end_time']
    )

    return {"message": "Text to speech conversion done", "file_path": output_file}
