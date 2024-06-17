from fastapi import APIRouter
from app.routers import video, fragment, translation, tts

router = APIRouter()
router.include_router(video.router, prefix="/video", tags=["video"])
router.include_router(fragment.router, prefix="/fragment", tags=["fragment"])
router.include_router(translation.router,
                      prefix="/translation", tags=["translation"])
router.include_router(tts.router, prefix="/tts", tags=["tts"])
