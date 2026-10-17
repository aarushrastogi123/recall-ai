import logging
import re
from typing import Optional

from app.models.smart_notes import (
    SmartNotesRequest,
    SmartNotesResponse,
    ActionItem,
    Decision,
    KeyPoint,
    Section,
)

logger = logging.getLogger(__name__)

# Configuration constants
MAX_SUMMARY_SENTENCES = 3
MAX_KEY_POINTS = 10
MAX_ACTION_ITEMS = 10
MAX_DECISIONS = 10
MAX_SECTIONS = 5
MIN_SENTENCE_LENGTH = 10

# Keywords that indicate importance
IMPORTANCE_KEYWORDS = {
    "decision", "decide", "agreed", "approved", "rejected", "approved",
    "action", "todo", "task", "will", "must", "need to", "should",
    "deadline", "due", "owner", "responsible", "assign",
    "budget", "revenue", "cost", "profit", "loss",
    "meeting", "project", "launch", "release", "milestone",
    "issue", "problem", "risk", "blocker", "challenge",
    "agenda", "discuss", "review", "update", "status",
    "quarter", "q1", "q2", "q3", "q4", "year", "month", "week",
    "client", "customer", "user", "team", "manager", "lead",
}

# Patterns for action items
ACTION_PATTERNS = [
    r"\b(?:will|must|need to|should|have to|going to)\s+(\w+\s+){0,5}\w+",
    r"\b(?:action|todo|task):\s*([^.]+)",
    r"\b(?:assign|assigned)\s+(?:to\s+)?(\w+(?:\s+\w+){0,2})\s+(?:to\s+)?([^.]+)",
    r"\b(?:by|before)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|\w+\s+\d{1,2}|\d{1,2}/\d{1,2})",
]

# Patterns for decisions
DECISION_PATTERNS = [
    r"\b(?:decided|agreed|approved|rejected|confirmed|resolved)\s+(?:that\s+)?([^.]+)",
    r"\b(?:decision|conclusion):\s*([^.]+)",
    r"\b(?:we\s+(?:agree|decide|approve|reject))\s+([^.]+)",
]

# Patterns for owners
OWNER_PATTERNS = [
    r"\b(?:owner|responsible|assigned to|lead by)\s*:?\s*(\w+(?:\s+\w+){0,2})",
    r"^(\w+(?:\s+\w+){0,2})\s+will\s+",  # "John will send..."
]

# Patterns for deadlines
DEADLINE_PATTERNS = [
    r"\b(?:by|before|due)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|\w+\s+\d{1,2}|\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2})",
    r"\b(?:deadline|due date)\s*:?\s*([^.\n]+)",
]

# Topic keywords for section grouping
TOPIC_KEYWORDS = {
    "finance": ["budget", "revenue", "cost", "profit", "loss", "financial", "money", "funding", "investment", "expense"],
    "project": ["project", "milestone", "launch", "release", "timeline", "deliverable", "sprint", "roadmap"],
    "team": ["team", "hiring", "staff", "resource", "capacity", "workload", "onboard", "employee"],
    "product": ["feature", "product", "user", "customer", "client", "feedback", "requirement", "spec", "design"],
    "operations": ["process", "workflow", "automation", "tool", "system", "infrastructure", "deployment", "devops"],
    "strategy": ["strategy", "goal", "objective", "vision", "mission", "quarter", "annual", "planning", "okr"],
    "meeting": ["meeting", "agenda", "follow up", "next step", "action item", "decision", "discussion"],
}

