import subprocess
import json
import time
import os
import sys
from datetime import datetime

# 1. Den absoluten Pfad zum 'metrics' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)

from metrics import PerformanceMonitor, print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"
SIZE = "640"
RESULTS_FILE = current_dir + "/results.json"


def invoke_openwhisk(action_name=ACTION_NAME, image_key=IMAGE_KEY, size=SIZE):
    start = time.time()

    cmd = [
        "wsk", "action", "invoke", action_name,
        "--result",
        "--param", "imageKey", image_key,
        "--param", "size", size
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        end = time.time()

        if result.returncode != 0:
            print("Error invoking action:", result.stderr)
            return None, None

        client_latency = (end - start) * 1000

        try:
            parsed = json.loads(result.stdout)
        except Exception:
            parsed = result.stdout

        return client_latency, parsed

    except Exception as e:
        print(f"Exception: {e}")
        return None, None


def save_results(latency, cpu_time, memory, detections_count):
    """Save results to JSON file, appending to existing results."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "latency_ms": latency,
        "cpu_time_ms": cpu_time,
        "memory_mb": memory,
        "detections_count": detections_count
    }
    
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
    else:
        results = []
    
    results.append(result)
    
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {RESULTS_FILE}")


def main():
    print(f"Starte OpenWhisk Benchmark (1 Durchlauf)...")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")

    with PerformanceMonitor() as mon:
        duration, result = invoke_openwhisk()

    if duration:
        latency = mon.get_duration()
        cpu_time = mon.get_cpu_time()
        memory = mon.get_memory()
        
        # Try to get detections count from result
        detections_count = 0
        if isinstance(result, dict) and "results" in result:
            detections_count = len(result.get("results", []))
        elif isinstance(result, list):
            detections_count = len(result)

        print(f"Run : {duration:.2f}ms (Round-Trip-Time)")
        print(f"Memory Usage: {memory:.2f}MB")
        print(f"CPU Time: {cpu_time:.2f}ms")
        
        save_results(latency, cpu_time, memory, detections_count)
    else:
        print("Run : FAILED")


if __name__ == "__main__":
    main()
