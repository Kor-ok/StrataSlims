import random
import time
import datetime
import json
import asyncio
from typing import Optional

BASE_URL = 'https://api.sunoapi.org/api/v1'
mock_time_start = time.time()

async def send_mock_payload(payload: dict) -> dict:
    # This function simulates sending a payload to an API endpoint
    # and returns a mock response for testing purposes.
    print("Sending payload to mock endpoint...")
    print(payload)
    # Simulate a response
    hash = random.getrandbits(128)
    mock_task_id = "%032x" % hash
    mock_response = {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": f"{mock_task_id}"
        }
    }
    # create the mock log with the taskid and payload in a json structure into the log file
    log_entry = {
        "taskId": mock_task_id,
        "created_timestamp": datetime.datetime.now().isoformat(),
        "payload": payload
    }
    
    with open("task_ids.log", "a") as f:
        f.write(f"{json.dumps(log_entry)}\n")

    return mock_response

async def mock_wait_for_completion(task_id: str, max_wait_time: int = 600, poll_interval: int = 30) -> dict:
    """Non-blocking mock poll loop using asyncio.sleep.

    Returns the inner response dict when SUCCESS.
    Raises Exception on FAILED or timeout.
    """
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        status = mock_get_task_status(task_id)
        data = status.get('data') or {}
        st = data.get('status')
        if st == 'SUCCESS':
            return data['response']
        if st == 'FAILED':
            raise Exception(f"Generation failed: {data.get('errorMessage')}")
        await asyncio.sleep(poll_interval)
    raise Exception('Generation timeout')

def _generate_mock_status_response(task_id: str, pending: bool = True) -> dict:
    if pending:
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
    else:
        hash = random.getrandbits(128)
        mock_suno_data_id = "%032x" % hash
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "taskId": f"{task_id}",
                "parentMusicId": "",
                "param": "{\"prompt\":\"A calm piano track\",\"style\":\"Classical\",\"title\":\"Peaceful Piano\",\"customMode\":true,\"instrumental\":true,\"model\":\"V3_5\"}",
                "response": {
                    "taskId": f"{task_id}",
                    "sunoData": [
                        {
                            "id": f"{mock_suno_data_id}",
                            "audioUrl": "https://example.cn/****.mp3",
                            "streamAudioUrl": "https://example.cn/****",
                            "imageUrl": "https://example.cn/****.jpeg",
                            "prompt": "[Verse] 夜晚城市 灯火辉煌",
                            "modelName": "chirp-v3-5",
                            "title": "钢铁侠",
                            "tags": "electrifying, rock",
                            "createTime": "2025-01-01 00:00:00",
                            "duration": 198.44
                        }
                    ]
                },
                "status": "SUCCESS",
                "type": "GENERATE",
                "errorCode": None,
                "errorMessage": None
            }
        }

def mock_get_task_status(task_id: str) -> dict:
    # Determine pending vs success based on elapsed wall time since global start.
    MOCK_WAIT_TIME = 400  
    elapsed_time = time.time() - mock_time_start
    mock_pending = elapsed_time <= MOCK_WAIT_TIME

    # Look for task id in log JSON lines
    found = False
    try:
        with open("task_ids.log", "r") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get('taskId') == task_id:
                    found = True
                    break
    except FileNotFoundError:
        pass

    if not found:
        return {"code": 404, "msg": "Task not found", "data": {}}
    return _generate_mock_status_response(task_id, pending=mock_pending)

async def get_remaining_credits() -> str:
    # Simulate fetching remaining credits
    credits = random.randint(0, 100)
    # Simulate a delay
    await asyncio.sleep(1)
    return str(credits)

async def get_credits_resilient(
	attempts: int = 3,
	timeout_seconds: float = 20.0,
	backoff_seconds: float = 0.5,
	fallback: str = "unknown",
) -> str:
	async def _with_timeout():
		return await asyncio.wait_for(get_remaining_credits(), timeout=timeout_seconds)

	last_err: Optional[BaseException] = None
	for i in range(attempts):
		try:
			return str(await _with_timeout())
		except Exception as e:
			last_err = e
			if i < attempts - 1:
				# exponential backoff between attempts
				await asyncio.sleep(backoff_seconds * (2 ** i))
	# Log best-effort and return fallback
	try:
		import logging
		logging.getLogger(__name__).warning(
			"get_remaining_credits failed after %s attempts: %s", attempts, last_err
		)
	except Exception:
		pass
	return fallback