import os
import datetime
import json

import requests

from config import get_suno_token, get_log_folder, DEV_MODE

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

async def generate_music(payload: dict) -> tuple [dict, dict]: # returns (response, log_entry)

    url = f"{BASE_URL}/generate"

    headers = {
        "Authorization": f"Bearer {get_suno_token()}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        return {"error": response.json()}, {"suno_fault": response}
    
    log_entry = {
        "taskId": response.json()['data']['taskId'],
        "created_timestamp": datetime.datetime.now().isoformat(),
        "request": payload
    }

    return response.json(), log_entry

async def get_task_results(task_id: str) -> tuple[dict, dict]:  # returns (results, log_entry)
    """Fetch task results and return both API payload and a structured log entry.

    The second tuple element (log_entry) is always provided with common fields to
    simplify downstream logging logic.
    """
    url = f"{BASE_URL}/generate/record-info?taskId={task_id}"
    headers = {
        "Authorization": f"Bearer {get_suno_token()}"
    }

    response = requests.get(url, headers=headers)
    timestamp = datetime.datetime.now().isoformat()

    if response.status_code == 200:
        results = response.json()
        status = (results.get('data', {}).get('status') or '').strip().upper()
        task_id_val = results.get('data', {}).get('taskId') or task_id
        log_entry = {
            "taskId": task_id_val,
            "status": status,
            "timestamp": timestamp
        }
        # Dev-only detailed persistence
        if DEV_MODE and status == 'SUCCESS':
            try:
                with open(os.path.join(LOG_FOLDER, "task_results.log"), "a", encoding="utf-8") as f:
                    f.write(f"{timestamp}: {task_id_val} -> {json.dumps(results, indent=4)}\n")
            except Exception:
                pass
        return results, log_entry
    else:
        if DEV_MODE:
            print(f"Error: {response.status_code} - {response.text}")
        log_entry = {
            "taskId": task_id,
            "status": 'ERROR',
            "timestamp": timestamp,
            "httpStatus": response.status_code
        }
        return {"error": {"msg": "Failed to retrieve task results", "status_code": response.status_code}}, log_entry
   
async def generate_boosted_style(payload: dict) -> tuple [dict, dict]: # returns (result, log_entry)

    url = f"{BASE_URL}/style/generate"

    headers = {
        "Authorization": f"Bearer {get_suno_token()}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        return {"error": response.json()}, {"suno_fault": response}
    
    # Convert createTime (example=1758165377153) to human-readable ISO 8601
    if 'data' in response.json() and 'createTime' in response.json()['data']:
        try:
            ts = int(response.json()['data']['createTime']) / 1000.0
            iso_time = datetime.datetime.fromtimestamp(ts).isoformat()
            response.json()['data']['createTime'] = iso_time
        except Exception:
            pass  # Leave as-is if conversion fails
    
    log_entry = {
        "taskId": response.json()['data']['taskId'],
        "originalStyle": response.json()['data']['param'],
        "boostedStyle": response.json()['data']['result'],
        "createTime": response.json()['data']['createTime']
    }

    result = {
        "result": response.json()['data']['result'],
        "creditsRemaining": response.json()['data']['creditsRemaining'],
    }
    return result, log_entry

__all__ = [
    "get_remaining_credits",
    "generate_music",
    "get_task_results",
    "generate_boosted_style"
]