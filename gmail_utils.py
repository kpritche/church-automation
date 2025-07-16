import os.path
import base64
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def fetch_latest_announcement_html(service, query):
    results = service.users().messages().list(userId='me', q=query).execute()
    msg_id = results['messages'][0]['id']
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    parts = msg['payload']['parts']
    for part in parts:
        if part['mimeType'] == 'text/html':
            return base64.urlsafe_b64decode(part['body']['data']).decode()
    return ""
