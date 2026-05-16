"""TTS (Text-to-Speech) route and shared helper."""
from __future__ import annotations
import io

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.api.middleware import limiter

router = APIRouter(tags=["Public"])


async def _generate_tts_bytes(text: str) -> bytes:
    """Dùng edge-tts tạo file MP3 từ văn bản, voice tiếng Việt HoaiMy."""
    try:
        import edge_tts
    except ImportError:
        raise RuntimeError("edge-tts chưa được cài. Chạy: pip install edge-tts")

    communicate = edge_tts.Communicate(text, voice="vi-VN-HoaiMyNeural")
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


@router.post("/public/tts")
@limiter.limit("20/minute")
async def public_tts(request: Request):
    """Tạo TTS MP3 cho văn bản công khai (không cần đăng nhập).
    Rate-limit: 20 req/phút/IP.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Body JSON không hợp lệ.")

    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text trống.")
    if len(text) > 3000:
        text = text[:3000]

    try:
        audio_bytes = await _generate_tts_bytes(text)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not audio_bytes:
        raise HTTPException(status_code=503, detail="edge-tts trả về dữ liệu trống.")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=tts.mp3"},
    )
