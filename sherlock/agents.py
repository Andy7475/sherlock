from __future__ import annotations

import logging
import os
from time import sleep, time
from typing import List, Optional
import json
from anthropic import Anthropic, RateLimitError
from sherlock.models import Argument, Claim, Evidence, EvidenceCollection, Query, Answer
from pydantic import BaseModel, Field
from sherlock.logger_config import get_logger

logger = get_logger(__name__)


class QueryInput(BaseModel):
    query: str = Field(
        description="Query for emails in the evidence database. Full Gmail search syntax is supported like after:(dates) from:(sender) and full boolean. It defaults to AND so use few keywords or use OR explicitly."
    )

# Tool definition using pydantic schema
evidence_query_tool = {
    "name": "query_evidence",
    "description": "Search for evidence using vector similarity matching. Takes keywords/phrases and returns relevant evidence. This is a semantic search - it finds similar meanings, not exact matches. Boolean operators are not supported.",
    "input_schema": QueryInput.model_json_schema(),
}
# only use gmail or vector similarity matching, not both
gmail_evidence_query_tool = {
    "name": "query_evidence",
    "description": "Search Gmail messages for evidence using gmail search syntax like from:(senders), after:(dates)  and boolean support OR AND NOT etc. By default searches are AND so use few keywords initially or explicitly use OR. ",
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


class ClaimInvestigationAgent:
    def __init__(self, evidence_store, supports=True, max_iterations=5, max_retries=3):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.evidence_store = evidence_store
        self.supports = supports
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.tools = {
            "query_evidence": self.query_evidence,
            "create_argument": self.create_argument,
        }

    def _call_claude_with_retry(self, **kwargs):
        """Call Claude API with retry logic for rate limit errors"""
        for attempt in range(self.max_retries):
            try:
                return self.client.messages.create(**kwargs)
            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 10 * (attempt + 1)  # 10s, 20s, 30s
                    logger.warning(f"⏸️  Rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    sleep(wait_time)
                else:
                    logger.error(f"❌ Rate limit error after {self.max_retries} attempts: {e}")
                    raise

    def query_evidence(self, query: str) -> EvidenceCollection:
        """Query evidence store for supporting evidence"""
        logger.info(f"Querying evidence store with: {query}")

        results = self.evidence_store.query(query)
        evidence_collection = EvidenceCollection(evidence=[Evidence(id=result["id"], text=result["text"], query=query) for result in results])
        return evidence_collection

    def create_argument(
    self,
    text: str,
    supports:bool,
    evidence_collection: EvidenceCollection = EvidenceCollection(),
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

        max_iterations = self.max_iterations  # Prevent infinite loops
        iteration = 0
        logger.info(f"Max iterations set to: {max_iterations}")

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}/{max_iterations}")

            # Force create_argument tool on last iteration if not used yet
            is_last_iteration = iteration == max_iterations
            tool_choice_param = {"type": "tool", "name": "create_argument"} if is_last_iteration else {"type": "any"}

            if is_last_iteration:
                logger.info("⚠️  LAST ITERATION - Forcing create_argument tool")

            response = self._call_claude_with_retry(
                model="claude-sonnet-4-5-20250929",
                system=system_prompt,
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
                tools=[create_argument_tool, gmail_evidence_query_tool], # replace with evidence_query_tool if you want to use vector similarity matching
                tool_choice=tool_choice_param
            )
            sleep(1)  # To avoid rate limiting

            # Log any thinking/text content from the LLM
            for content_block in response.content:
                if content_block.type == "text":
                    logger.info(f"LLM thinking (iteration {iteration}): {content_block.text}")

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
    5. If you find insuffient evidence, you can instead critique any evidence that strengthens the opposite side of the debate

    Guidelines:
    - Focus ONLY on evidence that {evidence_focus} the claim
    - Aim for 2-3 pieces of {support_type} evidence
    - If no {support_type} evidence is found after 3 searches, submit a {support_type} argument with no evidence.
    - Use your general knowledge to add context or plausible explanations

    Always think step-by-step and explain your reasoning."""


# Q&A Agent Tool Definitions
class AnswerInput(BaseModel):
    answer_text: str = Field(
        description="The detailed answer to the question with specific information like dates, names, locations, numbers etc. extracted from the evidence"
    )
    confidence: str = Field(
        description="Confidence level in the answer: 'low' (little/no evidence), 'medium' (some evidence), 'high' (strong evidence)",
        pattern="^(low|medium|high)$"
    )

provide_answer_tool = {
    "name": "provide_answer",
    "description": "Provide the final detailed answer to the question. Extract and include specific details from evidence like dates, times, locations, names, flight numbers, booking references, etc. Make the answer as informative as possible.",
    "input_schema": AnswerInput.model_json_schema(),
}


class StoreEvidenceInput(BaseModel):
    evidence_ids: List[str] = Field(
        description="List of evidence IDs that are relevant to answering the question. Only include evidence that directly helps answer the question."
    )

store_evidence_tool = {
    "name": "store_relevant_evidence",
    "description": "Store only the evidence pieces that are relevant to answering the question. Use this to filter out irrelevant results before making more queries.",
    "input_schema": StoreEvidenceInput.model_json_schema(),
}


class QuestionAnsweringAgent:
    """Agent that answers questions by gathering evidence through iterative queries"""

    def __init__(self, evidence_store, max_iterations=5, max_retries=3):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.evidence_store = evidence_store
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.queries: List[Query] = []
        self.last_query_results: List[Evidence] = []  # Store last query results for filtering
        self.last_query_text: str = ""  # Store last query text

    def _call_claude_with_retry(self, **kwargs):
        """Call Claude API with retry logic for rate limit errors"""
        for attempt in range(self.max_retries):
            try:
                return self.client.messages.create(**kwargs)
            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 20 * (attempt + 1)  # 10s, 20s, 30s
                    logger.warning(f"⏸️  Rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                    sleep(wait_time)
                else:
                    logger.error(f"❌ Rate limit error after {self.max_retries} attempts: {e}")
                    raise

    def query_evidence(self, query: str) -> EvidenceCollection:
        """Query evidence store - results are not tracked until filtered"""
        logger.info(f"🔍 Querying evidence store with: {query}")

        results = self.evidence_store.query(query)
        evidence_list = [Evidence(id=result["id"], text=result["text"], query=query) for result in results]
        evidence_collection = EvidenceCollection(evidence=evidence_list)

        # Store for filtering (don't track in queries yet)
        self.last_query_results = evidence_list
        self.last_query_text = query

        logger.info(f"📊 Found {len(evidence_list)} pieces of evidence (awaiting filtering)")
        return evidence_collection

    def store_relevant_evidence(self, evidence_ids: List[str]) -> str:
        """Store only relevant evidence from the last query"""
        if not self.last_query_results:
            logger.warning("⚠️  No query results to filter")
            return "No recent query results to filter"

        # Filter to only relevant evidence
        relevant_evidence = [e for e in self.last_query_results if e.id in evidence_ids]

        if not relevant_evidence:
            logger.info("📭 No relevant evidence found in this query")
            self.last_query_results = []
            return "No relevant evidence was found in the last query results"

        # Create query entry with filtered results
        query_obj = Query(
            query_text=self.last_query_text,
            evidence_found=relevant_evidence
        )
        self.queries.append(query_obj)

        logger.info(f"✂️  Stored {len(relevant_evidence)} relevant pieces (filtered from {len(self.last_query_results)})")

        self.last_query_results = []  # Clear after filtering
        return f"Stored {len(relevant_evidence)} relevant evidence pieces"

    def provide_answer(self, answer_text: str, confidence: str) -> Answer:
        """Create the final answer object"""
        logger.info(f"✅ Providing answer with {confidence} confidence")
        logger.info(f"💬 Answer: {answer_text[:100]}...")
        return Answer(
            question="",  # Will be set by answer_question
            answer_text=answer_text,
            queries=self.queries,
            confidence=confidence
        )

    def answer_question(self, question: str) -> Answer:
        """Main method to answer a question by gathering evidence"""
        start_time = time()
        logger.info(f"❓ Starting to answer question: {question}")

        # Reset state for this question
        self.queries = []
        self.last_query_results = []

        messages = [
            {
                "role": "user",
                "content": f"Answer this question: <question>{question}</question>\n\nUse the query_evidence tool to search for relevant information, then provide your answer using the provide_answer tool.",
            },
        ]

        system_prompt = self._get_system_prompt()

        iteration = 0
        logger.info(f"Max iterations set to: {self.max_iterations}")

        tools = {
            "query_evidence": self.query_evidence,
            "store_relevant_evidence": self.store_relevant_evidence,
            "provide_answer": self.provide_answer,
        }

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Starting iteration {iteration}/{self.max_iterations}")

            # Force provide_answer tool on last iteration if not used yet
            is_last_iteration = iteration == self.max_iterations
            tool_choice_param = {"type": "tool", "name": "provide_answer"} if is_last_iteration else {"type": "any"}

            if is_last_iteration:
                logger.info("⚠️  LAST ITERATION - Forcing provide_answer tool")

            response = self._call_claude_with_retry(
                model="claude-sonnet-4-5-20250929",
                system=system_prompt,
                messages=messages,
                temperature=0.2,
                max_tokens=1500,
                tools=[gmail_evidence_query_tool, store_evidence_tool, provide_answer_tool],
                tool_choice=tool_choice_param
            )
            sleep(1)  # To avoid rate limiting

            # Log any thinking/text content from the LLM
            for content_block in response.content:
                if content_block.type == "text":
                    logger.info(f"💭 LLM thinking (iteration {iteration}): {content_block.text}")

            # Process tool calls if any
            if response.stop_reason == "tool_use":
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                    }
                )

                tool_use_request = response.content[-1]
                tool_name = tool_use_request.name
                tool_inputs = tool_use_request.input
                tool_use_id = tool_use_request.id

                logger.info(f"🔧 Tool called: {tool_name}")

                result = tools[tool_name](**tool_inputs)

                if tool_name == "provide_answer":
                    # Set the question and metadata
                    result.question = question
                    result.iterations_used = iteration
                    result.time_seconds = round(time() - start_time, 2)

                    logger.info("✨ Question answering complete!")
                    logger.info(f"📈 Total queries made: {len(self.queries)}")
                    logger.info(f"📚 Total evidence found: {result.total_evidence}")
                    logger.info(f"🔄 Iterations used: {result.iterations_used}")
                    logger.info(f"⏱️  Time taken: {result.time_seconds}s")
                    return result

                # For other tools, continue the loop
                # Handle different result types
                if isinstance(result, str):
                    # store_relevant_evidence returns a string
                    tool_content = result
                else:
                    # query_evidence returns EvidenceCollection
                    tool_content = result.model_dump_json()

                tool_response = {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": tool_content
                        }
                    ]
                }

                messages.append(tool_response)

        # If we reach here, max iterations reached without providing answer
        logger.warning("⚠️  Max iterations reached without providing answer")

        # Force create an answer with what we have
        answer_text = "Unable to provide a conclusive answer based on available evidence."
        if self.queries and any(len(q) > 0 for q in self.queries):
            answer_text = "Based on the limited evidence available, I cannot provide a definitive answer. Please review the evidence gathered."

        elapsed_time = round(time() - start_time, 2)
        logger.info(f"⏱️  Total time: {elapsed_time}s")

        return Answer(
            question=question,
            answer_text=answer_text,
            queries=self.queries,
            confidence="low",
            iterations_used=self.max_iterations,
            time_seconds=elapsed_time
        )

    def _get_system_prompt(self):
        return """You are a Question Answering agent that helps users find information by searching through evidence.

Process:
1. Analyze the question to identify key search terms and concepts
2. Use the query_evidence tool to search for relevant information
   - Start with broad searches, then refine based on what you find
   - Try different search strategies (keywords, dates, people, etc.)
   - For Gmail: use search syntax like from:, after:, subject:, etc.
3. After each query, use store_relevant_evidence to save ONLY the evidence pieces that help answer the question
   - Review each piece of evidence and select only relevant ones
   - This keeps the evidence collection focused and manageable
4. Continue searching until you have enough evidence to answer
5. Use provide_answer to give a DETAILED answer with specific information

Guidelines for Evidence Filtering:
- Only store evidence that directly helps answer the question
- Discard irrelevant or tangential results
- This improves focus and reduces noise

Guidelines for Answers:
- Extract and include SPECIFIC DETAILS from evidence:
  * Dates and times (e.g., "October 30, 2025")
  * Locations (cities, countries, venues)
  * Names of people, companies, organizations
  * Numbers (flight numbers, booking references, prices)
  * Email subjects and key correspondence details
- Make answers as informative and detailed as possible
- Structure the answer clearly if providing multiple pieces of information
- Be transparent about the strength of evidence in your confidence level

Confidence levels:
- high: Strong, direct evidence clearly answers the question
- medium: Some relevant evidence, but not completely conclusive
- low: Little or no relevant evidence found

Always think step-by-step and explain your search strategy."""
