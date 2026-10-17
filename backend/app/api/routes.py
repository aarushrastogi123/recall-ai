import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.services.transcription import (
    get_model,
    is_model_available,
    get_model_error,
    validate_audio_file,
    transcribe_audio,
    save_upload_to_temp,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_LANGUAGES,
)
from app.models.smart_notes import SmartNotesRequest, SmartNotesResponse
from app.services.smart_notes import generate_smart_notes

logger = logging.getLogger(__name__)

router = APIRouter()


class TranscriptionSegment(BaseModel):
    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text")


class TranscriptionResponse(BaseModel):
    filename: str = Field(..., description="Original filename")
    language: str = Field(..., description="Detected or specified language")
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    text: str = Field(..., description="Full transcribed text")
    segments: list[TranscriptionSegment] = Field(default_factory=list, description="Individual segments")


@router.get("/")
async def root():
    return {
        "name": "RECALL AI API",
        "message": "Welcome to RECALL AI - your AI Meeting & Lecture Copilot",
        "version": "0.1.0",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "recall-ai-backend"}


@router.get("/api/v1/health")
async def health_v1():
    model_status = "loaded" if is_model_available() else "unavailable"
    response = {
        "status": "ok",
        "service": "recall-ai-backend",
        "version": "0.1.0",
        "transcription": {
            "status": model_status,
            "model": "base" if is_model_available() else None,
        },
    }
    if not is_model_available():
        error = get_model_error()
        if error:
            response["transcription"]["error"] = error
    return response


@router.post(
    "/api/v1/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio file",
    description="Upload an audio file for transcription using faster-whisper.",
)
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(
        None,
        description="Optional language code (e.g., 'en', 'es'). Auto-detected if not specified.",
    ),
):
    filename = file.filename or "unknown"

    # Validate filename extension early (before saving)
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Upload validation failed: Unsupported file format: {ext}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Validate and normalize language parameter
    if language is not None:
        language = language.strip().lower()
        if not language or language == "string":
            # Treat empty string or Swagger placeholder as auto-detect
            language = None
        elif language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Invalid language code: {language}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported language code: '{language}'. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}",
            )

    # Save file to temp first to get actual file size
    async with save_upload_to_temp(file) as temp_path:
        import os
        file_size = os.path.getsize(temp_path)

        validation_error = validate_audio_file(filename, file_size)
        if validation_error:
            logger.warning(f"Upload validation failed: {validation_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation_error,
            )

        if not is_model_available():
            error = get_model_error() or "Whisper model not initialized"
            logger.warning(f"Transcription requested but model unavailable: {error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Transcription service temporarily unavailable. Model not loaded.",
            )

        try:
            full_text, segments, duration, detected_lang = transcribe_audio(
                temp_path, language=language
            )
        except RuntimeError as e:
            logger.error(f"Transcription runtime error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transcription failed",
            )
        except Exception as e:
            logger.exception("Unexpected transcription error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Transcription failed due to an unexpected error",
            )

    logger.info(
        f"Transcription completed: {filename} "
        f"({detected_lang}, {duration:.1f}s, {len(segments)} segments)"
    )

    return TranscriptionResponse(
        filename=filename,
        language=detected_lang,
        duration_seconds=round(duration, 2),
        text=full_text,
        segments=[TranscriptionSegment(**s) for s in segments],
    )


@router.post(
    "/api/v1/notes",
    response_model=SmartNotesResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate smart notes from transcript",
    description="Generate structured smart notes (summary, key points, action items, decisions, sections) from a meeting transcript.",
)
async def create_smart_notes(request: SmartNotesRequest) -> SmartNotesResponse:
    try:
        return generate_smart_notes(request)
    except ValueError as e:
        logger.warning(f"Smart notes validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected smart notes generation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Smart notes generation failed due to an unexpected error",
        )