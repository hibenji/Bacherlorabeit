import os
import sys
import subprocess
import json
from datetime import datetime

# Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.join(current_dir, '../../pipeline_localminio')
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)
from metrics import PerformanceMonitor, print_stats

# Pipeline scripts
RESIZE_SCRIPT = os.path.join(pipeline_dir, 'resize.py')
DETECT_SCRIPT = os.path.join(pipeline_dir, 'detect.py')
POSTPROCESS_SCRIPT = os.path.join(pipeline_dir, 'postprocess.py')
RESULTS_FILE = current_dir + "/results_single.json"

def run_pipeline():
    """
    Run the full pipeline by executing each stage script.
    Each script reads from and writes to MinIO.
    """
    detections_count = 0
    
    # Stage 1: Resize
    result = subprocess.run(
        [sys.executable, RESIZE_SCRIPT],
        cwd=pipeline_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Resize failed: {result.stderr}")
        return None
    print(f"[Resize] {result.stdout.strip()}")
    
    # Stage 2: Detect
    result = subprocess.run(
        [sys.executable, DETECT_SCRIPT],
        cwd=pipeline_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Detect failed: {result.stderr}")
        return None
    print(f"[Detect] {result.stdout.strip()}")
    
    # Stage 3: Postprocess
    result = subprocess.run(
        [sys.executable, POSTPROCESS_SCRIPT],
        cwd=pipeline_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Postprocess failed: {result.stderr}")
        return None
    print(f"[Postprocess] {result.stdout.strip()}")
    
    # Try to extract detections count from output
    try:
        if "Final results:" in result.stdout:
            import re
            matches = re.findall(r"'class_id':", result.stdout)
            detections_count = len(matches)
    except:
        pass
    
    return detections_count

def save_results(latency, cpu_time, memory, detections_count):
    """Save results to JSON file, appending to existing results."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio",
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
    print(f"Starte lokale MinIO Benchmark (1 Durchlauf)...")
    print(f"Pipeline scripts from: {pipeline_dir}")
    print()

    with PerformanceMonitor() as mon:
        detections_count = run_pipeline()
    
    if detections_count is not None:
        latency = mon.get_duration()
        cpu_time = mon.get_cpu_time()
        memory = mon.get_memory()
        
        print()
        print(f"Run : {latency:.2f}ms")
        print(f"Memory Usage: {memory:.2f}MB")
        
        save_results(latency, cpu_time, memory, detections_count)
    else:
        print("Pipeline failed!")

if __name__ == "__main__":
    main()
