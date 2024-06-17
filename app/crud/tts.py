import os
from sqlalchemy import select, delete, insert
from app.database import database
from app.models import tts_conversions


async def insert_tts_conversion(video_id: int, fragment_id: int, path: str, language: str, voice: str, start_time: int, end_time: int):
    query = insert(tts_conversions).values(
        video_id=video_id,
        fragment_id=fragment_id,
        path=path,
        language=language,
        voice=voice,
        start_time=start_time,
        end_time=end_time
    )
    await database.execute(query)


async def delete_tts_by_video(video_id: int):
    tts_query = select(tts_conversions).where(
        tts_conversions.c.video_id == video_id)
    tts_records = await database.fetch_all(tts_query)
    for tts_record in tts_records:
        if os.path.exists(tts_record["path"]):
            os.remove(tts_record["path"])
    await database.execute(delete(tts_conversions).where(tts_conversions.c.video_id == video_id))
