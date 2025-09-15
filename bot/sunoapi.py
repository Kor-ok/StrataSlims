import os
import time
import datetime
import json

import requests

from config import get_suno_token, get_log_folder, DEV_MODE

_dev_mode = DEV_MODE

BASE_URL = 'https://api.sunoapi.org/api/v1'
LOG_FOLDER = get_log_folder()

async def get_remaining_credits() -> str:

    url = f"{BASE_URL}/generate/credit"

    headers = {
        "Authorization": f"Bearer {get_suno_token()}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return f"Error: {response.json().get('code', 'Unknown error')}"
    
    credits = response.json()['data']
    return str(credits)

async def generate_music(payload: dict) -> dict:

    url = f"{BASE_URL}/generate"

    headers = {
        "Authorization": f"Bearer {get_suno_token()}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        return {"error": response.json()}
    
    log_entry = {
        "taskId": response.json()['data']['taskId'],
        "created_timestamp": time.time(),
        "payload": payload
    }
    # ======================================================== LOG
    if _dev_mode:
        with open(os.path.join(LOG_FOLDER, "task_ids.log"), "a") as f:
            f.write(f"{log_entry}\n")

    return response.json()

async def get_task_results(task_id: str) -> dict:
    url = f"{BASE_URL}/generate/record-info?taskId={task_id}"
    headers = {
    "Authorization": f"Bearer {get_suno_token()}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        results = response.json()
        # ======================================================== LOG
        if results.get('data', {}).get('status') in ['SUCCESS']:
            status = (results.get('data', {}).get('status') or '').strip().upper()
            if status in {'SUCCESS'}:
                if _dev_mode:
                    with open(os.path.join(LOG_FOLDER, "task_results.log"), "a") as f:
                        f.write(f"{datetime.datetime.now()}: {task_id} -> {json.dumps(results, indent=4)}\n")
        return results
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"error": {"msg": f"Failed to retrieve task results"}}  # Return an error dict
   
async def generate_boosted_style(payload: dict) -> dict:

    url = f"{BASE_URL}/style/generate"

    headers = {
        "Authorization": f"Bearer {get_suno_token()}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        return {"error": response.json()}
    
    log_entry = {
        "taskId": response.json()['data']['taskId'],
        "param": response.json()['data']['param'],
        "result": response.json()['data']['result'],
        "creditsRemaining": response.json()['data']['creditsRemaining'],
        "createTime": response.json()['data']['createTime'],
        "originalPayload": payload
    }
    # ======================================================== LOG
    if _dev_mode:
        with open(os.path.join(LOG_FOLDER, "booststyle.log"), "a") as f:
            f.write(f"{log_entry}\n")

    result = {
        "result": response.json()['data']['result'],
        "creditsRemaining": response.json()['data']['creditsRemaining'],
    }
    return result

__all__ = [
    "get_remaining_credits",
    "generate_music",
    "get_task_results",
    "generate_boosted_style"
]