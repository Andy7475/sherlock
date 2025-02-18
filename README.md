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

## Applications
* Safety cases
* Investigations
* Law
* Winning arguments with your friends
