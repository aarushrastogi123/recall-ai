import pytest
from pydantic import ValidationError

from app.models.smart_notes import (
    SmartNotesRequest,
    SmartNotesResponse,
    ActionItem,
    Decision,
    KeyPoint,
    Section,
)


class TestSmartNotesRequest:
    def test_valid_request(self):
        req = SmartNotesRequest(transcript="This is a test transcript.", language="en")
        assert req.transcript == "This is a test transcript."
        assert req.language == "en"

    def test_valid_request_no_language(self):
        req = SmartNotesRequest(transcript="  Test transcript with whitespace  ")
        assert req.transcript == "Test transcript with whitespace"
        assert req.language is None

    def test_empty_transcript_raises(self):
        with pytest.raises(ValidationError) as exc:
            SmartNotesRequest(transcript="")
        assert "Transcript must not be empty" in str(exc.value)

    def test_whitespace_only_transcript_raises(self):
        with pytest.raises(ValidationError) as exc:
            SmartNotesRequest(transcript="   \n\t  ")
        assert "Transcript must not be empty" in str(exc.value)

    def test_missing_transcript_raises(self):
        with pytest.raises(ValidationError) as exc:
            SmartNotesRequest()
        assert "transcript" in str(exc.value).lower()


class TestActionItem:
    def test_valid_action_item(self):
        item = ActionItem(description="Send report", owner="John", deadline="Friday")
        assert item.description == "Send report"
        assert item.owner == "John"
        assert item.deadline == "Friday"

    def test_action_item_minimal(self):
        item = ActionItem(description="Review code")
        assert item.description == "Review code"
        assert item.owner is None
        assert item.deadline is None

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError) as exc:
            ActionItem(owner="John")
        assert "description" in str(exc.value).lower()


class TestDecision:
    def test_valid_decision(self):
        dec = Decision(description="Approved budget", context="Q4 planning")
        assert dec.description == "Approved budget"
        assert dec.context == "Q4 planning"

    def test_decision_minimal(self):
        dec = Decision(description="Postpone launch")
        assert dec.description == "Postpone launch"
        assert dec.context is None

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError) as exc:
            Decision(context="Some context")
        assert "description" in str(exc.value).lower()


class TestKeyPoint:
    def test_valid_key_point(self):
        kp = KeyPoint(text="Revenue increased 20%")
        assert kp.text == "Revenue increased 20%"

    def test_missing_text_raises(self):
        with pytest.raises(ValidationError) as exc:
            KeyPoint()
        assert "text" in str(exc.value).lower()


class TestSection:
    def test_valid_section(self):
        sec = Section(
            title="Financials",
            summary="Revenue up",
            key_points=[KeyPoint(text="Revenue +20%")],
            action_items=[ActionItem(description="Review forecast")],
            decisions=[Decision(description="Approved budget")],
        )
        assert sec.title == "Financials"
        assert sec.summary == "Revenue up"
        assert len(sec.key_points) == 1
        assert len(sec.action_items) == 1
        assert len(sec.decisions) == 1

    def test_section_defaults(self):
        sec = Section(title="Notes", summary="General notes")
        assert sec.key_points == []
        assert sec.action_items == []
        assert sec.decisions == []

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError) as exc:
            Section(title="Only title")
        assert "summary" in str(exc.value).lower()


class TestSmartNotesResponse:
    def test_valid_response(self):
        resp = SmartNotesResponse(
            summary="Meeting discussed Q4 goals",
            key_points=[KeyPoint(text="Revenue target $1M")],
            action_items=[ActionItem(description="Prepare deck", owner="Alice")],
            decisions=[Decision(description="Approved budget")],
            sections=[
                Section(
                    title="Finance",
                    summary="Budget approved",
                    key_points=[KeyPoint(text="Q4 budget $500k")],
                )
            ],
            language="en",
        )
        assert resp.summary == "Meeting discussed Q4 goals"
        assert len(resp.key_points) == 1
        assert len(resp.action_items) == 1
        assert len(resp.decisions) == 1
        assert len(resp.sections) == 1
        assert resp.language == "en"

    def test_response_defaults(self):
        resp = SmartNotesResponse(summary="Quick meeting")
        assert resp.key_points == []
        assert resp.action_items == []
        assert resp.decisions == []
        assert resp.sections == []
        assert resp.language is None

    def test_missing_summary_raises(self):
        with pytest.raises(ValidationError) as exc:
            SmartNotesResponse()
        assert "summary" in str(exc.value).lower()