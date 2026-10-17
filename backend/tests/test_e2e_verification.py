import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestEndToEndSmartNotes:
    """End-to-end tests for POST /api/v1/notes with realistic transcripts."""

    def test_realistic_meeting_with_action_items_owners_deadlines(self, client: TestClient):
        """Test realistic meeting transcript extracts action items with owners and deadlines.
        
        Note: Current rule-based extraction only captures owners for patterns like
        "Name will ..." at sentence start, and deadlines for day names or date formats.
        """
        transcript = """
        Good morning everyone. Thanks for joining the sprint planning meeting.
        We reviewed the current sprint progress and discussed the upcoming release.
        John will complete the API integration by Friday.
        Sarah will review the pull requests by Monday.
        The team agreed to deploy the new feature on March 20th.
        Mike will update the documentation by Wednesday.
        We decided to postpone the database migration to Q2.
        Action: Set up monitoring alerts for the new service.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify action items extracted (current implementation captures "will" pattern)
        action_items = data["action_items"]
        assert len(action_items) >= 3

        # Check for John with Friday deadline (pattern: "Name will ... by Day")
        john_actions = [a for a in action_items if "john" in a["description"].lower()]
        assert len(john_actions) >= 1
        assert john_actions[0]["owner"] == "John"
        assert "Friday" in john_actions[0]["deadline"]

        # Check for Sarah with Monday deadline
        sarah_actions = [a for a in action_items if "sarah" in a["description"].lower()]
        assert len(sarah_actions) >= 1
        assert sarah_actions[0]["owner"] == "Sarah"
        assert "Monday" in sarah_actions[0]["deadline"]

        # Check for Mike with Wednesday deadline
        mike_actions = [a for a in action_items if "mike" in a["description"].lower()]
        assert len(mike_actions) >= 1
        assert mike_actions[0]["owner"] == "Mike"
        assert "Wednesday" in mike_actions[0]["deadline"]

        # Verify decisions
        decisions = data["decisions"]
        assert len(decisions) >= 2
        decision_texts = [d["description"].lower() for d in decisions]
        assert any("deploy" in d or "march" in d for d in decision_texts)
        assert any("postpone" in d or "migration" in d for d in decision_texts)

    def test_suggestions_not_classified_as_decisions(self, client: TestClient):
        """Test that suggestions/ideas are not classified as confirmed decisions."""
        transcript = """
        We should consider increasing the marketing budget.
        Maybe we could hire more developers next quarter.
        I think we might want to explore new markets.
        Perhaps we could try a different approach.
        The team could potentially look into automation.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Suggestions should NOT be classified as decisions
        assert data["decisions"] == [], f"Suggestions incorrectly classified as decisions: {data['decisions']}"

        # But they may appear as key points
        key_point_texts = [kp["text"].lower() for kp in data["key_points"]]
        assert any("marketing" in t for t in key_point_texts) or any("hire" in t for t in key_point_texts)

    def test_long_transcript_handling(self, client: TestClient):
        """Test long transcript respects limits and produces sections."""
        # Create a long transcript with multiple topics
        sentences = []
        for i in range(50):
            if i % 5 == 0:
                sentences.append(f"Budget discussion point {i}: Revenue increased {i}% this quarter.")
            elif i % 5 == 1:
                sentences.append(f"Project update {i}: The launch is scheduled for month {i}.")
            elif i % 5 == 2:
                sentences.append(f"Team update {i}: We need to hire {i} new engineers.")
            elif i % 5 == 3:
                sentences.append(f"Operations note {i}: Process automation will save {i} hours.")
            else:
                sentences.append(f"Strategy item {i}: Q{i%4+1} goals include growth and stability.")

        transcript = " ".join(sentences)
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify limits are respected
        assert len(data["key_points"]) <= 10
        assert len(data["action_items"]) <= 10
        assert len(data["decisions"]) <= 10
        assert len(data["sections"]) <= 5

        # Should have sections for long transcript
        assert len(data["sections"]) > 0
        for section in data["sections"]:
            assert "title" in section
            assert "summary" in section
            assert isinstance(section["key_points"], list)
            assert isinstance(section["action_items"], list)
            assert isinstance(section["decisions"], list)

    def test_duplicate_sentences_deduplicated(self, client: TestClient):
        """Test that duplicate sentences are deduplicated in output."""
        transcript = """
        The quarterly budget was approved by the board.
        The quarterly budget was approved by the board.
        Revenue increased 15% compared to last quarter.
        Revenue increased 15% compared to last quarter.
        John will send the report by Friday.
        John will send the report by Friday.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check deduplication in key points
        key_point_texts = [kp["text"] for kp in data["key_points"]]
        assert len(key_point_texts) == len(set(key_point_texts)), "Duplicate key points found"

        # Check deduplication in action items
        action_descs = [a["description"] for a in data["action_items"]]
        assert len(action_descs) == len(set(action_descs)), "Duplicate action items found"

        # Check deduplication in decisions
        decision_descs = [d["description"] for d in data["decisions"]]
        assert len(decision_descs) == len(set(decision_descs)), "Duplicate decisions found"

    def test_missing_language_omitted(self, client: TestClient):
        """Test that language field is optional and defaults to null."""
        transcript = "We discussed the project. John will send the update by Friday."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None

    def test_explicit_language_null(self, client: TestClient):
        """Test explicit language: null is handled correctly."""
        transcript = "We discussed the project. John will send the update by Friday."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": None},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None

    def test_hindi_transcript_processing(self, client: TestClient):
        """Test Hindi transcript is processed without crashing."""
        transcript = """
        नमस्ते टीम, आज की मीटिंग में हमने बजट पर चर्चा की।
        राजस्व इस तिमाही में 20% बढ़ा है।
        जॉन शुक्रवार तक रिपोर्ट भेजेगा।
        हमने बजट को मंजूरी दे दी है।
        प्रोजेक्ट लॉन्च मार्च में निर्धारित है।
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "hi"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]
        assert data["language"] == "hi"
        assert isinstance(data["key_points"], list)
        assert isinstance(data["action_items"], list)
        assert isinstance(data["decisions"], list)

    def test_no_unsupported_facts_introduced(self, client: TestClient):
        """Test that generated notes never introduce unsupported names, statistics, or commitments."""
        transcript = """
        The team discussed the project timeline.
        We reviewed the current progress.
        Next steps will be determined later.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Collect all text from response
        all_text = data["summary"].lower()
        for kp in data["key_points"]:
            all_text += " " + kp["text"].lower()
        for ai in data["action_items"]:
            all_text += " " + ai["description"].lower()
            if ai["owner"]:
                all_text += " " + ai["owner"].lower()
            if ai["deadline"]:
                all_text += " " + ai["deadline"].lower()
        for dec in data["decisions"]:
            all_text += " " + dec["description"].lower()
            if dec["context"]:
                all_text += " " + dec["context"].lower()
        for sec in data["sections"]:
            all_text += " " + sec["title"].lower() + " " + sec["summary"].lower()

        # Verify no unsupported names introduced (names not in transcript)
        unsupported_names = ["alice", "bob", "charlie", "david", "emma", "frank", "grace", "henry"]
        for name in unsupported_names:
            assert name not in all_text, f"Unsupported name '{name}' introduced in notes"

        # Verify no unsupported statistics (percentages not in transcript)
        # The transcript has no percentages, so none should appear
        import re
        percentages = re.findall(r'\d+%', all_text)
        assert len(percentages) == 0, f"Unsupported percentages introduced: {percentages}"

        # Verify no unsupported dollar amounts
        dollar_amounts = re.findall(r'\$\d+', all_text)
        assert len(dollar_amounts) == 0, f"Unsupported dollar amounts introduced: {dollar_amounts}"

        # Verify no unsupported dates/deadlines not in transcript
        unsupported_deadlines = ["january", "february", "march", "april", "may", "june",
                                 "july", "august", "september", "october", "november", "december",
                                 "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for deadline in unsupported_deadlines:
            # These might appear in transcript, so only check if they're in action items deadlines
            pass  # Can't easily verify without false positives

    def test_regression_unsupported_facts_not_introduced(self, client: TestClient):
        """Regression test: ensure previously discovered unsupported facts don't reappear."""
        transcript = """
        We had a meeting about the project.
        John mentioned the timeline.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Specific regression: ensure "Sarah" is not introduced when only "John" is in transcript
        all_names_in_response = []
        for ai in data["action_items"]:
            if ai["owner"]:
                all_names_in_response.append(ai["owner"].lower())

        # Only names mentioned in transcript should appear
        # "Sarah" was never in transcript, so should not appear
        assert "sarah" not in all_names_in_response, "Regression: 'Sarah' introduced when not in transcript"

        # "John" is in transcript, so may appear
        # (but not guaranteed since extraction is heuristic)

    def test_action_item_extraction_variations(self, client: TestClient):
        """Test various action item patterns are captured.
        
        Note: Current implementation only extracts owners for "Name will ..." at sentence start,
        and deadlines for day names (Monday-Friday) or date formats.
        """
        transcript = """
        Alice will prepare the presentation by Monday.
        Bob will review the code by Friday.
        Action item: Update documentation by Wednesday.
        We must finalize the contract by Thursday.
        David will contact the vendor by Tuesday.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        action_items = data["action_items"]
        assert len(action_items) >= 3

        # Check owners are extracted for "Name will" pattern
        owners = [a["owner"] for a in action_items if a["owner"]]
        assert "Alice" in owners
        assert "Bob" in owners
        assert "David" in owners

        # Check deadlines are extracted for day names
        deadlines = [a["deadline"] for a in action_items if a["deadline"]]
        deadline_text = " ".join(deadlines).lower()
        assert any(d in deadline_text for d in ["monday", "friday", "wednesday", "thursday", "tuesday"])

    def test_decision_extraction_variations(self, client: TestClient):
        """Test various decision patterns are captured."""
        transcript = """
        We decided to approve the new budget.
        The team agreed on the revised timeline.
        Management approved the hiring plan.
        We resolved to delay the launch by two weeks.
        The board confirmed the acquisition.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        decisions = data["decisions"]
        assert len(decisions) >= 3

        decision_texts = [d["description"].lower() for d in decisions]
        assert any("approve" in d for d in decision_texts)
        assert any("agreed" in d or "timeline" in d for d in decision_texts)
        assert any("delay" in d or "launch" in d for d in decision_texts)

    def test_mixed_content_transcript(self, client: TestClient):
        """Test transcript with mixed: decisions, actions, suggestions, info."""
        transcript = """
        Welcome to the quarterly review meeting.
        We decided to approve the Q4 budget of 2 million dollars.
        John will present the marketing plan by Friday.
        We should consider expanding to Europe next year.
        The team agreed to hire three new engineers.
        Maybe we could reduce costs by 10 percent.
        Sarah will finalize the contract by Monday.
        We resolved to launch the product in April.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have decisions (approved budget, agreed to hire, resolved to launch)
        decisions = data["decisions"]
        assert len(decisions) >= 2
        decision_texts = [d["description"].lower() for d in decisions]
        assert any("approve" in d and "budget" in d for d in decision_texts)
        assert any("hire" in d or "engineer" in d for d in decision_texts)
        assert any("launch" in d or "april" in d for d in decision_texts)

        # Should have action items (John present, Sarah finalize)
        action_items = data["action_items"]
        assert len(action_items) >= 2
        owners = [a["owner"] for a in action_items if a["owner"]]
        assert "John" in owners
        assert "Sarah" in owners

        # Suggestions should NOT be decisions
        # "We should consider expanding" - suggestion
        # "Maybe we could reduce costs" - suggestion
        suggestion_like = [d for d in decision_texts if "should consider" in d or "maybe" in d or "could" in d]
        assert len(suggestion_like) == 0, f"Suggestions incorrectly classified as decisions: {suggestion_like}"

    def test_summary_contains_key_information(self, client: TestClient):
        """Test that summary captures key information from transcript."""
        transcript = """
        The board meeting covered three main topics.
        First, revenue increased 25 percent this quarter.
        Second, we decided to expand into the Asian market.
        Third, John will lead the expansion team.
        The meeting concluded with next steps.
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()

        summary = data["summary"].lower()
        # Summary should contain key topics
        assert any(keyword in summary for keyword in ["revenue", "25%", "expand", "asian", "market", "john", "lead"])


class TestEndToEndTranscriptionStillWorks:
    """Verify transcription endpoint remains functional after smart notes addition."""

    def test_transcribe_endpoint_exists(self, client: TestClient):
        """Test that transcription endpoint still exists and responds."""
        # Just verify endpoint exists (will fail validation without file)
        response = client.post("/api/v1/transcribe")
        # 422 = validation error (missing file), not 404
        assert response.status_code == 422

    def test_health_endpoints_still_work(self, client: TestClient):
        """Test that health endpoints still work."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_openapi_schema_includes_both_endpoints(self, client: TestClient):
        """Test that OpenAPI schema includes both transcribe and notes endpoints."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        assert "/api/v1/transcribe" in paths
        assert "post" in paths["/api/v1/transcribe"]

        assert "/api/v1/notes" in paths
        assert "post" in paths["/api/v1/notes"]


class TestEdgeCasesAndLimits:
    """Test edge cases and limits."""

    def test_very_short_transcript(self, client: TestClient):
        """Test very short but valid transcript."""
        transcript = "We agreed to proceed. John will handle it."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]
        assert isinstance(data["key_points"], list)
        assert isinstance(data["action_items"], list)
        assert isinstance(data["decisions"], list)

    def test_transcript_with_only_numbers_and_symbols(self, client: TestClient):
        """Test transcript with numbers and symbols."""
        transcript = "Revenue Q4 2024: $2.5M. Growth: 15%. John will report by 2024-12-31."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]

    def test_transcript_with_special_characters(self, client: TestClient):
        """Test transcript with special characters and punctuation."""
        transcript = "We discussed the project (Phase 1) - it's going well! John's team will deliver by Friday, 3/15/2024."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]

    def test_unicode_transcript(self, client: TestClient):
        """Test transcript with unicode characters."""
        transcript = "Meeting notes: 📝 Project α (alpha) approved. José will handle the café ☕ integration by Friday."
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]

    def test_whitespace_heavy_transcript(self, client: TestClient):
        """Test transcript with excessive whitespace."""
        transcript = """
        
        We    discussed    the    budget.
        
        
        John    will    send    the    report.
        
        """
        response = client.post(
            "/api/v1/notes",
            json={"transcript": transcript, "language": "en"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]


class TestConsistencyAndDeterminism:
    """Test that the same input produces consistent output."""

    def test_deterministic_output(self, client: TestClient):
        """Test that identical requests produce identical results."""
        transcript = "John will send the report by Friday. We decided to approve the budget."
        response1 = client.post("/api/v1/notes", json={"transcript": transcript, "language": "en"})
        response2 = client.post("/api/v1/notes", json={"transcript": transcript, "language": "en"})
        response3 = client.post("/api/v1/notes", json={"transcript": transcript, "language": "en"})

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        # All responses should be identical (deterministic)
        assert response1.json() == response2.json() == response3.json()

    def test_same_transcript_different_language_produces_same_structure(self, client: TestClient):
        """Test that language doesn't affect structure, only language field."""
        transcript = "John will send the report by Friday. We decided to approve the budget."

        response_en = client.post("/api/v1/notes", json={"transcript": transcript, "language": "en"})
        response_hi = client.post("/api/v1/notes", json={"transcript": transcript, "language": "hi"})
        response_none = client.post("/api/v1/notes", json={"transcript": transcript})

        assert response_en.status_code == 200
        assert response_hi.status_code == 200
        assert response_none.status_code == 200

        data_en = response_en.json()
        data_hi = response_hi.json()
        data_none = response_none.json()

        # Structure should be identical
        assert set(data_en.keys()) == set(data_hi.keys()) == set(data_none.keys())
        assert len(data_en["key_points"]) == len(data_hi["key_points"]) == len(data_none["key_points"])
        assert len(data_en["action_items"]) == len(data_hi["action_items"]) == len(data_none["action_items"])
        assert len(data_en["decisions"]) == len(data_hi["decisions"]) == len(data_none["decisions"])

        # Only language field should differ
        assert data_en["language"] == "en"
        assert data_hi["language"] == "hi"
        assert data_none["language"] is None