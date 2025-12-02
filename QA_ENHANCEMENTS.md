# Q&A Agent Enhancements

## Overview
Enhanced the QuestionAnsweringAgent with evidence filtering and detailed answer generation.

## Key Changes

### 1. Evidence Filtering Tool

**New Tool**: `store_relevant_evidence`

- **Purpose**: Allows the LLM to selectively store only relevant evidence from query results
- **Benefit**: Reduces noise and keeps evidence collection focused
- **Workflow**:
  1. Agent runs `query_evidence` (returns all matching results)
  2. Agent reviews results and decides which are relevant
  3. Agent calls `store_relevant_evidence` with IDs of relevant pieces
  4. Only relevant evidence is tracked in the Answer object

**Example**:
```
Query: "Andy travel 2025" → 20 results
LLM reviews and filters → 3 relevant pieces about Sweden trip
Only those 3 are stored in Answer.queries
```

### 2. Detailed Answer Generation

**Updated**: `provide_answer` tool description and prompt

- **Purpose**: Encourages LLM to extract and include specific details
- **Details to Extract**:
  - Dates and times
  - Locations (cities, countries, venues)
  - Names (people, companies, organizations)
  - Numbers (flight numbers, booking references, prices)
  - Email subjects and key details

**Before**:
```
"Andy traveled to Sweden in 2025"
```

**After**:
```
"Andy traveled to Sweden in 2025. Specifically:
- Dates: October 27-31, 2025
- Program: InTuition Languages immersive homestay
- Location: Gothenburg
- Booking reference: BE17719
- Also visited: World of Volvo Exhibition on October 30, 2025"
```

### 3. Longer Evidence Snippets

Changed evidence display truncation from 200 to 500 characters for better context.

## Implementation Details

### New Agent State

```python
self.last_query_results: List[Evidence] = []  # Pending filter
self.last_query_text: str = ""  # Query that produced results
```

### Updated Workflow

```
1. query_evidence()
   → Returns results to LLM
   → Stores in last_query_results (not tracked yet)

2. store_relevant_evidence(evidence_ids)
   → Filters last_query_results by IDs
   → Creates Query object with filtered evidence
   → Adds to self.queries (now tracked)

3. provide_answer(answer_text, confidence)
   → Returns Answer with only filtered evidence
```

### System Prompt Updates

Added explicit instructions to:
1. Use `store_relevant_evidence` after each query
2. Only store evidence that directly helps answer the question
3. Extract and include specific details in answers
4. Structure answers clearly with dates, names, locations, numbers

## Benefits

1. **Focused Evidence**: Only relevant pieces are saved, reducing clutter
2. **Detailed Answers**: More informative responses with extracted facts
3. **Better Context**: Longer snippets (500 chars) provide more information
4. **Transparency**: Still shows which query found each piece of evidence

## Example Usage

```python
from sherlock.agents import QuestionAnsweringAgent
from sherlock.evidence_store import GmailEvidenceStore
from sherlock.utils import display_answer

gmail_store = GmailEvidenceStore()
qa_agent = QuestionAnsweringAgent(gmail_store, max_iterations=5)

# Agent will now:
# 1. Query for evidence
# 2. Filter to relevant pieces
# 3. Provide detailed answer with specifics
answer = qa_agent.answer_question("Where did Andy travel in 2025?")

print(display_answer(answer))
```

## Logging

New log emojis:
- `✂️` Evidence filtered
- `📭` No relevant evidence in query results
- Previous: `🔍` Query, `📊` Results count, `✅` Answer

## Backward Compatibility

- Existing code continues to work
- If LLM doesn't use `store_relevant_evidence`, all evidence is still accessible via `last_query_results`
- Display functions work with both filtered and unfiltered results
