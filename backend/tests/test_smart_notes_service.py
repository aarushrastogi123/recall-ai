import pytest
from app.models.smart_notes import SmartNotesRequest
from app.services.smart_notes import (
    split_sentences,
    score_sentence,
    extract_summary,
    extract_key_points,
    find_action_items,
    find_decisions,
    group_into_sections,
    generate_smart_notes,
)


class TestSplitSentences:
    def test_basic_split(self):
        text = "Hello world. This is a test. Another sentence."
        sentences = split_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "Hello world."
        assert sentences[1] == "This is a test."
        assert sentences[2] == "Another sentence."

    def test_whitespace_normalization(self):
        text = "  Hello world.   This is a test.  "
        sentences = split_sentences(text)
        assert len(sentences) == 2

    def test_empty_input(self):
        assert split_sentences("") == []
        assert split_sentences("   ") == []

    def test_short_sentences_filtered(self):
        text = "Hi. Hello world. OK. This is a longer sentence here."
        sentences = split_sentences(text)
        # "Hi." and "OK." should be filtered out (< 10 chars)
        assert all(len(s) >= 10 for s in sentences)

    def test_hindi_sentences(self):
        text = "नमस्ते दुनिया। यह एक परीक्षा है। अगला वाक्य।"
        sentences = split_sentences(text)
        assert len(sentences) >= 1


class TestScoreSentence:
    def test_position_bonus(self):
        sentences = ["First sentence here.", "Second sentence here.", "Third sentence here."]
        scores = [score_sentence(s, i, len(sentences)) for i, s in enumerate(sentences)]
        assert scores[0] > scores[2]

    def test_keyword_bonus(self):
        s1 = "The budget was approved."
        s2 = "The weather is nice today."
        score1 = score_sentence(s1, 0, 2)
        score2 = score_sentence(s2, 0, 2)
        assert score1 > score2

    def test_number_bonus(self):
        s1 = "Revenue increased 20% this quarter."
        s2 = "Revenue increased this quarter."
        score1 = score_sentence(s1, 0, 1)
        score2 = score_sentence(s2, 0, 1)
        assert score1 > score2


class TestExtractSummary:
    def test_basic_summary(self):
        sentences = [
            "The team discussed the Q4 budget.",
            "Revenue increased 20% this quarter.",
            "We need to hire more engineers.",
            "The meeting ended at 5pm.",
        ]
        summary = extract_summary(sentences, max_sentences=2)
        assert len(summary) > 0
        assert "budget" in summary.lower() or "revenue" in summary.lower()

    def test_empty_sentences(self):
        assert extract_summary([]) == "No transcript content available."

    def test_single_sentence(self):
        sentences = ["Only one sentence here."]
        summary = extract_summary(sentences)
        assert "Only one sentence here" in summary


class TestExtractKeyPoints:
    def test_key_points_extraction(self):
        sentences = [
            "Revenue increased 20% this quarter.",
            "The team discussed the Q4 budget.",
            "We need to hire more engineers.",
            "Revenue increased 20% this quarter.",  # duplicate
        ]
        key_points = extract_key_points(sentences, max_points=3)
        assert len(key_points) >= 1
        # Deduplication
        texts = [kp.text for kp in key_points]
        assert len(texts) == len(set(texts))

    def test_empty_sentences(self):
        assert extract_key_points([]) == []

    def test_limit_respected(self):
        sentences = [f"Sentence number {i} with enough length." for i in range(20)]
        key_points = extract_key_points(sentences, max_points=5)
        assert len(key_points) <= 5


class TestFindActionItems:
    def test_explicit_action_items(self):
        sentences = [
            "John will send the report by Friday.",
            "We need to review the budget.",
            "Action: Assign task to Alice.",
            "The weather is nice.",
        ]
        items = find_action_items(sentences)
        assert len(items) >= 1
        descs = [item.description.lower() for item in items]
        assert any("report" in d for d in descs) or any("review" in d for d in descs)

    def test_action_item_with_owner_and_deadline(self):
        sentences = ["John will send the report by Friday."]
        items = find_action_items(sentences)
        assert len(items) == 1
        assert items[0].owner == "John"
        assert "Friday" in items[0].deadline

    def test_no_action_items(self):
        sentences = ["The weather is nice today.", "Meeting ended at 5pm."]
        items = find_action_items(sentences)
        assert items == []

    def test_deduplication(self):
        sentences = [
            "John will send the report.",
            "John will send the report.",
        ]
        items = find_action_items(sentences)
        assert len(items) == 1


