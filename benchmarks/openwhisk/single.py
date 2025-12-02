import subprocess
import json
import time
import os
import sys

# 1. Den absoluten Pfad zum 'metrics' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)

from metrics import PerformanceMonitor, print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"  # Pfad im MinIO Bucket, nicht lokal!
SIZE = "640"


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

        # Try parse JSON result, otherwise return raw stdout
        try:
            parsed = json.loads(result.stdout)
        except Exception:
            parsed = result.stdout

        return client_latency, parsed

    except Exception as e:
        print(f"Exception: {e}")
        return None, None


def main():
    print(f"Starte OpenWhisk Benchmark (1 Durchlauf)...")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")

    latencies = []
    cpu_times = []
    memories = []

    with PerformanceMonitor() as mon:
        duration, result = invoke_openwhisk()

    if duration:
        latencies.append(mon.get_duration())
        cpu_times.append(mon.get_cpu_time())
        memories.append(mon.get_memory())

        print(f"Run : {duration:.2f}ms (Round-Trip-Time)")
        print(f"Memory Usage: {mon.get_memory():.2f}MB")
        print(f"CPU Time: {mon.get_cpu_time():.2f}ms")
    else:
        print("Run : FAILED")


if __name__ == "__main__":
    main()
