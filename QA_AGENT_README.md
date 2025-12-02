# Question Answering Agent

A new agent that answers questions by gathering evidence through iterative searches, with full query transparency.

## Overview

The `QuestionAnsweringAgent` is designed to answer factual questions by:
1. Breaking down questions into search queries
2. Gathering evidence from your data sources (Gmail, ChromaDB, etc.)
3. Tracking all queries for transparency
4. Providing answers with confidence levels based on evidence strength

Unlike the `ClaimInvestigationAgent` which evaluates "for" and "against" arguments, the Q&A agent focuses purely on finding answers.

## Key Features

- **Query Tracking**: Every search query is logged and linked to the evidence it found
- **Evidence Transparency**: All evidence pieces know which query discovered them
- **Iteration Limits**: Automatically provides an answer after max iterations
- **Confidence Levels**: Low/Medium/High confidence based on evidence quality
- **Rich Display**: Multiple display formats for answers

## Models

### Evidence (Updated)
```python
class Evidence(BaseModel):
    id: str
    text: str
    query: Optional[str]  # NEW: The query that found this evidence
```

### Query
```python
class Query(BaseModel):
    query_text: str
    evidence_found: List[Evidence]
```

### Answer
```python
class Answer(BaseModel):
    question: str
    answer_text: str
    queries: List[Query]
    confidence: str  # "low", "medium", or "high"

    # Properties:
    @property
    def all_evidence(self) -> List[Evidence]  # All evidence from all queries

    @property
    def total_queries(self) -> int

    @property
    def total_evidence(self) -> int
```

## Usage

### Basic Usage

```python
from sherlock.agents import QuestionAnsweringAgent
from sherlock.evidence_store import GmailEvidenceStore
from sherlock.utils import display_answer

# Initialize evidence store
gmail_store = GmailEvidenceStore()

# Create Q&A agent
qa_agent = QuestionAnsweringAgent(gmail_store, max_iterations=5)

# Ask a question
answer = qa_agent.answer_question("Where did Andy travel abroad in 2025?")

# Display the answer
print(display_answer(answer))
```

### Display Options

**Full Display** (with all queries and evidence):
```python
from sherlock.utils import display_answer
print(display_answer(answer))
```

**Compact Display**:
```python
from sherlock.utils import display_answer_compact
print(display_answer_compact(answer))
```

**Programmatic Access**:
```python
# Access answer components
print(f"Question: {answer.question}")
print(f"Answer: {answer.answer_text}")
print(f"Confidence: {answer.confidence}")

# Access queries
for query in answer.queries:
    print(f"Query: {query.query_text}")
    print(f"Found: {len(query.evidence_found)} pieces")

    # Each evidence knows its source query
    for evidence in query.evidence_found:
        print(f"  - {evidence.text[:100]}...")
        print(f"  - Found by: {evidence.query}")
```

## How It Works

1. **Question Analysis**: The LLM analyzes the question to identify key search terms
2. **Iterative Search**: Makes 2-5 targeted searches using the `query_evidence` tool
3. **Evidence Gathering**: Each query returns evidence, all tracked with query metadata
4. **Answer Generation**: Uses `provide_answer` tool with confidence assessment
5. **Forced Completion**: On last iteration, forces answer creation even if evidence is limited

## Logging

The agent logs all activities with emojis for easy scanning:

- `❓` Question being answered
- `🔍` Queries being executed
- `📊` Evidence counts
- `💭` LLM thinking steps
- `🔧` Tool calls
- `✅` Answer provided
- `⚠️` Warnings (e.g., last iteration forcing)

## Confidence Levels

- **High**: Strong, direct evidence clearly answers the question
- **Medium**: Some relevant evidence, but not completely conclusive
- **Low**: Little or no relevant evidence found

## Configuration

```python
QuestionAnsweringAgent(
    evidence_store,      # Your evidence store (Gmail, ChromaDB, etc.)
    max_iterations=5     # Max search iterations before forcing answer
)
```

## Example Output

```
================================================================================
QUESTION & ANSWER
================================================================================

❓ Question:
   Where did Andy travel abroad in 2025?

💬 Answer (Confidence: HIGH):
   Based on the evidence, Andy traveled to Sweden in 2025. Specifically, he
   attended an immersive language homestay program and visited Gothenburg.

📊 Search Summary:
   • Total queries made: 3
   • Total evidence found: 12

🔍 Queries & Evidence:

   Query 1: "Andy travel abroad 2025"
   Found: 0 piece(s) of evidence
      (No evidence found)

   Query 2: "Andy (Sweden OR Volvo OR international) after:2025/01/01"
   Found: 6 piece(s) of evidence

      Evidence 2.1:
         Email about World of Volvo Exhibition ticket purchase...

      Evidence 2.2:
         Email about InTuition Languages homestay in Sweden...

   Query 3: "Andy homestay Sweden after:2025/01/01"
   Found: 6 piece(s) of evidence

      Evidence 3.1:
         Google Maps review reply for immersive Sweden experience...

================================================================================
```

## Integration with Existing Code

The Q&A agent:
- Uses the same `EvidenceStore` interface as `ClaimInvestigationAgent`
- Works with `GmailEvidenceStore` and ChromaDB stores
- Follows the same tool-use pattern with forced completion
- Logs LLM thinking steps like the claim agent

## Future Enhancements

Possible improvements:
- Support for follow-up questions with context
- Multi-source evidence synthesis
- Citation formatting (e.g., footnotes)
- Export to different formats (JSON, Markdown, HTML)
- Answer comparison (multiple runs)
