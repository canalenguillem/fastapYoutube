from sqlalchemy import select, delete, insert
from app.database import database
from app.models import translations


async def get_translation(fragment_id: int, target_language: str):
    query = select(translations).where(
        translations.c.fragment_id == fragment_id,
        translations.c.language == target_language
    )
    return await database.fetch_one(query)


async def insert_translation(video_id: int, fragment_id: int, translated_text: str, language: str, start_time: int, end_time: int):
    query = insert(translations).values(
        video_id=video_id,
        fragment_id=fragment_id,
        translated_text=translated_text,
        language=language,
        start_time=start_time,
        end_time=end_time
    )
    await database.execute(query)


async def delete_translations_by_video(video_id: int):
    await database.execute(delete(translations).where(translations.c.video_id == video_id))
