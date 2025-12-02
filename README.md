# sherlock
Exploring how agents can deduce and reason within a philosophical framework on argument construction

# Basic premise
Inpsired by a quote from Google Deepmind Head of AI Safety, Prof. Anca Dragan (on one of the Deepmind Podcasts).
The gist was, that when LLMs debate each other, the truth wins.
So let's have 2 agents (one 'for' and one 'against'), battle out to verify or dispute a claim.

## Framework
If we can get the 'atoms' of an argument correct, then we should be able to scale an agentic system to perform many layers of inference, given access to a pool of evidence.

Current approach is to define classes on:
* Questions: the thing you are trying to answer (e.g. 'Where's Wally)
* Claims (a verifiable statement - true or false)
  * Wally is in the library
* Argument (a collection of premises: evidence or other claims that supports or refutes a parent claim)
  * Arguments are deductive, inductive or abductive
  * 'Dave said he saw Wally in the Library' - evidence
  * 'Dave always tells the truth' - claim
* Evidence (bits of information, could be photos, videos, documents)
  * a stripey t-shirt was found in the library
 
Then arrange these in a critical thinking diagram. Inspired by https://argumentation.io/ 

## Evidence Stores

Sherlock supports multiple evidence stores that can be used individually or together:

### ChromaDB Evidence Store (Default)
The original local document store using vector embeddings for semantic search.

### Gmail Evidence Store (NEW)
Search your Gmail inbox as an evidence source. Useful for finding email conversations, receipts, confirmations, and other email-based evidence.

#### Gmail Setup Instructions

**Using Existing Gmail Authentication (Recommended)**

Since you already have a working Gmail authentication system, the Gmail evidence store uses your existing `create_service()` function:

1. **Make sure your Gmail credentials are in Cloud Storage:**
   - Your existing `credentials.json` should already be in your Cloud Storage bucket
   - The bucket name is configured in `sherlock/gmail.py` (currently set to `auto-gmail-421611`)

2. **Ensure proper scopes:**
   - Your Gmail credentials should have the required scopes for reading emails
   - The evidence store only needs read access to search emails

3. **Usage:**
   ```python
   from sherlock.evidence_store import GmailEvidenceStore
   
   # Uses your existing create_service() function automatically
   gmail_store = GmailEvidenceStore()
   
   # Search your emails
   results = gmail_store.query("meeting tomorrow")
   ```

**Configuration:**
- Bucket name: Edit `BUCKET_NAME` in `sherlock/gmail.py` 
- Scopes: Already configured in your existing setup
- Credentials: Uses your existing Cloud Storage credentials

This leverages your proven authentication system that already works!

#### Usage Example

```python
from sherlock.evidence_store import GmailEvidenceStore

# Initialize Gmail evidence store (tries ADC first, falls back to OAuth)
gmail_store = GmailEvidenceStore()

# Search your emails
results = gmail_store.query("meeting tomorrow")
for result in results:
    print(f"Subject: {result['metadata']['subject']}")
    print(f"From: {result['metadata']['sender']}")
    print(f"Preview: {result['text'][:100]}...")
```

## Applications
* Safety cases
* Investigations
* Law
* Winning arguments with your friends

## Seeing the argument diagrams
Paste the output text here: https://argdown.org/sandbox/html

