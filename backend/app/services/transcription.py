import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment

from app.config import settings

logger = logging.getLogger(__name__)

# Global model instance
_whisper_model: Optional[WhisperModel] = None
_model_loaded: bool = False
_model_error: Optional[str] = None

SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".mp4",
    ".webm", ".ogg", ".flac", ".mpeg"
}

# Language codes supported by faster-whisper (ISO 639-1)
SUPPORTED_LANGUAGES = {
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca",
    "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr",
    "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it",
    "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv",
    "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no",
    "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn",
    "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr",
    "tt", "uk", "ur", "uz", "vi", "yi", "yo", "zh", "yue"
}


def get_model() -> Optional[WhisperModel]:
    """Return the loaded Whisper model, or None if not available."""
    return _whisper_model


def is_model_available() -> bool:
    """Check if the model is loaded and ready."""
    return _model_loaded and _whisper_model is not None


def get_model_error() -> Optional[str]:
    """Return the model loading error message if any."""
    return _model_error


def init_model() -> None:
    """Initialize the Whisper model during application startup."""
    global _whisper_model, _model_loaded, _model_error

    logger.info(
        f"Initializing Whisper model: {settings.whisper_model} "
        f"(device={settings.whisper_device}, compute_type={settings.whisper_compute_type})"
    )

    try:
        _whisper_model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            download_root=settings.whisper_download_root,
        )
        _model_loaded = True
        _model_error = None
        logger.info("Whisper model initialized successfully")
    except Exception as e:
        _model_loaded = False
        _whisper_model = None
        _model_error = f"Failed to load Whisper model: {type(e).__name__}"
        logger.exception("Whisper model initialization failed")


def cleanup_model() -> None:
    """Clean up the model during application shutdown."""
    global _whisper_model, _model_loaded
    if _whisper_model is not None:
        logger.info("Cleaning up Whisper model")
        _whisper_model = None
        _model_loaded = False


def validate_audio_file(filename: str, file_size: int) -> Optional[str]:
    """Validate uploaded audio file. Returns error message if invalid, None if valid."""
    if not filename:
        return "No filename provided"

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return f"Unsupported file format: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"

    if file_size == 0:
        return "Empty file uploaded"

    if file_size > settings.max_upload_size:
        max_mb = settings.max_upload_size / (1024 * 1024)
        return f"File size exceeds maximum allowed ({max_mb:.0f} MB)"

    return None


def transcribe_audio(
    file_path: str,
    language: Optional[str] = None,
) -> tuple[str, list[dict], float, str]:
    """
    Transcribe audio file using the loaded Whisper model.

    Returns:
        tuple: (full_text, segments_list, duration_seconds, detected_language)
    """
    if not is_model_available():
        raise RuntimeError("Transcription service unavailable: model not loaded")

    model = get_model()
    if model is None:
        raise RuntimeError("Transcription service unavailable: model not loaded")

    # Run transcription in thread pool since it's CPU-bound
    import concurrent.futures

    def _transcribe():
        segments, info = model.transcribe(
            file_path,
            language=language,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            beam_size=5,
        )
        # Consume the generator to get all segments
        segment_list = list(segments)
        full_text = " ".join(s.text for s in segment_list).strip()
        segments_data = [
            {
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
            }
            for s in segment_list
        ]
        return full_text, segments_data, info.duration, info.language

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_transcribe)
        return future.result()


@asynccontextmanager
async def save_upload_to_temp(upload_file):
    """
    Save uploaded file to a secure temporary file.
    Yields the temporary file path.
    Guarantees cleanup on exit.
    """
    temp_dir = Path(tempfile.gettempdir()) / "recall-ai-uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Use a secure random filename
    import secrets
    suffix = Path(upload_file.filename).suffix.lower() if upload_file.filename else ".tmp"
    temp_filename = f"{secrets.token_urlsafe(16)}{suffix}"
    temp_path = temp_dir / temp_filename

    try:
        # Write in chunks to avoid loading entire file into memory
        with open(temp_path, "wb") as f:
            while chunk := await upload_file.read(8192):
                f.write(chunk)
        yield str(temp_path)
    finally:
        # Clean up temp file
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete temp file {temp_path}: {e}")

        # Try to remove temp dir if empty
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except Exception:
            pass