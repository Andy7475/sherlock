#!/usr/bin/env python3
"""
Sherlock: Agentic AI evidence evaluation system

This example demonstrates how to use both ChromaDB and Gmail evidence stores
to evaluate claims using supporting and opposing agents.
"""

import os
from sherlock.evidence_store import EvidenceStore, GmailEvidenceStore
from sherlock.models import Claim
from sherlock.agents import ClaimInvestigationAgent
from sherlock.utils import export_argdown
from sherlock.logger_config import get_logger

logger = get_logger(__name__)

def demonstrate_chromadb_store():
    """Demonstrate the original ChromaDB evidence store"""
    print("\n=== ChromaDB Evidence Store Demo ===")
    
    # Initialize ChromaDB store
    store = EvidenceStore("demo_evidence")
    
    # Add some sample evidence
    evidence_data = [
        "The weather forecast shows rain for tomorrow",
        "Multiple weather apps predict sunny skies",
        "Local meteorologist says 30% chance of precipitation", 
        "Satellite images show clear skies approaching",
        "Historical data shows this month typically has dry weather"
    ]
    
    for evidence in evidence_data:
        store.add_evidence(evidence)
    
    # Create a claim and evaluate it
    weather_claim = Claim(text="It will rain tomorrow")
    
    # Create agents
    agent_pro = ClaimInvestigationAgent(store, supports=True)
    agent_con = ClaimInvestigationAgent(store, supports=False)
    
    print(f"Evaluating claim: {weather_claim.text}")
    
    # Evaluate with both agents
    weather_claim = agent_pro.evaluate_claim(weather_claim)
    weather_claim = agent_con.evaluate_claim(weather_claim)
    
    print(f"Final likelihood: {weather_claim.likelihood}")
    print(f"Supporting evidence: {weather_claim.likelihood.supporting}")
    print(f"Opposing evidence: {weather_claim.likelihood.opposing}")
    
    return weather_claim

def demonstrate_gmail_store():
    """Demonstrate the Gmail evidence store"""
    print("\n=== Gmail Evidence Store Demo ===")
    
    try:
        # Initialize Gmail store (will try ADC first, then fall back to OAuth)
        gmail_store = GmailEvidenceStore()
        print("✅ Gmail store initialized successfully!")
        
        # Test a simple query
        results = gmail_store.query("meeting", n_results=3)
        print(f"Found {len(results)} email results for 'meeting'")
        
        if results:
            print("\nSample email evidence:")
            for i, result in enumerate(results[:2]):  # Show first 2
                print(f"{i+1}. ID: {result['id']}")
                if 'metadata' in result:
                    print(f"   Subject: {result['metadata']['subject']}")
                    print(f"   From: {result['metadata']['sender']}")
                print(f"   Preview: {result['text'][:100]}...")
                print()
        
        # Example: Create agents that use Gmail evidence
        print("Creating agents that use Gmail as evidence source...")
        gmail_agent_pro = ClaimInvestigationAgent(gmail_store, supports=True)
        gmail_agent_con = ClaimInvestigationAgent(gmail_store, supports=False)
        
        # Example claim (commented out to avoid making API calls)
        # email_claim = Claim(text="I have meetings scheduled this week")
        # email_claim = gmail_agent_pro.evaluate_claim(email_claim)
        # email_claim = gmail_agent_con.evaluate_claim(email_claim)
        
        print("✅ Gmail evidence store is ready for use!")
        return gmail_store
        
    except FileNotFoundError as e:
        print(f"❌ Gmail setup needed: {e}")
        print("\nTo set up Gmail evidence store (choose one):")
        print("\n🎯 OPTION 1 (Recommended): Use gcloud")
        print("   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        print("   gcloud auth application-default login")
        print("\n📋 OPTION 2: Manual OAuth setup")
        print("   1. Go to Google Cloud Console")
        print("   2. Enable Gmail API")
        print("   3. Create OAuth 2.0 credentials")
        print("   4. Download as 'credentials.json' in project root")
        return None
        
    except Exception as e:
        print(f"❌ Error initializing Gmail store: {e}")
        print("\nTroubleshooting:")
        print("- Ensure Gmail API is enabled in your Google Cloud project")
        print("- Try running: gcloud auth application-default login")
        print("- Check that you have the required permissions")
        return None

def demonstrate_combined_usage():
    """Show how different evidence stores can be used for different types of claims"""
    print("\n=== Combined Evidence Store Usage ===")
    
    print("Different types of claims benefit from different evidence sources:")
    print()
    print("📚 Document-based claims → ChromaDB Evidence Store")
    print("   - Research findings")
    print("   - Technical documentation") 
    print("   - Historical records")
    print()
    print("📧 Communication-based claims → Gmail Evidence Store")
    print("   - Meeting arrangements")
    print("   - Project communications")
    print("   - Email confirmations")
    print()
    print("🔄 Complex claims → Multiple Evidence Stores")
    print("   - Create specialized agents for each source")
    print("   - Combine evidence from multiple domains")
    print("   - Cross-reference findings")

def main():
    """Main demonstration function"""
    print("🕵️ Sherlock: Agentic AI Evidence Evaluation System")
    print("=" * 60)
    
    # Demonstrate ChromaDB store
    chromadb_claim = demonstrate_chromadb_store()
    
    # Demonstrate Gmail store
    gmail_store = demonstrate_gmail_store()
    
    # Show combined usage concepts
    demonstrate_combined_usage()
    
    # Export argdown for visualization
    if chromadb_claim:
        print("\n=== Argdown Export ===")
        argdown_text = export_argdown(chromadb_claim)
        with open("demo_argument.txt", "w") as f:
            f.write(argdown_text)
        print("✅ Argument exported to demo_argument.txt")
        print("   Paste the content at: https://argdown.org/sandbox/html")
    
    print(f"\n🎉 Demo complete!")
    if gmail_store:
        print("Both evidence stores are ready for use!")
    else:
        print("ChromaDB store ready. Set up Gmail credentials for full functionality.")


if __name__ == "__main__":
    main()
