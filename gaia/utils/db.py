import redis
import os
import json
from datetime import datetime

redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0
)

def save_result(tool, input_data, output):
    result = {
        'tool': tool,
        'input': input_data,
        'output': output,
        'timestamp': datetime.utcnow().isoformat()
    }
    # Store results with a unique key
    key = f"result:{tool}:{datetime.utcnow().timestamp()}"
    redis_client.set(key, json.dumps(result))