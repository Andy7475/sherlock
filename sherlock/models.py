from __future__ import annotations

from __future__ import annotations

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, model_validator
import uuid
from slugify import slugify


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    query: Optional[str] = Field(default=None, description="The query that retrieved this evidence")

class EvidenceCollection(BaseModel):
    evidence: List[Evidence] = Field(default_factory=list)
    
    def __len__(self):
        return len(self.evidence)

class Argument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    supports: bool  # True if supporting, False if opposing
    evidence_collection: EvidenceCollection = Field(default_factory=EvidenceCollection)
    subclaims: List[Claim] = Field(default_factory=list)  # IDs of other claims this argument depends on
    
    @property
    def evidence_score(self) -> int:
        """The weight of evidence supporting this argument"""
        return len(self.evidence_collection)


class Likelihood(BaseModel):
    supporting: int = Field(
        description="The number of supporting pieces of evidence", ge=0, default=0
    )
    opposing: int = Field(
        description="The number of opposing pieces of evidence", ge=0, default=0
    )
    
    @property
    def supporting_percentage(self) -> float:
        """Calculate percentage of support"""
        total = self.supporting + self.opposing
        if total == 0:
            return 0
        return (self.supporting / total) * 100

    @property
    def opposing_percentage(self) -> float:
        """Calculate percentage of opposition"""
        total = self.supporting + self.opposing
        if total == 0:
            return 0
        return (self.opposing / total) * 100


class Claim(BaseModel):
    text: str
    id: str = Field(default_factory=None)  # Will be set in validator
    arguments: List[Argument] = Field(default_factory=list)
    likelihood: Likelihood = Field(default_factory=Likelihood)
    
    @classmethod
    def generate_id(cls, text: str) -> str:
        """Generate a slugified ID from text"""
        return slugify(text)
    
    @model_validator(mode="before")
    @classmethod
    def set_id_from_text(cls, values):
        """Ensure ID is set based on text if not provided"""
        if isinstance(values, dict) and "id" not in values and "text" in values:
            values["id"] = cls.generate_id(values["text"])
        return values
    
    def add_argument(self, argument: Argument) -> str:
        """Add an argument to this claim"""
        self.arguments.append(argument)
        self._update_likelihood()
        return argument.id

    def _update_likelihood(self) -> None:
        """Update likelihood based on simple counting of arguments"""
        supporting = sum([arg.evidence_score for arg in self.arguments if arg.supports])
        opposing = sum([arg.evidence_score for arg in self.arguments if not arg.supports])
        self.likelihood = Likelihood(supporting=supporting, opposing=opposing)


# Q&A Models
class Query(BaseModel):
    """Represents a search query and its results"""
    query_text: str = Field(description="The search query string")
    evidence_found: List[Evidence] = Field(default_factory=list, description="Evidence retrieved by this query")

    def __len__(self):
        return len(self.evidence_found)


class Answer(BaseModel):
    """Represents an answer to a question with supporting evidence"""
    question: str = Field(description="The original question")
    answer_text: str = Field(description="The answer to the question")
    queries: List[Query] = Field(default_factory=list, description="All queries made to gather evidence")
    confidence: str = Field(default="medium", description="Confidence level: low, medium, high")
    iterations_used: int = Field(default=0, description="Number of iterations/turns taken to answer")
    time_seconds: float = Field(default=0.0, description="Total time in seconds to answer the question")

    @property
    def all_evidence(self) -> List[Evidence]:
        """Get all evidence from all queries"""
        evidence = []
        for query in self.queries:
            evidence.extend(query.evidence_found)
        return evidence

    @property
    def total_queries(self) -> int:
        """Total number of queries made"""
        return len(self.queries)

    @property
    def total_evidence(self) -> int:
        """Total number of evidence pieces found"""
        return len(self.all_evidence)