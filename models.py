from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from database import metadata, engine

videos = Table(
    "videos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("youtube_url", String, unique=True, nullable=False),
    Column("processed", Boolean, default=False)
)

fragments = Table(
    "fragments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("videos.id")),
    Column("file_path", String, nullable=False),
    Column("processed", Boolean, default=False),
    Column("transcription", Text),
    Column("language", String),
    Column("start_time", Integer),
    Column("end_time", Integer)
)

translations = Table(
    "translations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("videos.id")),
    Column("fragment_id", Integer, ForeignKey("fragments.id")),
    Column("translated_text", Text),
    Column("language", String),
    Column("start_time", Integer),
    Column("end_time", Integer)
)

tts_conversions = Table(
    "tts_conversions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("videos.id")),
    Column("fragment_id", Integer, ForeignKey("fragments.id")),
    Column("path", String, nullable=False),
    Column("language", String),
    Column("voice", String),
    Column("start_time", Integer),
    Column("end_time", Integer)
)

metadata.create_all(engine)
