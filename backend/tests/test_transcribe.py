import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.transcription import (
    init_model,
    cleanup_model,
    is_model_available,
    get_model_error,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_model_state():
    """Reset model state before each test."""
    import app.services.transcription as trans_module
    trans_module._whisper_model = None
    trans_module._model_loaded = False
    trans_module._model_error = None
    yield
    trans_module._whisper_model = None
    trans_module._model_loaded = False
    trans_module._model_error = None


class TestHealthEndpoints:
    def test_root(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "RECALL AI API"
        assert "message" in data
        assert data["version"] == "0.1.0"

    def test_health(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "recall-ai-backend"

    def test_health_v1_model_unavailable(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["transcription"]["status"] == "unavailable"

    def test_unknown_endpoint(self, client: TestClient):
        response = client.get("/nonexistent")
        assert response.status_code == 404


class TestTranscribeEndpoint:
    def test_transcribe_missing_file(self, client: TestClient):
        response = client.post("/api/v1/transcribe")
        assert response.status_code == 422

    def test_transcribe_empty_file(self, client: TestClient):
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("empty.mp3", b"", "audio/mpeg")},
        )
        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    def test_transcribe_unsupported_format(self, client: TestClient):
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.txt", b"some text content", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]

    def test_transcribe_oversized_file(self, client: TestClient):
        large_content = b"x" * (101 * 1024 * 1024)
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("large.mp3", large_content, "audio/mpeg")},
        )
        assert response.status_code == 400
        assert "exceeds maximum allowed" in response.json()["detail"]

    def test_transcribe_model_unavailable(self, client: TestClient):
        audio_content = b"fake audio content"
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", audio_content, "audio/mpeg")},
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()

    @patch("app.api.routes.is_model_available", return_value=True)
    @patch("app.api.routes.transcribe_audio")
    def test_transcribe_success(self, mock_transcribe, mock_available, client: TestClient):
        mock_transcribe.return_value = (
            "Hello world this is a test",
            [{"start": 0.0, "end": 2.5, "text": "Hello world this is a test"}],
            2.5,
            "en",
        )

        audio_content = b"fake audio content"
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", audio_content, "audio/mpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.mp3"
        assert data["language"] == "en"
        assert data["duration_seconds"] == 2.5
        assert data["text"] == "Hello world this is a test"
        assert len(data["segments"]) == 1
        assert data["segments"][0]["start"] == 0.0
        assert data["segments"][0]["end"] == 2.5
        assert data["segments"][0]["text"] == "Hello world this is a test"

    @patch("app.api.routes.is_model_available", return_value=True)
    @patch("app.api.routes.transcribe_audio")
    def test_transcribe_with_language_override(self, mock_transcribe, mock_available, client: TestClient):
        mock_transcribe.return_value = (
            "Hola mundo",
            [{"start": 0.0, "end": 2.0, "text": "Hola mundo"}],
            2.0,
            "es",
        )

        audio_content = b"fake audio content"
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", audio_content, "audio/mpeg")},
            data={"language": "es"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "es"

    @patch("app.api.routes.is_model_available", return_value=True)
    @patch("app.api.routes.transcribe_audio")
    def test_transcribe_empty_transcript(self, mock_transcribe, mock_available, client: TestClient):
        mock_transcribe.return_value = (
            "",
            [],
            5.0,
            "en",
        )

        audio_content = b"fake audio content"
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("silence.mp3", audio_content, "audio/mpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == ""
        assert data["segments"] == []
        assert data["duration_seconds"] == 5.0

    @patch("app.api.routes.is_model_available", return_value=True)
    @patch("app.api.routes.transcribe_audio")
    def test_transcribe_engine_failure(self, mock_transcribe, mock_available, client: TestClient):
        mock_transcribe.side_effect = RuntimeError("Model inference failed")

        audio_content = b"fake audio content"
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", audio_content, "audio/mpeg")},
        )

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

    @pytest.mark.parametrize("ext", [".mp3", ".wav", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".mpeg"])
    def test_transcribe_supported_formats(self, client: TestClient, ext: str):
        response = client.post(
            "/api/v1/transcribe",
            files={"file": (f"test{ext}", b"audio content", "audio/mpeg")},
        )
        assert response.status_code != 400 or "Unsupported" not in response.json().get("detail", "")


class TestModelInitialization:
    def test_model_init_and_cleanup(self):
        init_model()
        # Model may or may not load depending on environment
        # Just verify the functions don't crash
        is_model_available()
        get_model_error()
        cleanup_model()


class TestLanguageValidation:
    def test_transcribe_omitted_language(self, client: TestClient):
        """Omitted language should be treated as auto-detect (not an error)."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
        )
        # Should not be 400 due to language validation
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_blank_language(self, client: TestClient):
        """Blank language should be treated as auto-detect."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": ""},
        )
        # Should not be 400 due to language validation
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_swagger_placeholder_string(self, client: TestClient):
        """Literal 'string' placeholder should be treated as auto-detect."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "string"},
        )
        # Should not be 400 due to language validation
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_valid_language(self, client: TestClient):
        """Valid language code should be accepted."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "en"},
        )
        # Should not be 400 due to language validation
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_valid_language_hi(self, client: TestClient):
        """Valid language code 'hi' should be accepted."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "hi"},
        )
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_valid_language_ta(self, client: TestClient):
        """Valid language code 'ta' should be accepted."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "ta"},
        )
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_invalid_language(self, client: TestClient):
        """Invalid language code should return 400."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "invalid"},
        )
        assert response.status_code == 400
        assert "language" in response.json()["detail"].lower()
        assert "invalid" in response.json()["detail"].lower()

    def test_transcribe_case_insensitive_language(self, client: TestClient):
        """Language codes should be normalized to lowercase (EN -> en)."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "EN"},
        )
        # EN should be normalized to 'en' and accepted (not a 400 for language)
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()

    def test_transcribe_language_with_whitespace(self, client: TestClient):
        """Language with surrounding whitespace should be trimmed and validated."""
        response = client.post(
            "/api/v1/transcribe",
            files={"file": ("test.mp3", b"audio content", "audio/mpeg")},
            data={"language": "  en  "},
        )
        # Should be treated as 'en' after trimming
        assert response.status_code != 400 or "language" not in response.json().get("detail", "").lower()


class TestOpenAPISchema:
    def test_openapi_schema_includes_required_endpoints(self, client: TestClient):
        """Verify the generated OpenAPI schema includes all required endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        # Check GET /health exists
        assert "/health" in paths
        assert "get" in paths["/health"]

        # Check POST /api/v1/transcribe exists
        assert "/api/v1/transcribe" in paths
        assert "post" in paths["/api/v1/transcribe"]

        # Verify transcription response schema is present
        components = schema.get("components", {})
        schemas = components.get("schemas", {})
        assert "TranscriptionResponse" in schemas
        assert "TranscriptionSegment" in schemas