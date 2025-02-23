from __future__ import annotations

import logging
import os
from typing import List, Optional

from anthropic import Anthropic
from sherlock.models import Argument, Claim, Evidence
from pydantic import BaseModel, Field
from sherlock.logger_config import get_logger

logger = get_logger(__name__)


class QueryInput(BaseModel):
    query: str = Field(
        description="Keywords or phrases to search for in the evidence database. The search uses vector similarity to find relevant matches. Boolean operators (AND, OR, NOT) are not supported."
    )


def query_evidence(store, query: str) -> List[Evidence]:
    """Tool implementation that queries the evidence store"""
    results = store.query(query)
    return [Evidence(id=result["id"], text=result["text"]) for result in results]


# Tool definition using pydantic schema
evidence_query_tool = {
    "name": "query_evidence",
    "description": "Search for evidence using vector similarity matching. Takes keywords/phrases and returns relevant evidence. This is a semantic search - it finds similar meanings, not exact matches. Boolean operators are not supported.",
    "input_schema": QueryInput.model_json_schema(),
}


class ArgumentInput(BaseModel):
    text: str = Field(description="The main text of the argument being made")
    supports: bool = Field(
        description="Whether this argument supports (True) or opposes (False) the claim"
    )
    evidence: List[Evidence] = Field(
        default=[], description="List of evidence to support this argument"
    )
    subclaims: List[str] = Field(
        default=[],
        description="List of claim texts - these will be slugified to create/link claims",
    )


def create_argument(
    text: str, supports: bool, evidence: List[Evidence] = [], subclaims: List[str] = []
) -> Argument:
    """Tool implementation that creates an Argument object"""
    # Create subclaim objects - IDs will be auto-generated from text
    subclaim_objects = [Claim(text=claim_text) for claim_text in subclaims]

    # Create argument
    argument = Argument(
        text=text, supports=supports, evidence=evidence, subclaim=subclaim_objects
    )

    return argument


# Tool definition using pydantic schema
create_argument_tool = {
    "name": "create_argument",
    "description": "Create an argument with supporting evidence and subclaims. The argument can either support or oppose a main claim. Subclaims are provided as text and will be automatically converted to slugified IDs.",
    "input_schema": ArgumentInput.model_json_schema(),
}


SYSTEM_PROMPT = """You are a ClaimSupport agent that evaluates claims by finding supporting evidence. Your goal is to form well-reasoned arguments that strengthen the claim.

Process:
1. Analyse the given claim to identify key concepts for finding supporting evidence
2. Search for relevant evidence using the query_evidence tool
3. Evaluate each piece of evidence - only keep evidence that supports the claim
4. Once you have 2-3 pieces of supporting evidence, form an argument

Guidelines:
- Focus ONLY on evidence that supports the claim
- Aim for 2-3 pieces of supporting evidence
- If no supporting evidence is found after 3 searches, stop and report this

Always think step-by-step and explain your reasoning."""


class ClaimSupportAgent:
    def __init__(self, evidence_store):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.evidence_store = evidence_store
        self.tools = {
            "query_evidence": self.query_evidence,
            "create_argument": self.create_argument,
        }

    def query_evidence(self, query: str) -> List[Evidence]:
        """Query evidence store for supporting evidence"""
        logger.info(f"Querying evidence store with: {query}")
        results = self.evidence_store.query(query)
        evidence = [
            Evidence(id=result["id"], text=result["text"]) for result in results
        ]
        logger.info(f"Found {len(evidence)} pieces of evidence")
        return evidence

    def create_argument(
        self,
        text: str,
        supports: bool = True,
        evidence: List[Evidence] = [],
        subclaims: List[str] = [],
    ) -> Argument:
        """Create a supporting argument with evidence"""
        logger.info(f"Creating argument: {text}")
        logger.info(
            f"With {len(evidence)} pieces of evidence and {len(subclaims)} subclaims"
        )
        return Argument(
            text=text,
            supports=True,  # Always True for support agent
            evidence=evidence,
            subclaim=[Claim(text=claim_text) for claim_text in subclaims],
        )

    def evaluate_claim(self, claim: Claim) -> Claim:
        """Main method to evaluate a claim and find supporting evidence"""
        logger.info(f"Starting evaluation of claim: {claim.text}")

        messages = [
            {
                "role": "user",
                "content": f"Evaluate this claim <claim>{claim.text}</claim>. Use the tools to find supporting evidence and create an argument.",
            },
        ]

        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}")

            response = self.client.messages.create(
                model="claude-3-opus-latest",
                system=SYSTEM_PROMPT,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                tools=[create_argument_tool, evidence_query_tool],
            )

            # Process tool calls if any
            if response.stop_reason == "tool_use":
                tool_name = response.content[0].name
                tool_inputs = response.content[0].input

                result = self.tools[tool_name](**tool_inputs)

                # Add tool result to messages
                messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    }
                )

            # Check if we have a final argument
            if "create_argument" in [tc.name for tc in response.tool_calls or []]:
                logger.info("Argument created, adding to claim")
                # Get the last created argument
                for tc in reversed(response.tool_calls):
                    if tc.name == "create_argument":
                        final_argument = self.tools[tc.name](**tc.parameters)
                        claim.add_argument(final_argument)
                        logger.info("Evaluation complete")
                        return claim

            # Add assistant's response to messages
            messages.append({"role": "assistant", "content": response.content})

        logger.warning("Max iterations reached without creating argument")
        return claim
