from __future__ import annotations

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str


class Argument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    supports: bool  # True if supporting, False if opposing
    evidence: List[Evidence] = []
    subclaim: List[Claim] = []  # IDs of other claims this argument depends on


class Likelihood(BaseModel):
    supporting: int = Field(
        description="The number of supporting arguments", ge=0, default=0
    )
    opposing: int = Field(
        description="The number of opposing arguments", ge=0, default=0
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    arguments: List[Argument] = []
    likelihood: Likelihood = Field(default_factory=Likelihood)

    def add_argument(self, argument: Argument) -> str:
        """Add an argument to this claim"""
        self.arguments.append(argument)
        self._update_likelihood()
        return argument.id

    def _update_likelihood(self) -> None:
        """Update likelihood based on simple counting of arguments"""
        supporting = len([arg for arg in self.arguments if arg.supports])
        opposing = len([arg for arg in self.arguments if not arg.supports])

        self.likelihood = Likelihood(supporting=supporting, opposing=opposing)
