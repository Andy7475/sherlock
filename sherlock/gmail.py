

from google.cloud import storage
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config import SCOPES, BUCKET_NAME

CREDS_FILE = "credentials.json"

def create_service():
    """reads credentials from blob storage, checks they are fine, updates if not"""

    credentials_dict = read_credentials()
    print("🔐 [AUTH] Credentials loaded from storage successfully")

    print(f"🔐 [AUTH] Required scopes: {SCOPES}")

    # Check what scopes the stored credentials have
    stored_scopes = credentials_dict.get("scopes", [])
    print(f"🔍 [AUTH] Stored credential scopes: {stored_scopes}")

    creds = Credentials.from_authorized_user_info(info=credentials_dict, scopes=SCOPES)
    print(f"🔐 [AUTH] OAuth2 credentials created")

    if creds.expired:
        print("🔄 [AUTH] Credentials expired, refreshing...")
        try:
            creds.refresh(Request())
            update_credentials(creds)
            print("✅ [AUTH] Credentials refreshed and updated in Cloud Storage")
        except Exception as e:
            print(f"❌ [AUTH] Failed to refresh credentials: {e}")
            print(
                "🔧 [AUTH] This usually means scope mismatch - run auth.py to re-authenticate"
            )
            raise
    else:
        print("✅ [AUTH] Credentials are valid, no refresh needed")

    service = build("gmail", "v1", credentials=creds)
    print("✅ [AUTH] Gmail API service built successfully")
    return service


def read_credentials():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(CREDS_FILE)
    credentials_json = blob.download_as_text()
    credentials_dict = json.loads(credentials_json)
    return credentials_dict


def update_credentials(creds):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(CREDS_FILE)

    # Convert the dictionary to a JSON string
    updated_credentials_json = creds.to_json()

    # Upload the JSON string to the blob
    blob.upload_from_string(updated_credentials_json, content_type="application/json")


def check_stored_scopes():
    """Helper function to check what scopes are stored in Cloud Storage"""
    try:
        credentials_dict = read_credentials()
        stored_scopes = credentials_dict.get("scopes", [])
        print(f"🔍 [DEBUG] Stored scopes: {stored_scopes}")
        print(f"🔍 [DEBUG] Required scopes: {SCOPES}")

        missing_scopes = [scope for scope in SCOPES if scope not in stored_scopes]
        extra_scopes = [scope for scope in stored_scopes if scope not in SCOPES]

        if missing_scopes:
            print(f"❌ [DEBUG] Missing scopes: {missing_scopes}")
        if extra_scopes:
            print(f"⚠️ [DEBUG] Extra scopes: {extra_scopes}")

        if not missing_scopes and not extra_scopes:
            print("✅ [DEBUG] Scopes match perfectly")

        return stored_scopes == SCOPES
    except Exception as e:
        print(f"❌ [DEBUG] Error checking scopes: {e}")
        return False