class TestFindDecisions:
    def test_explicit_decisions(self):
        sentences = [
            "We decided to approve the budget.",
            "The team agreed on the timeline.",
            "The weather is nice.",
        ]
        decisions = find_decisions(sentences)
        assert len(decisions) >= 1
        descs = [d.description.lower() for d in decisions]
        assert any("approve" in d for d in descs) or any("agreed" in d for d in descs)

    def test_suggestions_not_decisions(self):
        sentences = [
            "We should consider the budget.",
            "Maybe we could hire more people.",
        ]
        decisions = find_decisions(sentences)
        assert decisions == []

    def test_deduplication(self):
        sentences = [
            "We decided to approve the budget.",
            "We decided to approve the budget.",
        ]
        decisions = find_decisions(sentences)
        assert len(decisions) == 1


class TestGroupIntoSections:
    def test_sections_for_long_transcript(self):
        sentences = [
            "The budget for Q4 is 500k.",
            "Revenue increased 20% this quarter.",
            "We need to hire more engineers for the project.",
            "The project launch is scheduled for March.",
            "Team capacity is a concern.",
            "Financial forecast looks positive.",
            "Budget allocation for marketing increased.",
        ] * 2  # Make it longer
        sections = group_into_sections(sentences)
        # Should find finance and project sections
        titles = [s.title.lower() for s in sections]
        assert any("finance" in t for t in titles) or any("project" in t for t in titles)

    def test_no_sections_for_short_transcript(self):
        sentences = ["Short meeting.", "Only two sentences."]
        sections = group_into_sections(sentences)
        assert sections == []


class TestGenerateSmartNotes:
    def test_realistic_meeting_transcript(self):
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
        request = SmartNotesRequest(transcript=transcript, language="en")
        response = generate_smart_notes(request)

        assert response.summary
        assert len(response.key_points) > 0
        assert len(response.action_items) >= 1
        assert len(response.decisions) >= 1
        assert response.language == "en"

        # Check action item extraction
        action_descs = [a.description.lower() for a in response.action_items]
        assert any("report" in d for d in action_descs) or any("documentation" in d for d in action_descs)

    def test_no_action_items_or_decisions(self):
        transcript = "The weather today is sunny. The team had a casual chat about weekend plans."
        request = SmartNotesRequest(transcript=transcript, language="en")
        response = generate_smart_notes(request)

        assert response.summary
        assert response.action_items == []
        assert response.decisions == []

    def test_hindi_transcript_no_crash(self):
        transcript = """
        नमस्ते टीम, आज की मीटिंग में हमने बजट पर चर्चा की।
        राजस्व इस तिमाही में 20% बढ़ा है।
        जॉन शुक्रवार तक रिपोर्ट भेजेगा।
        हमने बजट को मंजूरी दे दी है।
        """
        request = SmartNotesRequest(transcript=transcript, language="hi")
        response = generate_smart_notes(request)

        assert response.summary
        assert response.language == "hi"
        # Should not crash, should produce some output
        assert len(response.key_points) >= 0

    def test_duplicate_and_blank_lines(self):
        transcript = """
        We discussed the budget.

        We discussed the budget.
        Revenue increased 20%.
        Revenue increased 20%.
        """
        request = SmartNotesRequest(transcript=transcript, language="en")
        response = generate_smart_notes(request)

        # Deduplication should work
        key_point_texts = [kp.text for kp in response.key_points]
        assert len(key_point_texts) == len(set(key_point_texts))

    def test_long_transcript_limits(self):
        # Generate a long transcript
        sentences = [f"Sentence {i} with some important keyword budget revenue project." for i in range(100)]
        transcript = " ".join(sentences)
        request = SmartNotesRequest(transcript=transcript, language="en")
        response = generate_smart_notes(request)

        assert len(response.key_points) <= 10
        assert len(response.action_items) <= 10
        assert len(response.decisions) <= 10
        assert len(response.sections) <= 5

    def test_empty_input_handled_by_request_model(self):
        # The request model validation handles this, but ensure service doesn't crash
        request = SmartNotesRequest(transcript="Valid transcript with enough content here.")
        response = generate_smart_notes(request)
        assert response.summary