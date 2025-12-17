import os
import sys
import subprocess
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.join(current_dir, '../../pipeline_localminio')
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)
from metrics import PerformanceMonitor, print_stats

RESIZE_SCRIPT = os.path.join(pipeline_dir, 'resize.py')
DETECT_SCRIPT = os.path.join(pipeline_dir, 'detect.py')
POSTPROCESS_SCRIPT = os.path.join(pipeline_dir, 'postprocess.py')
BATCH_SIZE = 5
ITERATIONS = 10
RESULTS_FILE = current_dir + "/results_batch.json"

def run_pipeline():
    for script in [RESIZE_SCRIPT, DETECT_SCRIPT, POSTPROCESS_SCRIPT]:
        result = subprocess.run([sys.executable, script], cwd=pipeline_dir, capture_output=True, text=True)
        if result.returncode != 0:
            return False
    return True

def process_single_request(request_id):
    with PerformanceMonitor() as mon:
        success = run_pipeline()
    return {'request_id': request_id, 'latency': mon.get_duration() if success else None, 
            'cpu_time': mon.get_cpu_time(), 'memory': mon.get_memory()}

def run_batch(batch_size):
    results = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_single_request, i) for i in range(batch_size)]
        for future in as_completed(futures):
            results.append(future.result())
    return results

def save_results(batch_latencies, all_latencies, all_cpu_times, all_memories):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio",
        "test_type": "batch",
        "batch_size": BATCH_SIZE,
        "iterations": ITERATIONS,
        "batch_latency_avg_ms": statistics.mean(batch_latencies),
        "batch_latency_std_ms": statistics.stdev(batch_latencies) if len(batch_latencies) > 1 else 0,
        "request_latency_avg_ms": statistics.mean(all_latencies) if all_latencies else 0,
        "throughput_rps": BATCH_SIZE / (statistics.mean(batch_latencies) / 1000) if batch_latencies else 0,
        "cpu_time_avg_ms": statistics.mean(all_cpu_times),
        "memory_avg_mb": statistics.mean(all_memories),
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
    all_latencies, all_cpu_times, all_memories, batch_latencies = [], [], [], []

    print(f"Starte local_minio Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")

    for batch_num in range(ITERATIONS):
        print(f"\n=== Batch {batch_num+1}/{ITERATIONS} ===")
        with PerformanceMonitor() as batch_mon:
            batch_results = run_batch(BATCH_SIZE)
        batch_latencies.append(batch_mon.get_duration())
        for r in batch_results:
            if r['latency']:
                all_latencies.append(r['latency'])
            all_cpu_times.append(r['cpu_time'])
            all_memories.append(r['memory'])
        print(f"Batch-Zeit: {batch_mon.get_duration():.2f}ms")

    save_results(batch_latencies, all_latencies, all_cpu_times, all_memories)

if __name__ == "__main__":
    main()
