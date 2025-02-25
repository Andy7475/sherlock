from typing import Dict, List
from sherlock.models import Claim, Argument, Evidence, EvidenceCollection

def export_argdown(claim: Claim) -> str:
    """
    Export a Claim object to Argdown markup for visualisation.
    
    Args:
        claim: A Claim object with arguments and evidence
        
    Returns:
        String containing Argdown markup
    """
    # Start building the Argdown document
    argdown = f"# {claim.text}\n\n"
    
    # Define the main claim
    argdown += f"[{claim.id}]: {claim.text}\n"
    
    # Process all arguments
    for i, argument in enumerate(claim.arguments):
        arg_id = f"Argument {i+1}"
        
        # Define relation between claim and argument (supporting or opposing)
        if argument.supports:
            argdown += f"  + <{arg_id}>: {argument.text}\n"
        else:
            argdown += f"  - <{arg_id}>: {argument.text}\n"
            
        # Add evidence as premises in argument reconstruction section
        if argument.evidence_collection and len(argument.evidence_collection.evidence) > 0:
            argdown += f"\n<{arg_id}>\n\n"
            
            # Add premises (evidence)
            for j, evidence in enumerate(argument.evidence_collection.evidence):
                argdown += f"({j+1}) Evidence {evidence.id}: {evidence.text}\n"
            
            argdown += "--\n"  # Inference separator
            argdown += "Therefore\n"  # Inference rule
            argdown += "--\n"
            argdown += f"({len(argument.evidence_collection.evidence) + 1}) {argument.text}\n"
            
            # Add relation back to the main claim
            if argument.supports:
                argdown += f"  -> [{claim.id}]\n"
            else:
                argdown += f"  -| [{claim.id}]\n"
                
        # Process subclaims if any
        if argument.subclaims:
            for subclaim in argument.subclaims:
                argdown += f"\n## Subclaim: {subclaim.text}\n\n"
                argdown += f"[{subclaim.id}]: {subclaim.text}\n"
                
                # Relation between argument and subclaim
                argdown += f"<{arg_id}>\n  -> [{subclaim.id}]\n"
            
        argdown += "\n"  # Add spacing between arguments
    
    # Add likelihood section if available
    if claim.likelihood:
        argdown += "\n## Likelihood Assessment\n\n"
        argdown += f"Supporting evidence: {claim.likelihood.supporting} ({claim.likelihood.supporting_percentage:.1f}%)\n"
        argdown += f"Opposing evidence: {claim.likelihood.opposing} ({claim.likelihood.opposing_percentage:.1f}%)\n"
    
    return argdown


def export_argdown_json(claim: Claim) -> Dict:
    """
    Export a Claim object to Argdown JSON format for visualisation.
    
    Args:
        claim: A Claim object with arguments and evidence
        
    Returns:
        Dictionary in Argdown JSON format
    """
    # Create statements dictionary
    statements = {
        claim.id: {
            "text": claim.text,
            "title": claim.id
        }
    }
    
    # Create arguments dictionary
    arguments = {}
    
    # Create relations list
    relations = []
    
    # Process all arguments
    for i, argument in enumerate(claim.arguments):
        arg_id = f"argument_{i+1}"
        
        # Add argument to arguments dictionary
        arguments[arg_id] = {
            "text": argument.text,
            "title": f"Argument {i+1}"
        }
        
        # Add relation between argument and claim
        relation_type = "support" if argument.supports else "attack"
        relations.append({
            "from": arg_id,
            "to": claim.id,
            "type": relation_type
        })
        
        # Process evidence as premises
        premises = []
        for j, evidence in enumerate(argument.evidence_collection.evidence):
            evidence_id = f"evidence_{evidence.id}"
            
            # Add evidence as statement
            statements[evidence_id] = {
                "text": evidence.text,
                "title": f"Evidence {evidence.id}"
            }
            
            # Add premise
            premises.append(evidence_id)
            
            # Add relation from evidence to argument
            relations.append({
                "from": evidence_id,
                "to": arg_id,
                "type": "premise"
            })
        
        # Process subclaims
        for subclaim in argument.subclaims:
            subclaim_id = subclaim.id
            
            # Add subclaim as statement
            statements[subclaim_id] = {
                "text": subclaim.text,
                "title": subclaim_id
            }
            
            # Add relation from argument to subclaim
            relations.append({
                "from": arg_id,
                "to": subclaim_id,
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