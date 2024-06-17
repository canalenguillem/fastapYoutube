from fastapi import APIRouter, HTTPException, Query
from app.crud.video import create_video, process_video, delete_video

router = APIRouter()


@router.delete("/delete_video/{video_id}")
async def delete_video_endpoint(video_id: int):
    await delete_video(video_id)
    return {"message": "Video and all associated data deleted successfully"}


@router.post("/transcribe/")
async def transcribe_youtube_video(url: str, fragment_duration: int = Query(100, gt=0)):
    video_id = await create_video(url)
    response = await process_video(video_id, url, fragment_duration)
    return response


@router.get("/generate_srt/{video_id}")
async def generate_srt(video_id: int):
    fragments = await get_fragments_by_video(video_id)
    if not fragments:
        raise HTTPException(
            status_code=404, detail="No fragments found for the given video ID")

    subtitles = []
    for fragment in fragments:
        if fragment['transcription']:
            subtitles.append({
                "start_time": fragment['start_time'],
                "end_time": fragment['end_time'],
                "text": fragment['transcription']
            })

    output_path = f"tts/{video_id}.srt"
    create_srt(subtitles, output_path)

    return {"message": "SRT file generated", "file_path": output_path}
