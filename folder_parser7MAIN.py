import time
import io
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Define the scope for Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def get_service():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('drive', 'v3', credentials=creds)


def parse_content(text):
    """
    Manual interpreter without Regex or Argparse.
    Expects format: action value key2 value2
    Example: output "Hello from Google Drive!" Speed 10
    """
    parts = text.strip().split()
    if not parts:
        return

    # Logical mapping for the specific output format requested
    # Basic index-based extraction as an alternative to argparse
    action = parts if len(parts) > 0 else "None"

    # Reconstructing the message (everything between action and Speed)
    message = ""
    speed = "N/A"

    for i in range(1, len(parts)):
        if parts[i].lower() == "speed":
            if i + 1 < len(parts):
                speed = parts[i + 1]
            break
        else:
            message += parts[i] + " "

    print(f"Action: {action} Message: {message.strip().replace('\"', '')} Speed: {speed}")


def monitor_folder(folder_id, interval):
    service = get_service()
    processed_files = set()

    print(f"Monitoring Folder: {folder_id} every {interval} seconds...")

    while True:
        # Query for files in the specific folder
        query = f"'{folder_id}' in parents and (mimeType = 'text/plain' or mimeType = 'application/vnd.google-apps.document')"
        results = service.files().list(q=query, fields="files(id, name, mimeType, modifiedTime)").execute()
        items = results.get('files', [])

        for item in items:
            file_id = item['id']
            # Only process if file was modified since last check
            file_key = f"{file_id}_{item['modifiedTime']}"

            if file_key not in processed_files:
                # Handle Google Doc vs Raw Text
                if item['mimeType'] == 'application/vnd.google-apps.document':
                    request = service.files().export_media(fileId=file_id, mimeType='text/plain')
                else:
                    request = service.files().get_media(fileId=file_id)

                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()

                content = fh.getvalue().decode('utf-8')
                parse_content(content)
                processed_files.add(file_key)

        time.sleep(interval)


if __name__ == "__main__":
    target_folder = input("Enter the Google Drive Folder ID to monitor: ")
    refresh_rate = input("Enter polling interval in seconds (t): ")

    try:
        monitor_folder(target_folder, int(refresh_rate))
    except KeyboardInterrupt:
        print("\nStopping monitor...")