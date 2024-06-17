import os
from sqlalchemy import select, delete, insert, update
from app.database import database
from app.models import fragments


async def get_fragment(fragment_id: int):
    query = select(fragments).where(fragments.c.id == fragment_id)
    return await database.fetch_one(query)


async def insert_fragment(video_id: int, file_path: str, start_time: int, end_time: int):
    query = insert(fragments).values(
        video_id=video_id,
        file_path=file_path,
        processed=False,
        start_time=start_time,
        end_time=end_time
    )
    fragment_id = await database.execute(query)
    return fragment_id


async def update_fragment(fragment_id: int, transcription: str, language: str):
    query = update(fragments).where(fragments.c.id == fragment_id).values(
        transcription=transcription,
        processed=True,
        language=language
    )
    await database.execute(query)


async def delete_fragments_by_video(video_id: int):
    fragments_query = select(fragments).where(fragments.c.video_id == video_id)
    fragments_records = await database.fetch_all(fragments_query)
    for fragment_record in fragments_records:
        if os.path.exists(fragment_record["file_path"]):
            os.remove(fragment_record["file_path"])
    await database.execute(delete(fragments).where(fragments.c.video_id == video_id))
