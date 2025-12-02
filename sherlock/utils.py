from typing import Dict
import re
from sherlock.models import Claim, Argument, Evidence, EvidenceCollection, Answer

def export_argdown(claim: Claim) -> str:
    """
    Export a Claim object to Argdown markup for visualisation using a simple format.
    
    Args:
        claim: A Claim object with arguments and evidence
        
    Returns:
        String containing Argdown markup
    """
    # Start building the Argdown document
    argdown = f"# {claim.text}\n\n"
    
    # Define the main claim - replace underscores with hyphens in ID
    claim_id = claim.id.replace('_', '-') if claim.id else claim.id
    argdown += f"[{claim_id}]: {claim.text} "
    argdown += f"({claim.likelihood})\n"
    
    # Process all arguments
    for i, argument in enumerate(claim.arguments):
        # Define relation between claim and argument (supporting or opposing)
        # Use "Argument N" format instead of UUIDs for better readability
        arg_id = f"Argument {i+1}"
        
        if argument.supports:
            argdown += f"  + <{arg_id}>: {argument.text}\n"
        else:
            argdown += f"  - <{arg_id}>: {argument.text}\n"
        
        # Add evidence as bullet points
        if argument.evidence_collection and len(argument.evidence_collection.evidence) > 0:
            for evidence in argument.evidence_collection.evidence:
                # Replace any underscores in evidence text or ID
                evidence_text = evidence.text
                evidence_id = evidence.id.replace('_', '-') if evidence.id else ""
                
                # If evidence ID is included in text, replace underscores there too
                if evidence_id and evidence_id in evidence_text:
                    evidence_text = evidence_text.replace(evidence_id, evidence_id.replace('_', '-'))
                
                # Add the evidence as a bullet point
                argdown += f"    + {evidence_text}\n"
    
    # Add likelihood section if available
    if claim.likelihood:
        argdown += "\n## Likelihood Assessment\n\n"
        argdown += f"Supporting evidence: {claim.likelihood.supporting} ({claim.likelihood.supporting_percentage:.1f}%)\n"
        argdown += f"Opposing evidence: {claim.likelihood.opposing} ({claim.likelihood.opposing_percentage:.1f}%)\n"
    
    return argdown


def _replace_underscores(text: str) -> str:
    """Replace underscores with hyphens to avoid Argdown's markdown italics parsing."""
    return text.replace('_', '-') if text else text


def export_argdown_json(claim: Claim) -> Dict:
    """
    Export a Claim object to Argdown JSON format for visualisation.
    
    Args:
        claim: A Claim object with arguments and evidence
        
    Returns:
        Dictionary in Argdown JSON format
    """
    # Create statements dictionary - replace underscores with hyphens in IDs
    claim_id = _replace_underscores(claim.id)
    statements = {
        claim_id: {
            "text": claim.text,
            "title": claim_id
        }
    }
    
    # Create arguments dictionary
    arguments = {}
    
    # Create relations list
    relations = []
    
    # Process all arguments
    for i, argument in enumerate(claim.arguments):
        # Use "Argument N" format instead of UUIDs
        arg_id = f"argument_{i+1}"
        
        # Add argument to arguments dictionary
        arguments[arg_id] = {
            "text": argument.text,
            "title": arg_id
        }
        
        # Add relation between argument and claim
        relation_type = "support" if argument.supports else "attack"
        relations.append({
            "from": arg_id,
            "to": claim.id,
            "type": relation_type
        })
        
        # Process evidence
        for j, evidence in enumerate(argument.evidence_collection.evidence):
            original_evidence_id = evidence.id
            evidence_id = _replace_underscores(original_evidence_id)
            
            # Add evidence as statement
            statements[evidence_id] = {
                "text": evidence.text,
                "title": f"Evidence {evidence_id}"
            }
            
            # Add relation from evidence to argument
            relations.append({
                "from": evidence_id,
                "to": arg_id,
                "type": "support"
            })
    
    # Build the final JSON structure
    argdown_json = {
        "statements": statements,
        "arguments": arguments,
        "relations": relations,
        "metadata": {
            "title": claim.text,
            "likelihood": {
                "supporting": claim.likelihood.supporting,
                "opposing": claim.likelihood.opposing,
                "supporting_percentage": claim.likelihood.supporting_percentage,
                "opposing_percentage": claim.likelihood.opposing_percentage
            }
        }
    }
    
    return argdown_json


def display_answer(answer: Answer) -> str:
    """
    Format an Answer object for display with questions, answers, queries, and evidence.

    Args:
        answer: An Answer object from QuestionAnsweringAgent

    Returns:
        String containing formatted answer with all queries and evidence
    """
    output = []

    # Header
    output.append("=" * 80)
    output.append("QUESTION & ANSWER")
    output.append("=" * 80)
    output.append("")

    # Question
    output.append(f"❓ Question:")
    output.append(f"   {answer.question}")
    output.append("")

    # Answer
    output.append(f"💬 Answer (Confidence: {answer.confidence.upper()}):")
    output.append(f"   {answer.answer_text}")
    output.append("")

    # Statistics
    output.append(f"📊 Search Summary:")
    output.append(f"   • Iterations used: {answer.iterations_used}")
    output.append(f"   • Total queries made: {answer.total_queries}")
    output.append(f"   • Total evidence found: {answer.total_evidence}")
    output.append(f"   • Time taken: {answer.time_seconds}s")
    output.append("")

    # Queries and Evidence
    if answer.queries:
        output.append("🔍 Queries & Evidence:")
        output.append("")

        for i, query in enumerate(answer.queries, 1):
            output.append(f"   Query {i}: \"{query.query_text}\"")
            output.append(f"   Found: {len(query)} piece(s) of evidence")

            if query.evidence_found:
                output.append("")
                for j, evidence in enumerate(query.evidence_found, 1):
                    # Truncate long evidence text
                    evidence_text = evidence.text
                    if len(evidence_text) > 500:
                        evidence_text = evidence_text[:500] + "..."

                    output.append(f"      Evidence {i}.{j}:")
                    # Split long lines for better readability
                    for line in evidence_text.split('\n'):
                        if line.strip():
                            output.append(f"         {line.strip()}")
                    output.append("")
            else:
                output.append("      (No evidence found)")
                output.append("")
    else:
        output.append("🔍 No queries were made")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


def display_answer_compact(answer: Answer) -> str:
    """
    Format an Answer object in a compact format showing just answer and key evidence.

    Args:
        answer: An Answer object from QuestionAnsweringAgent

    Returns:
        String containing compact formatted answer
    """
    output = []

    output.append(f"Q: {answer.question}")
    output.append(f"A: {answer.answer_text} (confidence: {answer.confidence})")
    output.append(f"   [{answer.iterations_used} iterations, {answer.total_queries} queries, {answer.total_evidence} evidence pieces, {answer.time_seconds}s]")

    return "\n".join(output)