# Patterns to split sentences (handles English and basic non-English)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+(?=[A-Z\u0900-\u097F])")
SENTENCE_SPLIT_FALLBACK = re.compile(r"[.!?।]")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, handling basic punctuation."""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []

    # Try sentence split
    sentences = SENTENCE_SPLIT.split(text)

    # Fallback: simple split on punctuation
    if len(sentences) <= 1:
        parts = SENTENCE_SPLIT_FALLBACK.split(text)
        sentences = [p.strip() for p in parts if p.strip()]

    # Clean and filter
    cleaned = []
    for s in sentences:
        s = s.strip()
        if len(s) >= MIN_SENTENCE_LENGTH:
            cleaned.append(s)

    return cleaned


def score_sentence(sentence: str, position: int, total: int) -> float:
    """Score sentence importance based on position, length, and keywords."""
    score = 0.0
    words = sentence.lower().split()

    # Position bonus (early sentences often more important)
    if total > 0:
        position_score = 1.0 - (position / total) * 0.5
        score += position_score * 2.0

    # Length bonus (moderate length sentences preferred)
    length = len(words)
    if 8 <= length <= 30:
        score += 1.5
    elif 5 <= length <= 40:
        score += 1.0

    # Keyword bonus
    for keyword in IMPORTANCE_KEYWORDS:
        if keyword in sentence.lower():
            score += 2.0

    # Number/name bonus (numbers, capitalized words)
    if re.search(r"\b\d+(\.\d+)?%?\b", sentence):
        score += 1.0
    if re.search(r"\b[A-Z][a-z]+\b", sentence):
        score += 0.5

    return score


def extract_summary(sentences: list[str], max_sentences: int = MAX_SUMMARY_SENTENCES) -> str:
    """Extract top sentences for summary."""
    if not sentences:
        return "No transcript content available."

    scored = [(score_sentence(s, i, len(sentences)), s) for i, s in enumerate(sentences)]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:max_sentences]]

    # Sort by original order for readability
    top_set = set(top)
    ordered = [s for s in sentences if s in top_set]

    return " ".join(ordered) if ordered else sentences[0]


def extract_key_points(sentences: list[str], max_points: int = MAX_KEY_POINTS) -> list[KeyPoint]:
    """Extract key points from sentences."""
    if not sentences:
        return []

    scored = [(score_sentence(s, i, len(sentences)), s) for i, s in enumerate(sentences)]
    scored.sort(key=lambda x: x[0], reverse=True)

    seen = set()
    key_points = []
    for _, s in scored:
        # Deduplicate by normalized text
        norm = re.sub(r"\s+", " ", s.lower()).strip()
        if norm not in seen and len(s) >= MIN_SENTENCE_LENGTH:
            seen.add(norm)
            key_points.append(KeyPoint(text=s))
            if len(key_points) >= max_points:
                break

    return key_points


def find_action_items(sentences: list[str]) -> list[ActionItem]:
    """Extract action items from sentences."""
    action_items = []
    seen = set()

    for sentence in sentences:
        lower = sentence.lower()

        # Check for action keywords
        if not any(kw in lower for kw in ["will", "must", "need to", "should", "action", "todo", "task", "assign"]):
            continue

        # Try to extract description
        description = sentence.strip()
        if len(description) < MIN_SENTENCE_LENGTH:
            continue

        norm = re.sub(r"\s+", " ", description.lower()).strip()
        if norm in seen:
            continue
        seen.add(norm)

        # Extract owner
        owner = None
        for pattern in OWNER_PATTERNS:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                owner = match.group(1).strip().title()
                break

        # Extract deadline
        deadline = None
        for pattern in DEADLINE_PATTERNS:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                deadline = match.group(1).strip()
                break

        action_items.append(ActionItem(
            description=description,
            owner=owner,
            deadline=deadline,
        ))

        if len(action_items) >= MAX_ACTION_ITEMS:
            break

    return action_items


def find_decisions(sentences: list[str]) -> list[Decision]:
    """Extract decisions from sentences."""
    decisions = []
    seen = set()

    for sentence in sentences:
        lower = sentence.lower()

        # Check for decision keywords
        if not any(kw in lower for kw in ["decided", "agreed", "approved", "rejected", "confirmed", "resolved", "decision"]):
            continue

        description = sentence.strip()
        if len(description) < MIN_SENTENCE_LENGTH:
            continue

        norm = re.sub(r"\s+", " ", description.lower()).strip()
        if norm in seen:
            continue
        seen.add(norm)

        # Try to extract context (previous sentence if relevant)
        context = None

        decisions.append(Decision(
            description=description,
            context=context,
        ))

        if len(decisions) >= MAX_DECISIONS:
            break

    return decisions


def group_into_sections(sentences: list[str]) -> list[Section]:
    """Group sentences into topic-based sections."""
    if len(sentences) < 5:
        return []

    # Score each sentence for each topic
    topic_scores = {topic: [] for topic in TOPIC_KEYWORDS}
    for i, sentence in enumerate(sentences):
        lower = sentence.lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score > 0:
                topic_scores[topic].append((score, i, sentence))

    # Build sections for topics with enough content
    sections = []
    for topic, scored in topic_scores.items():
        if len(scored) < 2:
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, _, s in scored[:3]]

        section = Section(
            title=topic.title(),
            summary=" ".join(top_sentences[:2]),
            key_points=[KeyPoint(text=s) for s in top_sentences[:3]],
            action_items=[a for s in top_sentences for a in find_action_items([s])],
            decisions=[d for s in top_sentences for d in find_decisions([s])],
        )
        sections.append(section)

        if len(sections) >= MAX_SECTIONS:
            break

    return sections


def generate_smart_notes(request: SmartNotesRequest) -> SmartNotesResponse:
    """Main entry point to generate smart notes from transcript."""
    transcript = request.transcript
    language = request.language

    sentences = split_sentences(transcript)

    # Summary
    summary = extract_summary(sentences)

    # Key points
    key_points = extract_key_points(sentences)

    # Action items
    action_items = find_action_items(sentences)

    # Decisions
    decisions = find_decisions(sentences)

    # Sections (only for longer transcripts)
    sections = group_into_sections(sentences) if len(sentences) > 10 else []

    logger.info(
        f"Generated smart notes: {len(key_points)} key points, "
        f"{len(action_items)} action items, {len(decisions)} decisions, "
        f"{len(sections)} sections, language={language}"
    )

    return SmartNotesResponse(
        summary=summary,
        key_points=key_points,
        action_items=action_items,
        decisions=decisions,
        sections=sections,
        language=language,
    )