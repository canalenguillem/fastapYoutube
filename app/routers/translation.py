from fastapi import APIRouter, HTTPException
from app.crud.translation import get_translation, insert_translation
from app.crud.fragment import get_fragment
from googletrans import Translator

router = APIRouter()
translator = Translator()


@router.get("/translation/{fragment_id}/{target_language}")
async def read_translation(fragment_id: int, target_language: str):
    translation = await get_translation(fragment_id, target_language)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    return translation


@router.post("/translate_fragment/")
async def translate_fragment(fragment_id: int, target_language: str = "en"):
    fragment_record = await get_fragment(fragment_id)
    if not fragment_record:
        raise HTTPException(status_code=404, detail="Fragment not found")

    if not fragment_record['transcription']:
        raise HTTPException(
            status_code=400, detail="Fragment has not been transcribed yet")

    translated_text = translator.translate(
        fragment_record['transcription'], dest=target_language).text

    await insert_translation(
        video_id=fragment_record['video_id'],
        fragment_id=fragment_record['id'],
        translated_text=translated_text,
        language=target_language,
        start_time=fragment_record['start_time'],
        end_time=fragment_record['end_time']
    )

    return {"message": "Fragment translated", "translated_text": translated_text}
