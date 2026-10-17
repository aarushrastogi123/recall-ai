import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSmartNotesAPI:
    def test_smart_notes_valid_transcript(self, client: TestClient):
        transcript = """
        Team, thanks for joining the Q4 planning meeting. We discussed the budget allocation for next quarter.
        The finance team presented the revenue forecast showing 20% growth year over year.
        John will send the detailed budget report by Friday.
        We decided to approve the marketing budget increase of 50k.
        Sarah needs to review the hiring plan before the end of the month.
        The project launch is scheduled for March 15th.
        Action: Assign the API documentation task to Mike.
        We agreed to postpone the mobile app redesign to Q1.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "summary" in data
        assert data["summary"]
        assert "key_points" in data
        assert isinstance(data["key_points"], list)
        assert len(data["key_points"]) > 0
        assert "action_items" in data
        assert isinstance(data["action_items"], list)
        assert len(data["action_items"]) >= 1
        assert "decisions" in data
        assert isinstance(data["decisions"], list)
        assert len(data["decisions"]) >= 1
        assert "sections" in data
        assert isinstance(data["sections"], list)
        assert "language" in data
        assert data["language"] == "en"

        # Check action item extraction
        action_descs = [a["description"].lower() for a in data["action_items"]]
        assert any("report" in d for d in action_descs) or any("documentation" in d for d in action_descs)

    def test_smart_notes_no_action_items_or_decisions(self, client: TestClient):
        transcript = "The weather today is sunny. The team had a casual chat about weekend plans."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]
        assert data["action_items"] == []
        assert data["decisions"] == []
        assert data["language"] == "en"

    def test_smart_notes_missing_transcript(self, client: TestClient):
        response = client.post(
            "/api/v1/notes",
            json={"language": "en"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_smart_notes_empty_transcript(self, client: TestClient):
        response = client.post(
            "/api/v1/notes",
            json={"transcript": "", "language": "en"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_smart_notes_whitespace_only_transcript(self, client: TestClient):
        response = client.post(
            "/api/v1/notes",
            json={"transcript": "   \n\t  ", "language": "en"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_smart_notes_optional_language_omitted(self, client: TestClient):
        transcript = "We discussed the project timeline. John will send the update by Friday."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None

    def test_smart_notes_language_none_explicit(self, client: TestClient):
        transcript = "We discussed the project timeline. John will send the update by Friday."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None

    @patch("app.api.routes.generate_smart_notes")
    def test_smart_notes_service_error_no_internal_details(self, mock_generate, client: TestClient):
        mock_generate.side_effect = RuntimeError("Internal service failure")

        transcript = "Valid transcript with enough content here."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "failed" in data["detail"].lower()
        assert "Internal service failure" not in data["detail"]
        assert "RuntimeError" not in data["detail"]
        assert "traceback" not in data["detail"].lower()

    def test_smart_notes_invalid_json(self, client: TestClient):
        response = client.post(
            "/api/v1/notes",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_smart_notes_response_structure_complete(self, client: TestClient):
        transcript = """
        The quarterly budget review meeting covered revenue targets and expense management.
        Revenue increased 15% compared to last quarter.
        Marketing spend will be reduced by 10%.
        The team agreed to hire two new engineers by Q1.
        We decided to delay the product launch by two weeks.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields exist with correct types
        assert isinstance(data["summary"], str)
        assert isinstance(data["key_points"], list)
        assert isinstance(data["action_items"], list)
        assert isinstance(data["decisions"], list)
        assert isinstance(data["sections"], list)
        assert data["language"] == "en"

        # Verify nested structures
        for kp in data["key_points"]:
            assert "text" in kp
            assert isinstance(kp["text"], str)

        for ai in data["action_items"]:
            assert "description" in ai
            assert isinstance(ai["description"], str)
            assert "owner" in ai
            assert "deadline" in ai

        for dec in data["decisions"]:
            assert "description" in dec
            assert isinstance(dec["description"], str)
            assert "context" in dec

        for sec in data["sections"]:
            assert "title" in sec
            assert "summary" in sec
            assert "key_points" in sec
            assert "action_items" in sec
            assert "decisions" in sec


class TestSmartNotesOpenAPISchema:
    def test_openapi_schema_includes_smart_notes_endpoint(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        assert "/api/v1/notes" in paths
        assert "post" in paths["/api/v1/notes"]

    def test_openapi_schema_includes_smart_notes_schemas(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        assert "SmartNotesRequest" in schemas
        assert "SmartNotesResponse" in schemas
        assert "ActionItem" in schemas
        assert "Decision" in schemas
        assert "KeyPoint" in schemas
        assert "Section" in schemas