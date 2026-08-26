import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ..base_plugin import BasePlugin

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Gmail Advanced Reader"

    def _get_service(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    return "ERROR: Missing credentials.json. Please download it from Google Cloud Console."
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('gmail', 'v1', credentials=creds)

    def authenticate(self):
        """Triggers local server OAuth flow and returns success status."""
        try:
            if not os.path.exists('credentials.json'):
                return False, "Missing credentials.json on server. Contact Administrator."
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            return True, "Authenticated"
        except Exception as e:
            return False, str(e)

    def execute(self, action: str, params: dict) -> str:
        if action == "check_emails":
            try:
                service = self._get_service()
                if isinstance(service, str): return service # Error message

                category = params.get("category", "INBOX").upper()
                query = f"label:{category}" if category != "UNREAD" else "is:unread"
                
                results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
                messages = results.get('messages', [])

                if not messages:
                    return f"You have no recent emails in {category}."

                summary = f"Checking your {category} emails:\n"
                for msg in messages:
                    m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
                    headers = m.get('payload', {}).get('headers', [])
                    
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                    
                    summary += f"• From: {sender} | Sub: {subject[:30]}...\n"
                
                return summary
            except Exception as e:
                return f"Gmail API Error: {str(e)}"
        
        return f"Action {action} not supported."

    def get_capabilities(self) -> list[str]:
        return ["check_emails", "compose"]
