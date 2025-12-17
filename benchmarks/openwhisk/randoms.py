import subprocess
import json
import time
import random
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
MIN_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 1200
RANDOM_SEED = 18
SIZE = "640"
RESULTS_FILE = current_dir + "/results_random.json"

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

def generate_random_delays(num_delays, min_delay, max_delay, seed):
    rng = random.Random(seed)
    return [rng.uniform(min_delay, max_delay) for _ in range(num_delays)]

def save_results(latencies, total_time):
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "test_type": "random",
        "iterations": len(latencies),
        "total_time_seconds": total_time,
        "latency_avg_ms": statistics.mean(latencies) if latencies else 0,
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
    delays = generate_random_delays(ITERATIONS - 1, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, RANDOM_SEED)
    latencies = []

    print(f"Starte OpenWhisk Benchmark mit zufälligen Delays ({ITERATIONS} Durchläufe)...")
    print(f"Delays zwischen {MIN_DELAY_SECONDS}s und {MAX_DELAY_SECONDS}s")
    
    print("\nWarming up...")
    invoke_openwhisk()

    start_time = time.time()
    
    for i in range(ITERATIONS):
        current_time = time.time() - start_time
        duration, result = invoke_openwhisk()
        
        if duration:
            latencies.append(duration)
            print(f"Run {i+1} (t={current_time:.1f}s): {duration:.2f}ms")
        else:
            print(f"Run {i+1}: FAILED")
        
        if i < ITERATIONS - 1:
            delay = delays[i]
            print(f"  -> Nächster Request in {delay:.1f}s")
            time.sleep(delay)

    total_time = time.time() - start_time
    print(f"\nGesamtzeit: {total_time:.1f}s")
    
    print_stats(latencies)
    save_results(latencies, total_time)

if __name__ == "__main__":
    main()
