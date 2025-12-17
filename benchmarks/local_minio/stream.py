import os
import sys
import subprocess
import json
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
RESULTS_FILE = current_dir + "/results_stream.json"

def run_pipeline():
    for script in [RESIZE_SCRIPT, DETECT_SCRIPT, POSTPROCESS_SCRIPT]:
        result = subprocess.run([sys.executable, script], cwd=pipeline_dir, capture_output=True, text=True)
        if result.returncode != 0:
            return False
    return True

def save_results(latencies, cpu_times, memories):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio",
        "test_type": "stream",
        "iterations": len(latencies),
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
    latencies, cpu_times, memories = [], [], []
    print(f"Starte local_minio Stream Benchmark ({ITERATIONS} Durchläufe)...")

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

    if latencies:
        print_stats(latencies, cpu_times, memories)
        save_results(latencies, cpu_times, memories)

if __name__ == "__main__":
    main()
