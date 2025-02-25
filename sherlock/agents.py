from __future__ import annotations

import logging
import os
from typing import List, Optional
import json
from anthropic import Anthropic
from sherlock.models import Argument, Claim, Evidence, EvidenceCollection
from pydantic import BaseModel, Field
from sherlock.logger_config import get_logger

logger = get_logger(__name__)


class QueryInput(BaseModel):
    query: str = Field(
        description="Keywords or phrases to search for in the evidence database. The search uses vector similarity to find relevant matches. Boolean operators (AND, OR, NOT) are not supported."
    )

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
    evidence_collection: EvidenceCollection = Field(
        default_factory=EvidenceCollection, 
        description="Evidence collection to support this argument"
    )
    subclaims: List[str] = Field(
        default_factory=list,
        description="List of claim texts - these will be slugified to create/link claims",
    )

# Tool definition using pydantic schema
create_argument_tool = {
    "name": "create_argument",
    "description": "Create an argument with supporting evidence and subclaims. The argument can either support or oppose a main claim. Subclaims are provided as text and will be automatically converted to slugified IDs.",
    "input_schema": ArgumentInput.model_json_schema(),
}


class ClaimInvestgiationAgent:
    def __init__(self, evidence_store, supports=True):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.evidence_store = evidence_store
        self.supports = supports
        self.tools = {
            "query_evidence": self.query_evidence,
            "create_argument": self.create_argument,
        }

    def query_evidence(self, query: str) -> EvidenceCollection:
        """Query evidence store for supporting evidence"""
        logger.info(f"Querying evidence store with: {query}")
        
        results = self.evidence_store.query(query)
        evidence_collection = EvidenceCollection(evidence=[Evidence(id=result["id"], text=result["text"]) for result in results])
        return evidence_collection

    def create_argument(
    self,
    text: str,
    evidence_collection: EvidenceCollection,
    supports:bool,
    subclaims: List[str] = [],
) -> Argument:
        """Create an argument with evidence"""
        logger.info(f"Creating {'supporting' if supports else 'opposing'} argument: {text}")
        logger.info(
            f"With {len(evidence_collection)} pieces of evidence and {len(subclaims)} subclaims"
        )
        
        return Argument(
            text=text,
            supports=supports,
            evidence_collection=evidence_collection,
            subclaims=[Claim(text=claim_text) for claim_text in subclaims],
        )

    def evaluate_claim(self, claim: Claim) -> Claim:
        """Main method to evaluate a claim and find supporting evidence"""
        support_type = "supporting" if self.supports else "opposing"
        logger.info(f"Starting evaluation of claim for {support_type} evidence: {claim.text}")

        messages = [
            {
                "role": "user",
                "content": f"Evaluate this claim <claim>{claim.text}</claim>. Use the tools to find {support_type} evidence and create an argument.",
            },
        ]
        
        # Use the dynamic system prompt
        system_prompt = self._get_system_prompt()

        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}")

            response = self.client.messages.create(
                model="claude-3-opus-latest",
                system=system_prompt,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                tools=[create_argument_tool, evidence_query_tool],
            )

            # Process tool calls if any
            if response.stop_reason == "tool_use":
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                    }
                )
                logger.info(f"Tool_use stop reason. Response.content: {response.content}")

                tool_use_request = response.content[-1]
                tool_name = tool_use_request.name
                tool_inputs = tool_use_request.input
                tool_use_id = tool_use_request.id

                result = self.tools[tool_name](**tool_inputs)
                logger.info(f"result from tool {tool_name}: {str(result)[:15]}, type is: {type(result)}")

                tool_response = {
                "role": "user",
                "content": [
                    {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result.model_dump_json()
                    }
                ]
                }
                
                messages.append(tool_response)

                if tool_name == "create_argument": #creating argumnet so no need for further calls yet
                    claim.add_argument(result)
                    logger.info(f"create_argument called, evaluation complete: {result}")
                    return claim
                
                
                logger.info(messages)

        logger.warning("Max iterations reached without creating argument")
        return claim
    
    def _get_system_prompt(self):
        support_type = "supporting" if self.supports else "opposing"
        evidence_focus = "supports" if self.supports else "opposes"
        
        return f"""You are a Claim {support_type.capitalize()} agent that evaluates claims by finding {support_type} evidence. Your goal is to form well-reasoned arguments that {'strengthen' if self.supports else 'challenge'} the claim.

    Process:
    1. Analyse the given claim to identify key concepts for finding {support_type} evidence
    2. Search for relevant evidence using the query_evidence tool
    3. Evaluate each piece of evidence - only keep evidence that {evidence_focus} the claim
    4. Once you have 2-3 pieces of {support_type} evidence, form an argument
    5. If you find insuffient evidence you can critique or contest the evidence that is there and submit an argument with no evidence, or weak evidence.

    Guidelines:
    - Focus ONLY on evidence that {evidence_focus} the claim
    - Aim for 2-3 pieces of {support_type} evidence
    - If no {support_type} evidence is found after 3 searches, submit a weak argument with no evidence

    Always think step-by-step and explain your reasoning."""
