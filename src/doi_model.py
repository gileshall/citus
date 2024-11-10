from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class Institution(BaseModel):
    """Represents an academic institution associated with the research."""
    name: str = Field(..., description="The name of the institution.")


class DateParts(BaseModel):
    """Represents a date composed of year, month, and day."""
    year: int = Field(..., description="The year of the date.")
    month: Optional[int] = Field(None, description="The month of the date (optional).")
    day: Optional[int] = Field(None, description="The day of the date (optional).")


class Indexed(BaseModel):
    """Represents the indexing details."""
    date_parts: List[List[int]] = Field(..., description="The parts of the indexed date.")
    date_time: str = Field(..., description="The date and time when the document was indexed.")
    timestamp: int = Field(..., description="The timestamp of the indexing in milliseconds since epoch.")


class Posted(BaseModel):
    """Represents when the document was posted."""
    date_parts: List[List[int]] = Field(..., description="The parts of the posted date.")


class Accepted(BaseModel):
    """Represents when the document was accepted."""
    date_parts: List[List[int]] = Field(..., description="The parts of the accepted date.")


class Author(BaseModel):
    """Represents an author of the research document."""
    given: str = Field(..., description="The given name of the author.")
    family: str = Field(..., description="The family name of the author.")
    sequence: str = Field(..., description="The sequence of the author (e.g., first, additional).")
    orcid: Optional[str] = Field(None, description="The ORCID identifier for the author (optional).")
    authenticated_orcid: bool = Field(False, description="Indicates whether the ORCID is authenticated.")


class Link(BaseModel):
    """Represents a hyperlink associated with the document."""
    url: HttpUrl = Field(..., description="The URL link to the document.")
    content_type: Optional[str] = Field(None, description="The type of content of the link (optional).")
    content_version: Optional[str] = Field(None, description="The version of the content (optional).")
    intended_application: Optional[str] = Field(None, description="The intended application for the link (optional).")


class Resource(BaseModel):
    """Represents the resource information for the document."""
    primary: Dict[str, HttpUrl] = Field(..., description="Primary resource URL.")


class Relation(BaseModel):
    """Represents relationships between documents."""
    is_preprint_of: List[Dict[str, Any]] = Field(..., description="List of documents that this document is a preprint of.")


class ResearchDocument(BaseModel):
    """Represents a research document with detailed information."""
    institution: List[Institution] = Field(..., description="List of institutions associated with the research.")
    indexed: Indexed = Field(..., description="Indexing information for the document.")
    posted: Posted = Field(..., description="Posting information for the document.")
    group_title: str = Field(..., description="The title of the research group.")
    reference_count: int = Field(0, description="Count of references used in the document.")
    publisher: str = Field(..., description="The publisher of the document.")
    content_domain: Dict[str, Any] = Field(..., description="Content domain information.")
    accepted: Accepted = Field(..., description="Acceptance information for the document.")
    abstract: str = Field(..., description="Abstract summarising the research.")
    doi: str = Field(..., description="Digital Object Identifier for the document.")
    type: str = Field(..., description="Type of the document.")
    created: DateParts = Field(..., description="Creation information for the document.")
    source: str = Field(..., description="Source of the document.")
    is_referenced_by_count: int = Field(0, description="Count of times this document is referenced.")
    title: str = Field(..., description="Title of the research document.")
    prefix: str = Field(..., description="Prefix for the DOI.")
    author: List[Author] = Field(..., description="List of authors of the document.")
    member: str = Field(..., description="Member ID.")
    link: List[Link] = Field(..., description="List of links associated with the document.")
    deposited: DateParts = Field(..., description="Deposit information for the document.")
    score: float = Field(..., description="Score assigned to the document.")
    resource: Resource = Field(..., description="Resource information associated with the document.")
    url: HttpUrl = Field(..., description="URL for accessing the document.")
    relation: Relation = Field(..., description="Relationships associated with the document.")
    subject: List[str] = Field(..., description="List of subjects related to the document.")
    published: DateParts = Field(..., description="Published information for the document.")
    subtype: str = Field(..., description="Subtype of the document.")
