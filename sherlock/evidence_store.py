import chromadb
from chromadb.utils import embedding_functions

class EvidenceStore:
    """A handy way to query and add evidence to a chromadb local client"""
    def __init__(self, collection_name="wally_evidence"):

        self.client = chromadb.Client()
        self.embedder = embedding_functions.DefaultEmbeddingFunction()
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedder
        )
    
    def add_evidence(self, evidence_text, metadata=None):
        # Generate a simple ID
        evidence_id = f"ev_{len(self.collection.get()['ids']) + 1}"
        
        # Add to collection
        self.collection.add(
            ids=[evidence_id],
            documents=[evidence_text],
            metadatas=[metadata or {"type": "evidence"}]
        )
        
        return evidence_id
    
    def query(self, text, n_results=3):
        # Simple query function
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )
        
        # Return results in a simpler format
        evidence_results = []
        if results and results['ids'] and results['ids'][0]:
            for i, ev_id in enumerate(results['ids'][0]):
                evidence_results.append({
                    "id": ev_id,
                    "text": results['documents'][0][i],
                    "score": results['distances'][0][i] if 'distances' in results else None
                })
                
        return evidence_results