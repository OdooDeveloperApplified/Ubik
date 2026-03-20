import json
import os
import requests
import logging
from google.oauth2 import service_account
import google.auth.transport.requests

_logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, 'ubik-connect-firebase-adminsdk-fbsvc-a1bdaa8fe2.json')

SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
PROJECT_ID = "ubik-connect"


def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        JSON_FILE, scopes=SCOPES
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


def send_fcm_notification(device_token, title, body):
    """Send push notification to a device token"""

    access_token = get_access_token()

    url = f'https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; UTF-8',
    }

    message = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body,
            }
        }
    }

    response = requests.post(url, headers=headers, json=message)

    if response.status_code == 200:
        _logger.info(f"FCM sent to token {device_token}")
        return response.json()
    else:
        _logger.error(f"FCM Error: {response.status_code} - {response.text}")
        return None