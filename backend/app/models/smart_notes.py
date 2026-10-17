from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SmartNotesRequest(BaseModel):
    """Request model for generating smart notes from transcript text."""
    transcript: str = Field(..., description="Full transcript text from transcription")
    language: Optional[str] = Field(None, description="Optional language code (e.g., 'en', 'es')")

    @field_validator("transcript")
    @classmethod
    def transcript_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Transcript must not be empty or whitespace only")
        return v.strip()


class ActionItem(BaseModel):
    """An action item extracted from the transcript."""
    description: str = Field(..., description="What needs to be done")
    owner: Optional[str] = Field(None, description="Person responsible, if explicitly mentioned")
    deadline: Optional[str] = Field(None, description="Due date or timeframe, if explicitly mentioned")


class Decision(BaseModel):
    """A decision identified in the transcript."""
    description: str = Field(..., description="What was decided")
    context: Optional[str] = Field(None, description="Supporting context or rationale")


class KeyPoint(BaseModel):
    """A key point or takeaway from the transcript."""
    text: str = Field(..., description="The key point")


class Section(BaseModel):
    """A topic-based section grouping related content."""
    title: str = Field(..., description="Section heading")
    summary: str = Field(..., description="Concise summary of this section")
    key_points: list[KeyPoint] = Field(default_factory=list, description="Key points in this section")
    action_items: list[ActionItem] = Field(default_factory=list, description="Action items in this section")
    decisions: list[Decision] = Field(default_factory=list, description="Decisions in this section")


class SmartNotesResponse(BaseModel):
    """Complete structured smart notes response."""
    summary: str = Field(..., description="Overall concise summary")
    key_points: list[KeyPoint] = Field(default_factory=list, description="Global key points")
    action_items: list[ActionItem] = Field(default_factory=list, description="Global action items")
    decisions: list[Decision] = Field(default_factory=list, description="Global decisions")
    sections: list[Section] = Field(default_factory=list, description="Topic-based sections")
    language: Optional[str] = Field(None, description="Language of the notes")