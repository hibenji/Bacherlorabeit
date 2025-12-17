import subprocess
import json
import time
import statistics
import os
import sys
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')
sys.path.append(metrics_dir)
from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"
ITERATIONS = 30
RESULTS_FILE = current_dir + "/results_stream.json"

def invoke_openwhisk():
    start = time.time()
    cmd = [
        "wsk", "action", "invoke", ACTION_NAME,
        "--result",
        "--param", "imageKey", IMAGE_KEY,
        "--param", "size", "640"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        end = time.time()
        
        if result.returncode != 0:
            return None, None

        client_latency = (end - start) * 1000
        return client_latency, json.loads(result.stdout)
        
    except Exception as e:
        print(f"Exception: {e}")
        return None, None

def save_results(latencies):
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "test_type": "stream",
        "iterations": len(latencies),
        "latency_avg_ms": statistics.mean(latencies),
        "latency_std_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
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
    latencies = []
    
    print(f"Starte OpenWhisk Stream Benchmark ({ITERATIONS} Durchläufe)...")

    for i in range(ITERATIONS):
        duration, result = invoke_openwhisk()
        
        if duration:
            latencies.append(duration)
            print(f"Run {i+1}: {duration:.2f}ms")
        else:
            print(f"Run {i+1}: FAILED")

    print_stats(latencies)
    save_results(latencies)

if __name__ == "__main__":
    main()