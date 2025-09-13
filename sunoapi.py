import asyncio
import time
import datetime
import json

import requests

from config import get_suno_token
import sunoresults as sp

BASE_URL = 'https://api.sunoapi.org/api/v1'
# mock_time_start = time.time()

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
    with open("task_ids.log", "a") as f:
        f.write(f"{log_entry}\n")

    return response.json()

async def wait_for_completion(task_id: str, max_wait_time: int = 600, poll_interval: int = 5) -> dict:

    url = f"{BASE_URL}/generate/record-info?taskId={task_id}"
    headers = {
    "Authorization": f"Bearer {get_suno_token()}"
    }
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        response = requests.get(url, headers=headers)
        results = sp.parse_log_dict(str(response))
        
        if response.status_code != 200:
            return {
                "code": results.get("code"),
                "msg": results.get("msg")
            }

        status = results.get("data", {}).get("status")

        """
        PENDING: Task is waiting to be processed
        TEXT_SUCCESS: Lyrics/text generation completed successfully
        FIRST_SUCCESS: First track generation completed successfully
        SUCCESS: All tracks generated successfully
        CREATE_TASK_FAILED: Failed to create the generation task
        GENERATE_AUDIO_FAILED: Failed to generate music tracks
        CALLBACK_EXCEPTION: Error occurred during callback
        SENSITIVE_WORD_ERROR: Content contains prohibited words
        """
        if status == "SENSITIVE_WORD_ERROR" or \
           status == "CREATE_TASK_FAILED" or \
           status == "GENERATE_AUDIO_FAILED" or \
           status == "CALLBACK_EXCEPTION":
            return {
                "error": {
                    "msg": f"{status}"
                }
            }
        elif status == "TEXT_SUCCESS":
            song_lyrics = {}
            song_lyrics['lyrics'] = results.get("data", {}).get("text", {})
            return song_lyrics
        elif status == "SUCCESS":
            song_ids = []
            tracks = sp.build_tracks(results)
            for track in tracks:
                song_ids.append(track.id)
            
            song_titles = []
            for track in tracks:
                song_titles.append(track.title)
            
            song_audio_urls = []
            for track in tracks:
                song_audio_urls.append(track.audio_url)
            
            song_image_urls = []
            for track in tracks:
                song_image_urls.append(track.image_url)
            
            song_durations = []
            for track in tracks:
                song_durations.append(track.duration)
            # Duration in Minutes and Seconds
            song_durations = [f"{int(d // 60)}m {int(d % 60)}s" if d is not None else "Unknown" for d in song_durations]    
            
            return {
                "song_ids": song_ids,
                "song_titles": song_titles,
                "song_audio_urls": song_audio_urls,
                "song_image_urls": song_image_urls,
                "song_durations": song_durations
            }
        # PENDING or other statuses
        await asyncio.sleep(poll_interval)
    raise Exception('Generation timeout')

def _mock_pending_status_response(task_id: str) -> dict:
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": f"{task_id}",
            "parentMusicId": "",
            "param": "{\"prompt\":\"A calm piano track\",\"style\":\"Classical\",\"title\":\"Peaceful Piano\",\"customMode\":true,\"instrumental\":true,\"model\":\"V3_5\"}",
            "response": None,
            "status": "PENDING",
            "type": "GENERATE",
            "errorCode": None,
            "errorMessage": None
        }
    }

async def get_task_results(task_id: str) -> dict:
    url = f"{BASE_URL}/generate/record-info?taskId={task_id}"
    headers = {
    "Authorization": f"Bearer {get_suno_token()}"
    }
    # ============= MOCK TESTING =================
    # MOCK_WAIT_TIME = 180  
    # elapsed_time = time.time() - mock_time_start
    # mock_pending = elapsed_time <= MOCK_WAIT_TIME
    # if mock_pending:
    #     return _mock_pending_status_response(task_id)
    # ============================================
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        results = response.json()
        # Write as pretty JSON to task_results.log
        if results.get('data', {}).get('status') in ['SUCCESS']:
            status = (results.get('data', {}).get('status') or '').strip().upper()
            if status in {'SUCCESS'}:
                with open("task_results.log", "a") as f:
                    f.write(f"{datetime.datetime.now()}: {task_id} -> {json.dumps(results, indent=4)}\n")
        return results
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"error": {"msg": f"Failed to retrieve task results"}}  # Return an error dict
    
async def boost_style(text: str) -> dict:

    url = f"{BASE_URL}/style/generate"

    payload = {
        "content": f"{text}",
    }

    headers = {
        "Authorization": f"Bearer {get_suno_token()}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        with open("booststyle.log", "a") as f:
            f.write(f"{datetime.datetime.now()}: {text} -> {json.dumps(response.json(), indent=4)}\n")
        result = {
            "task_id": response.json()['data']['taskId'],
            "result": response.json()['data']['result'],
            "creditsRemaining": response.json()['data']['creditsRemaining'],
            "errorCode": response.json()['data']['errorCode'],
            "errorMessage": response.json()['data']['errorMessage']
        }
        return result
    else:
        print(f"Error: {response.status_code} - {response.json().get('msg', 'Unknown error')}")
        return {"error": {"msg": f"Failed to boost style"}}
