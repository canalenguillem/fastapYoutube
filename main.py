from fastapi import FastAPI, HTTPException, Query
from pytube import YouTube
from pydub import AudioSegment
import speech_recognition as sr
from googletrans import Translator
import os
from sqlalchemy import select, delete
from sqlalchemy.engine import Result
from database import database, engine
from models import videos, fragments, translations, tts_conversions
from libraries.ttsmp3 import TtsMp3
from libraries.elevenlabs_tts import convert_text_to_speech

app = FastAPI()

translator = Translator()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/transcribe/")
async def transcribe_youtube_video(url: str, fragment_duration: int = Query(100, gt=0)):
    query = select(videos).where(videos.c.youtube_url == url)
    video_record = await database.fetch_one(query)

    if video_record:
        video_id = video_record['id']
    else:
        query = videos.insert().values(youtube_url=url, processed=False)
        video_id = await database.execute(query)

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

        return {"message": "Video audio has been split and saved.", "video_id": video_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process_fragment/")
async def process_fragment(fragment_id: int):
    query = select(fragments).where(fragments.c.id == fragment_id)
    fragment_record = await database.fetch_one(query)

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

    query = fragments.update().where(fragments.c.id == fragment_id).values(
        transcription=text,
        processed=True,
        language="es-ES"
    )
    await database.execute(query)

    return {"message": "Fragment processed", "transcription": text}


@app.get("/video_fragments/{video_id}")
async def get_video_fragments(video_id: int):
    query = select(fragments).where(fragments.c.video_id == video_id)
    results = await database.fetch_all(query)

    if not results:
        raise HTTPException(status_code=404, detail="Video not found")

    return {"fragments": results}


@app.post("/translate_fragment/")
async def translate_fragment(fragment_id: int, target_language: str = "en"):
    query = select(fragments).where(fragments.c.id == fragment_id)
    fragment_record = await database.fetch_one(query)

    if not fragment_record:
        raise HTTPException(status_code=404, detail="Fragment not found")

    if not fragment_record['transcription']:
        raise HTTPException(
            status_code=400, detail="Fragment has not been transcribed yet")

    translated_text = translator.translate(
        fragment_record['transcription'], dest=target_language).text

    query = translations.insert().values(
        video_id=fragment_record['video_id'],
        fragment_id=fragment_record['id'],
        translated_text=translated_text,
        language=target_language,
        start_time=fragment_record['start_time'],
        end_time=fragment_record['end_time']
    )
    await database.execute(query)

    return {"message": "Fragment translated", "translated_text": translated_text}


@app.post("/text_to_speech/")
async def text_to_speech(fragment_id: int, voice: str = "Lucia"):
    query = select(fragments).where(fragments.c.id == fragment_id)
    fragment_record = await database.fetch_one(query)

    if not fragment_record:
        raise HTTPException(status_code=404, detail="Fragment not found")

    if not fragment_record['transcription']:
        raise HTTPException(
            status_code=400, detail="Fragment has not been transcribed yet")

    tts = TtsMp3()
    result = tts.tts(fragment_record['transcription'], voz=voice)

    if result['res'] != "OK":
        raise HTTPException(status_code=500, detail=result['res'])

    if not os.path.exists("tts"):
        os.makedirs("tts")

    output_file = f"tts/{fragment_id}_tts_{voice}.mp3"
    with open(output_file, "wb") as f:
        f.write(result['audio'])

    query = tts_conversions.insert().values(
        video_id=fragment_record['video_id'],
        fragment_id=fragment_id,
        path=output_file,
        language="es-ES",
        voice=voice,
        start_time=fragment_record['start_time'],
        end_time=fragment_record['end_time']
    )
    await database.execute(query)

    return {"message": "Text to speech conversion done", "file_path": output_file}


@app.post("/elevenlabs_text_to_speech/")
async def elevenlabs_text_to_speech(fragment_id: int):
    query = select(fragments).where(fragments.c.id == fragment_id)
    fragment_record = await database.fetch_one(query)

    if not fragment_record:
        raise HTTPException(status_code=404, detail="Fragment not found")

    if not fragment_record['transcription']:
        raise HTTPException(
            status_code=400, detail="Fragment has not been transcribed yet")

    audio_content = convert_text_to_speech(fragment_record['transcription'])

    if audio_content is None:
        raise HTTPException(
            status_code=500, detail="Error converting text to speech with ElevenLabs")

    if not os.path.exists("tts"):
        os.makedirs("tts")

    output_file = f"tts/{fragment_id}_tts_elevenlabs.mp3"
    with open(output_file, "wb") as f:
        f.write(audio_content)

    query = tts_conversions.insert().values(
        video_id=fragment_record['video_id'],
        fragment_id=fragment_id,
        path=output_file,
        language="es-ES",
        voice="Rachel",
        start_time=fragment_record['start_time'],
        end_time=fragment_record['end_time']
    )
    await database.execute(query)

    return {"message": "Text to speech conversion done", "file_path": output_file}


@app.post("/elevenlabs_translated_tts/")
async def elevenlabs_translated_tts(fragment_id: int, target_language: str = "en"):
    query = select(translations).where(translations.c.fragment_id ==
                                       fragment_id).where(translations.c.language == target_language)
    translation_record = await database.fetch_one(query)

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

    query = tts_conversions.insert().values(
        video_id=translation_record['video_id'],
        fragment_id=fragment_id,
        path=output_file,
        language=target_language,
        voice="Rachel",
        start_time=translation_record['start_time'],
        end_time=translation_record['end_time']
    )
    await database.execute(query)

    return {"message": "Text to speech conversion done", "file_path": output_file}


@app.delete("/delete_video/{video_id}")
async def delete_video(video_id: int):
    # Eliminar registros de TTS
    tts_query = select(tts_conversions).where(
        tts_conversions.c.video_id == video_id)
    tts_records = await database.fetch_all(tts_query)
    for tts_record in tts_records:
        if os.path.exists(tts_record["path"]):
            os.remove(tts_record["path"])
    await database.execute(delete(tts_conversions).where(tts_conversions.c.video_id == video_id))

    # Eliminar registros de traducciones
    translations_query = select(translations).where(
        translations.c.video_id == video_id)
    translations_records = await database.fetch_all(translations_query)
    await database.execute(delete(translations).where(translations.c.video_id == video_id))

    # Eliminar registros de fragmentos y archivos de fragmentos
    fragments_query = select(fragments).where(fragments.c.video_id == video_id)
    fragments_records = await database.fetch_all(fragments_query)
    for fragment_record in fragments_records:
        if os.path.exists(fragment_record["file_path"]):
            os.remove(fragment_record["file_path"])
    await database.execute(delete(fragments).where(fragments.c.video_id == video_id))

    # Eliminar el registro del video
    await database.execute(delete(videos).where(videos.c.id == video_id))

    return {"message": "Video and all associated data deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
