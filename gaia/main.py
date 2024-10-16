# main.py

import os
import time
import threading
from tasks import TASK_NAMES, app  # Importing TASK_NAMES and app from tasks.py
from autoscaler import Autoscaler
from utils.monitoring import get_queue_length
from utils.db import init_db, save_result


def calculate_desired_containers(queue_length):

    MAX_TASKS_PER_CONTAINER = 5
    return (queue_length // MAX_TASKS_PER_CONTAINER) + 1


def monitor_and_scale():
    autoscaler = Autoscaler()
    while True:
        for tool, task_name in TASK_NAMES.items():
            # Assuming only 'llm' tasks require autoscaling
            if tool == "llm":
                queue_length = get_queue_length(tool)
                desired_containers = calculate_desired_containers(queue_length)
                image_name = os.environ.get("DOCKER_IMAGE_LLM", "llm")
                autoscaler.scale_containers(desired_containers, image_name)
        time.sleep(10)  # Adjust the sleep time as needed



def run_test():
    print("Starting GAIA communication test...")

    test_data = "This is a test message from GAIA"
    results = {}

    for tool, task_name in TASK_NAMES.items():
        print(f"Sending task to {tool}...")
        # Sending task to the appropriate queue
        task = app.send_task(task_name, args=[test_data], queue=tool)
        results[tool] = task

    # Collect results
    for tool, task in results.items():
        try:
            result = task.get(timeout=60)  # Adjust timeout as needed
            results[tool] = result
            save_result(tool, test_data, result)
        except Exception as e:
            print(f"Error getting result from {tool}: {str(e)}")
            results[tool] = f"Error: {str(e)}"
            save_result(tool, test_data, f"Error: {str(e)}")

    print("\nTest Results:")
    for tool, result in results.items():
        print(f"{tool}: {result}")

    print("\nGAIA communication test completed.")


if __name__ == "__main__":
    # Wait for RabbitMQ and other services to be ready
    time.sleep(10)
    init_db()

    # Start autoscaling in a separate thread
    threading.Thread(target=monitor_and_scale, daemon=True).start()

    # Run the test
    run_test()
