# Building an AI Agent to Answer Questions from Your Gmail

I've been experimenting with **agentic AI** to build a personal knowledge assistant that answers questions by searching through my Gmail history. Here's how it works:

## The Approach

Instead of manually searching through thousands of emails, I built an **AI agent** that:
1. Takes natural language questions (e.g., "Where did I travel abroad in 2025?")
2. Breaks them down into targeted searches
3. Gathers relevant evidence from Gmail
4. Synthesizes a detailed answer with citations

## Architecture

### Tool-Use Pattern

The system uses **Claude's tool-use API** to give the LLM three capabilities:

1. **`query_evidence`** - Search Gmail using full Gmail query syntax
2. **`store_relevant_evidence`** - Filter results to keep only relevant emails
3. **`provide_answer`** - Return a detailed answer with confidence level

The agent iteratively calls these tools until it has enough information to answer confidently.

### Gmail Integration

Rather than vector embeddings, I query Gmail directly using its native search:
- Full Gmail search syntax (`from:`, `after:`, boolean operators)
- Real-time access to latest emails
- No need for indexing or embeddings
- Extracts: sender, recipient, CC, date, subject, and body content

### Evidence Tracking

Every piece of evidence knows:
- Which query found it
- The full email metadata
- When it was retrieved

This provides **complete transparency** - you can see exactly what the agent searched for and what it found.

## Key Features

**Iterative Search**: The agent refines its searches based on what it finds, just like a human would.

**Evidence Filtering**: The LLM decides which emails are actually relevant, discarding noise.

**Detailed Answers**: Extracts specific information (dates, locations, names, booking references) from evidence.

**Performance Metrics**: Tracks iterations, queries, evidence count, and time to answer.

**Early Termination**: Stops searching as soon as it has enough evidence to answer confidently.

## Example

**Question**: "Where did Andy travel abroad in 2025?"

**Agent Process**:
- Query 1: `"Andy travel abroad 2025"` → 0 results
- Query 2: `"Andy 2025 trip OR flight"` → 10 results → filters to 3 relevant
- Query 3: `"Andy Sweden Gothenburg 2025"` → 3 results → filters to 2 relevant
- **Answer**: "Andy traveled to Sweden in October 2025, specifically an immersive language homestay in Gothenburg from October 27-31, booking reference BE17719."

**Metrics**: 3 iterations, 3 queries, 5 evidence pieces, 12.4 seconds

## Why This Works

**No RAG complexity**: Direct Gmail search is simpler and more reliable than maintaining vector embeddings.

**Transparent reasoning**: Every search and decision is logged and visible.

**Structured outputs**: Pydantic models ensure consistent data structures.

**Rate limit handling**: Automatic retry with exponential backoff.

**Flexible content**: Configurable email body length based on your needs.

## Technical Stack

- **LLM**: Claude Sonnet 4.5 (extended thinking, tool use)
- **Email API**: Gmail API with OAuth2
- **Storage**: Google Cloud Storage for credentials
- **Models**: Pydantic for structured data
- **Language**: Python

## What's Next?

I'm exploring:
- Multi-agent collaboration (research agent + fact-checking agent)
- Argument mapping for complex claims (supporting/opposing evidence)
- Integration with other data sources beyond Gmail
- Automated fact extraction and timeline building

The key insight: **Give the LLM the right tools, not the right context**. Instead of stuffing everything into a prompt, let it search iteratively like a human researcher would.

---

*Code available at: [your repo link]*

#AI #LLM #Agents #Gmail #Claude #Python #MachineLearning
