import requests
import time
import datetime
import json

from config import get_suno_token

BASE_URL = 'https://api.sunoapi.org/api/v1'

def get_task_results(task_id: str) -> None:
    url = f"{BASE_URL}/generate/record-info?taskId={task_id}"
    headers = {
    "Authorization": f"Bearer {get_suno_token()}"
    }
    response = requests.get(url, headers=headers)
    task_results = response.json()
    if response.status_code == 200:
        # Write as pretty JSON to task_results.log
        with open("task_results.log", "a") as f:
            f.write(f"{datetime.datetime.now()}: {task_id} -> {json.dumps(task_results, indent=4)}\n")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    results = {
        "task_id": task_results["data"]["taskId"],
        "song_title_1": task_results["data"]["response"]["sunoData"][0]["title"],
        "song_title_2": task_results["data"]["response"]["sunoData"][1]["title"],
        "song_image_url_1": task_results["data"]["response"]["sunoData"][0]["imageUrl"],
        "song_image_url_2": task_results["data"]["response"]["sunoData"][1]["imageUrl"],
        "song_audio_url_1": task_results["data"]["response"]["sunoData"][0]["audioUrl"],
        "song_audio_url_2": task_results["data"]["response"]["sunoData"][1]["audioUrl"]
    }

    print(f"Song Title 1: {results['song_title_1']}")
    print(f"Song Title 2: {results['song_title_2']}")
    print(f"Song Image URL 1: {results['song_image_url_1']}")
    print(f"Song Image URL 2: {results['song_image_url_2']}")
    print(f"Song Audio URL 1: {results['song_audio_url_1']}")
    print(f"Song Audio URL 2: {results['song_audio_url_2']}")

def boost_style(text: str) -> None:
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
        print("Boosted style response:")
        print(json.dumps(response.json(), indent=4))
    else:
        print(f"Error: {response.status_code} - {response.json().get('msg', 'Unknown error')}")
        
        
# style_text = "Electro-pop with a dash of retro chipwave"

# boost_style(style_text)
