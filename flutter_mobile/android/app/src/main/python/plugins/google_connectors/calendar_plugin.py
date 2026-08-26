import os
import json
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class CalendarPlugin:
    # We use the same credentials.json but different scopes
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']
    
    def __init__(self, token_path='calendar_token.json', credentials_path='credentials.json'):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None

    def authenticate(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    return False, "credentials.json not found. Please add it to python_backend."
                
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        return True, "Authenticated successfully"

    def execute(self, action, params=None):
        if not self.creds:
            success, msg = self.authenticate()
            if not success: return msg

        service = build('calendar', 'v3', credentials=self.creds)
        
        if action == "list_events":
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            limit = params.get("limit", 5)
            events_result = service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=limit, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            return events

        elif action == "add_event":
            event = {
                'summary': params.get('summary'),
                'location': params.get('location', ''),
                'description': params.get('description', ''),
                'start': {
                    'dateTime': params.get('start_time'), # ISO format
                    'timeZone': params.get('timezone', 'UTC'),
                },
                'end': {
                    'dateTime': params.get('end_time'),
                    'timeZone': params.get('timezone', 'UTC'),
                },
            }
            event = service.events().insert(calendarId='primary', body=event).execute()
            return f"Event created: {event.get('htmlLink')}"

        return "Unknown action"
