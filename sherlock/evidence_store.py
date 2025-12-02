import chromadb
from chromadb.utils import embedding_functions
import os
import pickle
import json
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import storage
import google.auth
from sherlock.logger_config import get_logger

logger = get_logger(__name__)

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
    
    def query(self, text, n_results=10):
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


class GmailEvidenceStore:
    """Evidence store that searches Gmail using the proven create_service() function"""

    def __init__(self, max_content_length: int = 512):
        """
        Initialize Gmail evidence store using the existing create_service() function

        Args:
            max_content_length: Maximum number of characters to include from email body (default: 512)
        """
        self.service = None
        self.max_content_length = max_content_length
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate using the proven create_service() function"""
        try:
            logger.info("🔐 [AUTH] Initializing Gmail service using proven create_service() function...")

            # Import and use the working create_service function
            from sherlock.gmail import create_service
            self.service = create_service()

            logger.info("✅ [AUTH] Gmail service created successfully using create_service()")

            # Test the connection
            try:
                profile = self.service.users().getProfile(userId='me').execute()
                logger.info(f"✅ [AUTH] Gmail API test successful. Email: {profile.get('emailAddress', 'Unknown')}")
            except Exception as test_error:
                logger.error(f"❌ [AUTH] Gmail API test failed: {test_error}")
                raise test_error

        except ImportError as e:
            logger.error(f"❌ [AUTH] Could not import create_service from sherlock.gmail: {e}")
            logger.error("📁 [AUTH] Make sure gmail.py is in the sherlock directory with create_service() function")
            raise
        except Exception as e:
            error_str = str(e)

            # Check if it's a scope mismatch error
            if "invalid_scope" in error_str or "scope mismatch" in error_str.lower():
                logger.error(f"❌ [AUTH] Scope mismatch detected: {e}")
                logger.error("🔧 [AUTH] Your stored credentials don't have all required scopes")
                logger.error("🔧 [AUTH] Starting re-authentication flow...")

                # Try to re-authenticate with proper scopes
                try:
                    self._reauth_with_new_scopes()
                except Exception as reauth_error:
                    logger.error(f"❌ [AUTH] Re-authentication failed: {reauth_error}")
                    raise
            else:
                logger.error(f"❌ [AUTH] Failed to create Gmail service: {e}")
                logger.error("🔧 [AUTH] Check your Cloud Storage credentials and bucket configuration")
                raise

    def _reauth_with_new_scopes(self):
        """Re-authenticate with the correct scopes"""
        from config import SCOPES, BUCKET_NAME
        from sherlock.gmail import update_credentials

        logger.info("🔐 [AUTH] Starting OAuth flow for new scopes...")
        logger.info(f"🔍 [AUTH] Required scopes: {SCOPES}")

        # Check if client_secret.json exists
        client_secret_file = "client_secret.json"
        if not os.path.exists(client_secret_file):
            logger.error(f"❌ [AUTH] {client_secret_file} not found")
            logger.error("📝 [AUTH] Please download OAuth credentials from Google Cloud Console")
            logger.error("📝 [AUTH] Go to: https://console.cloud.google.com/apis/credentials")
            raise FileNotFoundError(f"{client_secret_file} not found. Download from Google Cloud Console.")

        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
        creds = flow.run_local_server(port=0)

        logger.info("✅ [AUTH] OAuth flow completed successfully")

        # Update credentials in Cloud Storage
        update_credentials(creds)
        logger.info("✅ [AUTH] Credentials updated in Cloud Storage")

        # Build service with new credentials
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("✅ [AUTH] Gmail service rebuilt with new credentials")

        # Test the connection
        profile = self.service.users().getProfile(userId='me').execute()
        logger.info(f"✅ [AUTH] Re-authentication successful! Email: {profile.get('emailAddress', 'Unknown')}")
        
    def query(self, text: str, n_results: int = 25) -> List[Dict[str, Any]]:
        """
        Search Gmail for emails matching the query text
        
        Args:
            text: Search query
            n_results: Maximum number of results to return
            
        Returns:
            List of evidence results in same format as EvidenceStore
        """
        try:
            search_query = text
            logger.info(f"🔍 [GMAIL] Searching Gmail with query: {search_query}")
            
            # Get list of message IDs
            results = self.service.users().messages().list(
                userId='me', 
                q=search_query, 
                maxResults=n_results
            ).execute()
            
            messages = results.get('messages', [])
            evidence_results = []
            
            # Fetch full message details for each result
            for i, message in enumerate(messages):
                try:
                    msg = self.service.users().messages().get(
                        userId='me', 
                        id=message['id'],
                        format='full'
                    ).execute()
                    # The Gmail API returns a 'snippet' field in the message resource, which is a short preview of the message text.
                    # You can access it via msg.get('snippet')
                    
                    # Extract email content with configured max length
                    email_data = self._extract_email_content(msg, self.max_content_length)
                    
                    # Build email text with optional fields
                    email_text = (
                        f"Email\n"
                        f"Subject: {email_data['subject']}\n"
                        f"From: {email_data['sender']}\n"
                    )
                    if email_data.get('recipient'):
                        email_text += f"To: {email_data['recipient']}\n"
                    if email_data.get('cc'):
                        email_text += f"CC: {email_data['cc']}\n"
                    email_text += (
                        f"Date: {email_data['date']}\n"
                        f"Snippet: {email_data['snippet']}\n"
                        f"Content: {email_data['content']}"
                    )

                    evidence = {
                        "id": f"gmail_{message['id']}",
                        "text": email_text
                    }
                    logger.info(f"📥 [GMAIL] Adding evidence: {evidence['text'][:250]}...")
                    evidence_results.append(evidence)
                    
                except HttpError as error:
                    logger.warning(f"⚠️ [GMAIL] Error fetching message {message['id']}: {error}")
                    continue
                    
            logger.info(f"✅ [GMAIL] Found {len(evidence_results)} email results for query: {text}")
            return evidence_results
            
        except HttpError as error:
            logger.error(f"❌ [GMAIL] Gmail API error: {error}")
            return []
            
    def _extract_email_content(self, message: Dict, max_content_length: int) -> Dict[str, str]:
        """
        Extract relevant content from Gmail message

        Args:
            message: Gmail message object
            max_content_length: Maximum characters to include from email body
        """
        payload = message['payload']
        snippet = message.get('snippet', '')
        headers = payload.get('headers', [])
        
        # Extract headers
        subject = ""
        sender = ""
        date = ""
        recipient = ""
        cc = ""

        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                subject = header['value']
            elif name == 'from':
                sender = header['value']
            elif name == 'date':
                date = header['value']
            elif name == 'to':
                recipient = header['value']
            elif name == 'cc':
                cc = header['value']
                
        # Extract body content
        body = self._extract_body(payload)
        
        # Create a comprehensive text representation
        content = f"Subject: {subject}\n"
        content += f"From: {sender}\n"
        if recipient:
            content += f"To: {recipient}\n"
        if cc:
            content += f"CC: {cc}\n"
        content += f"Date: {date}\n"
        content += f"Content: {body}"

        return {
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "cc": cc,
            "date": date,
            "content": content[:max_content_length],
            "snippet": snippet
        }
        
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from message payload"""
        body = ""
        
        if 'parts' in payload:
            # Multi-part message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        import base64
                        body += base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    # For HTML, we could parse it, but for simplicity just include it
                    if 'data' in part['body'] and not body:  # Only if no plain text found
                        import base64
                        html_content = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        # Basic HTML stripping (in production, use proper HTML parser)
                        import re
                        body += re.sub('<[^<]+?>', '', html_content)
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                if 'data' in payload['body']:
                    import base64
                    body = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8')
                    
        return body.strip()