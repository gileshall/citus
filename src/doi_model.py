from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl


class Institution(BaseModel):
    """Represents an academic institution associated with the research."""
    name: str = Field(..., description="The name of the institution.")


class DateParts(BaseModel):
    """Represents a date composed of year, month, and day."""
    date_parts: Optional[List[List[int]]] = Field(None, description="The parts of the date as year, month, and day.")


class Indexed(BaseModel):
    """Represents the indexing details."""
    date_parts: Optional[List[List[int]]] = Field(None, description="The parts of the indexed date.")
    date_time: Optional[str] = Field(None, description="The date and time when the document was indexed.")
    timestamp: Optional[int] = Field(None, description="The timestamp of the indexing in milliseconds since epoch.")


class Posted(BaseModel):
    """Represents when the document was posted."""
    date_parts: Optional[List[List[int]]] = Field(None, description="The parts of the posted date.")


class Accepted(BaseModel):
    """Represents when the document was accepted."""
    date_parts: Optional[List[List[int]]] = Field(None, description="The parts of the accepted date.")


class Author(BaseModel):
    """Represents an author of the research document."""
    given: str = Field(..., description="The given name of the author.")
    family: str = Field(..., description="The family name of the author.")
    sequence: str = Field(..., description="The sequence of the author (e.g., first, additional).")
    orcid: Optional[str] = Field(None, description="The ORCID identifier for the author (optional).")
    authenticated_orcid: bool = Field(False, description="Indicates whether the ORCID is authenticated.")


class Link(BaseModel):
    """Represents a hyperlink associated with the document."""
    url: Optional[HttpUrl] = Field(None, description="The URL link to the document.")
    content_type: Optional[str] = Field(None, description="The type of content of the link (optional).")
    content_version: Optional[str] = Field(None, description="The version of the content (optional).")
    intended_application: Optional[str] = Field(None, description="The intended application for the link (optional).")


class Resource(BaseModel):
    """Represents the resource information for the document."""
    primary: Optional[Dict[str, HttpUrl]] = Field(None, description="Primary resource URL.")


class Relation(BaseModel):
    """Represents relationships between documents."""
    is_preprint_of: Optional[List[Dict[str, Any]]] = Field(None, description="List of documents that this document is a preprint of.")


class ResearchDocument(BaseModel):
    """Represents a research document with detailed information."""
    institution: Optional[List[Institution]] = Field(None, description="List of institutions associated with the research.")
    indexed: Optional[Indexed] = Field(None, description="Indexing information for the document.")
    posted: Optional[Posted] = Field(None, description="Posting information for the document.")
    group_title: Optional[str] = Field(None, description="The title of the research group.")
    reference_count: int = Field(0, description="Count of references used in the document.")
    publisher: Optional[str] = Field(None, description="The publisher of the document.")
    content_domain: Optional[Dict[str, Any]] = Field(None, description="Content domain information.")
    accepted: Optional[Accepted] = Field(None, description="Acceptance information for the document.")
    abstract: Optional[str] = Field(None, description="Abstract summarising the research.")
    doi: Optional[str] = Field(None, description="Digital Object Identifier for the document.")
    type: Optional[str] = Field(None, description="Type of the document.")
    created: Optional[DateParts] = Field(None, description="Creation information for the document.")
    source: Optional[str] = Field(None, description="Source of the document.")
    is_referenced_by_count: int = Field(0, description="Count of times this document is referenced.")
    title: Optional[Union[str, List[str]]] = Field(None, description="Title of the research document.")
    prefix: Optional[str] = Field(None, description="Prefix for the DOI.")
    author: Optional[List[Author]] = Field(None, description="List of authors of the document.")
    member: Optional[str] = Field(None, description="Member ID.")
    link: Optional[List[Link]] = Field(None, description="List of links associated with the document.")
    deposited: Optional[DateParts] = Field(None, description="Deposit information for the document.")
    score: Optional[float] = Field(None, description="Score assigned to the document.")
    resource: Optional[Resource] = Field(None, description="Resource information associated with the document.")
    url: Optional[HttpUrl] = Field(None, description="URL for accessing the document.")
    relation: Optional[Relation] = Field(None, description="Relationships associated with the document.")
    subject: Optional[List[str]] = Field(None, description="List of subjects related to the document.")
    published: Optional[DateParts] = Field(None, description="Published information for the document.")
    subtype: Optional[str] = Field(None, description="Subtype of the document.")
