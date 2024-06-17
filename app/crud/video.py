import os
from sqlalchemy import select, update, delete
from fastapi import HTTPException
from pytube import YouTube
from pydub import AudioSegment
from app.database import database
from app.models import videos, fragments, translations, tts_conversions
from app.crud.fragment import delete_fragments_by_video
from app.crud.translation import delete_translations_by_video
from app.crud.tts import delete_tts_by_video


async def create_video(url: str):
    query = select(videos).where(videos.c.youtube_url == url)
    video_record = await database.fetch_one(query)

    if video_record:
        return video_record['id']
    else:
        query = videos.insert().values(youtube_url=url, processed=False)
        video_id = await database.execute(query)
        return video_id


async def process_video(video_id: int, url: str, fragment_duration: int):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        output_file = stream.download()

        audio = AudioSegment.from_file(output_file)
        duration = len(audio)
        chunk_duration = fragment_duration * 1000  # Convertir a milisegundos

        if not os.path.exists("audios"):
            os.makedirs("audios")

        for i in range(0, duration, chunk_duration):
            start_time = i
            end_time = min(i + chunk_duration, duration)
            chunk = audio[start_time:end_time]
            chunk_file = f"audios/{video_id}_chunk_{start_time // 1000}-{end_time // 1000}.mp3"
            chunk.export(chunk_file, format="mp3")

            query = fragments.insert().values(
                video_id=video_id,
                file_path=chunk_file,
                processed=False,
                start_time=start_time // 1000,
                end_time=end_time // 1000
            )
            await database.execute(query)

        os.remove(output_file)
        await database.execute(update(videos).where(videos.c.id == video_id).values(processed=True))

        return {"message": "Video audio has been split and saved.", "video_id": video_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def delete_video(video_id: int):
    # Eliminar registros de TTS
    await delete_tts_by_video(video_id)

    # Eliminar registros de traducciones
    await delete_translations_by_video(video_id)

    # Eliminar registros de fragmentos y archivos de fragmentos
    await delete_fragments_by_video(video_id)

    # Eliminar el registro del video
    await database.execute(delete(videos).where(videos.c.id == video_id))
