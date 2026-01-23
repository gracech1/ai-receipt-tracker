import requests
import time
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv("TABSCANNER_API_KEY")

# API Configuration in .env
PROCESS_ENDPOINT = "https://api.tabscanner.com/api/2/process"
RESULT_ENDPOINT_BASE = "https://api.tabscanner.com/api/result/"

def upload_receipt(file_path):

    """
    Upload a receipt image to Tabscanner for processing.
    Returns a token to poll for results.
    """

    with open(file_path, 'rb') as file:
        response = requests.post(
            PROCESS_ENDPOINT,
            headers={"apikey": API_KEY},
            files={"file": file}
        )

    if response.status_code == 200:
        token = response.json().get("token")
        print(f"Token: {token}")
        return token
    else:
        print(f"Error uploading receipt: {response.status_code}, {response.text}")
        return None

def poll_for_result(token):

    """
    Poll Tabscanner's result endpoint using the token until processing is complete.
    Returns the extracted data as a JSON object.
    """

    polling_url = f"{RESULT_ENDPOINT_BASE}{token}"

    while True:

        response = requests.get(polling_url, headers={"apikey": API_KEY})

        if response.status_code == 200:

            result_data = response.json()
            status = result_data.get("status")

            if status == "done":
                print("Processing complete!")
                return result_data.get("result")
            elif status == "pending":
                print("Processing... retrying in 1 second.")
                time.sleep(1)
            else:
                print(f"Unexpected status: {status}")
                return None
        else:
            print(f"Error polling for result: {response.status_code}, {response.text}")
            return None

def process_receipt(file_path):

    """
    Upload a receipt and retrieve its processed data.
    """

    print("Uploading receipt...")
    token = upload_receipt(file_path)

    if not token:
        print("Failed to start receipt processing.")
        return None

    print("Polling for results...")
    result = poll_for_result(token)

    if result:
        print("Receipt Data Retrieved:")
        print(result)
        return result
    else:
        print("Failed to retrieve receipt data.")