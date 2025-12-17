import os
import sys
import subprocess
import json
import time
import random
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.join(current_dir, '../../pipeline_localminio')
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)
from metrics import PerformanceMonitor, print_stats

RESIZE_SCRIPT = os.path.join(pipeline_dir, 'resize.py')
DETECT_SCRIPT = os.path.join(pipeline_dir, 'detect.py')
POSTPROCESS_SCRIPT = os.path.join(pipeline_dir, 'postprocess.py')
ITERATIONS = 30
MIN_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 1200
RANDOM_SEED = 18
RESULTS_FILE = current_dir + "/results_random.json"

def run_pipeline():
    for script in [RESIZE_SCRIPT, DETECT_SCRIPT, POSTPROCESS_SCRIPT]:
        result = subprocess.run([sys.executable, script], cwd=pipeline_dir, capture_output=True, text=True)
        if result.returncode != 0:
            return False
    return True

def generate_random_delays(num, min_d, max_d, seed):
    return [random.Random(seed).uniform(min_d, max_d) for _ in range(num)]

def save_results(latencies, cpu_times, memories, total_time):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio",
        "test_type": "random",
        "iterations": len(latencies),
        "total_time_seconds": total_time,
        "latency_avg_ms": statistics.mean(latencies),
        "latency_std_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "cpu_time_avg_ms": statistics.mean(cpu_times),
        "memory_avg_mb": statistics.mean(memories),
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
    latencies, cpu_times, memories = [], [], []

    print(f"Starte local_minio Random Benchmark ({ITERATIONS} Durchläufe)...")

    start_time = time.time()
    for i in range(ITERATIONS):
        with PerformanceMonitor() as mon:
            success = run_pipeline()
        if success:
            latencies.append(mon.get_duration())
            cpu_times.append(mon.get_cpu_time())
            memories.append(mon.get_memory())
            print(f"Run {i+1}: {mon.get_duration():.2f}ms")
        else:
            print(f"Run {i+1}: FAILED")
        
        if i < ITERATIONS - 1:
            print(f"  -> Delay: {delays[i]:.1f}s")
            time.sleep(delays[i])

    total_time = time.time() - start_time
    if latencies:
        print_stats(latencies, cpu_times, memories)
        save_results(latencies, cpu_times, memories, total_time)

if __name__ == "__main__":
    main()
