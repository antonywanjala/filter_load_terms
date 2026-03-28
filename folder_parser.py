import os
import time
# 1. Static Import: Import your local script here
from sample import sample

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
LOCAL_VAR_FILE = "local_vars.txt"


def get_drive_service():
    """Handles Google API Authentication."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)


def load_local_variables(filepath):
    """Reads variables from a local text file and returns a dictionary."""
    local_vars = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if ":" in line and not line.startswith("#"):
                    key, val = line.split(":", 1)
                    local_vars[key.strip()] = val.strip()
    return local_vars


def parse_syntax(content, local_vars):
    """
    Parses Google Drive content, merges with local variables,
    and passes them to the PRE-IMPORTED sample function.
    """
    lines = content.split('\n')
    # Start with local variables as the base
    context_vars = local_vars.copy()

    for line in lines:
        # Manual bracket removal
        while "[" in line and "]" in line:
            start = line.find("[")
            end = line.find("]") + 1
            line = line[:start] + line[end:]

        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 1. Capture variables from the Drive Document
        if ":" in line and not line.startswith("run"):
            try:
                key, val = line.split(":", 1)
                context_vars[key.strip()] = val.strip()
            except ValueError:
                continue

        # 2. Trigger the pre-imported function
        elif line.startswith("run:"):
            print(f"---> Passing all variables to sample.main_process()...")
            try:
                # 2. CALL THE STATICALLY IMPORTED FUNCTION
                # This assumes sample.py has a function called 'main_process'
                sample(**context_vars)
            except Exception as e:
                print(f"Error executing sample function: {e}")


def main():
    folder_id = input("Enter the Google Drive Folder ID: ")
    poll_interval = 30
    service = get_drive_service()
    known_files = {}

    print(f"Monitoring folder {folder_id}...")

    try:
        while True:
            # Refresh local variables from local_vars.txt every loop
            local_vars = load_local_variables(LOCAL_VAR_FILE)

            query = f"'{folder_id}' in parents"
            results = service.files().list(q=query, fields="files(id, name, modifiedTime, mimeType)").execute()
            items = results.get('files', [])

            for item in items:
                f_id = item['id']
                m_time = item['modifiedTime']

                if f_id not in known_files or known_files[f_id] != m_time:
                    known_files[f_id] = m_time
                    print(f"\n--- Change detected: {item['name']} ---")

                    try:
                        if item['mimeType'] == 'application/vnd.google-apps.document':
                            request = service.files().export_media(fileId=f_id, mimeType='text/plain')
                        else:
                            request = service.files().get_media(fileId=f_id)

                        content = request.execute().decode('utf-8')
                        parse_syntax(content, local_vars)
                    except Exception as e:
                        print(f"Error: {e}")

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    main()
