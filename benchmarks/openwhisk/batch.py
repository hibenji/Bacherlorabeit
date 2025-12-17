import subprocess
import json
import time
import statistics
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')
sys.path.append(metrics_dir)
from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"
BATCH_SIZE = 3
ITERATIONS = 10
SIZE = "640"
RESULTS_FILE = current_dir + "/results_batch.json"

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

def process_single_invocation(request_id):
    latency, result = invoke_openwhisk()
    return {'request_id': request_id, 'latency': latency}

def run_batch(batch_size):
    results = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_single_invocation, i) for i in range(batch_size)]
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                print(f"Invocation raised exception: {e}")
    return results

def save_results(batch_latencies, latencies):
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "test_type": "batch",
        "batch_size": BATCH_SIZE,
        "iterations": ITERATIONS,
        "batch_latency_avg_ms": statistics.mean(batch_latencies),
        "batch_latency_std_ms": statistics.stdev(batch_latencies) if len(batch_latencies) > 1 else 0,
        "request_latency_avg_ms": statistics.mean(latencies) if latencies else 0,
        "throughput_rps": BATCH_SIZE / (statistics.mean(batch_latencies) / 1000) if batch_latencies else 0,
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
    print(f"Starte OpenWhisk Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")

    latencies = []
    batch_latencies = []

    for i in range(ITERATIONS):
        print(f"\n=== Batch {i+1}/{ITERATIONS} ===")

        start_batch = time.time()
        batch_results = run_batch(BATCH_SIZE)
        end_batch = time.time()

        batch_duration = (end_batch - start_batch) * 1000
        batch_latencies.append(batch_duration)

        successful = [r for r in batch_results if r.get('latency') is not None]
        for r in successful:
            latencies.append(r['latency'])

        throughput = (len(successful) / (batch_duration / 1000)) if batch_duration > 0 else 0
        print(f"Batch-Gesamtzeit: {batch_duration:.2f}ms")
        print(f"Durchsatz: {throughput:.2f} requests/sec")

    print("\n" + "="*60)
    print("BATCH-STATISTIKEN:")
    print("="*60)
    if batch_latencies:
        print(f"Durchschnittliche Batch-Zeit: {statistics.mean(batch_latencies):.2f}ms")
        
    save_results(batch_latencies, latencies)

if __name__ == "__main__":
    main()
