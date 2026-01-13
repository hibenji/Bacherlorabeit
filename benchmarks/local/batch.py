import cv2
import numpy as np
import os
import sys
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../../pipeline_without')
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(src_dir)
sys.path.append(metrics_dir)

import resize as resize_mod
import detect as detect_mod
import postprocess as post_mod
from metrics import PerformanceMonitor, print_stats

# Konfiguration
IMAGE_PATH = current_dir + "/../test.jpg"
BATCH_SIZE = 50
ITERATIONS = 30
RESULTS_FILE = current_dir + "/results_batch.json"

def run_pipeline(img):
    h, w, blob = resize_mod.preprocess_image(img)
    input_name = detect_mod.input_name
    output_names = detect_mod.output_names
    outputs = detect_mod.session.run(output_names, {input_name: blob})
    detections = outputs[0]
    img_copy = img.copy() 
    results = post_mod.postprocess(img_copy, h, w, detections)
    return results

def process_single_request(image_path, request_id):
    with PerformanceMonitor() as mon:
        img = cv2.imread(image_path)
        if img is None:
             return {'request_id': request_id, 'error': 'Disk IO failed'}
        result = run_pipeline(img)
    return {
        'request_id': request_id,
        'latency': mon.get_duration(),
        'cpu_time': mon.get_cpu_time(),
        'memory': mon.get_memory(),
    }

def run_batch(image_path, batch_size):
    results = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_single_request, image_path, i) for i in range(batch_size)]
        for future in as_completed(futures):
            results.append(future.result())
    return results

def save_results(batch_latencies, all_latencies, all_cpu_times, all_memories):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local",
        "test_type": "batch",
        "batch_size": BATCH_SIZE,
        "iterations": ITERATIONS,
        "batch_latency_avg_ms": statistics.mean(batch_latencies),
        "batch_latency_std_ms": statistics.stdev(batch_latencies) if len(batch_latencies) > 1 else 0,
        "request_latency_avg_ms": statistics.mean(all_latencies),
        "throughput_rps": BATCH_SIZE / (statistics.mean(batch_latencies) / 1000),
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
    if not os.path.exists(IMAGE_PATH):
        print(f"Fehler: Bild {IMAGE_PATH} nicht gefunden.")
        return

    original_img = cv2.imread(IMAGE_PATH)
    
    all_latencies = []
    all_cpu_times = []
    all_memories = []
    batch_latencies = []

    print(f"Starte lokale Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")

    print("Warming up...")
    warmup_img = cv2.imread(IMAGE_PATH)
    if warmup_img is not None:
        run_pipeline(warmup_img)

    for batch_num in range(ITERATIONS):
        print(f"\n=== Batch {batch_num+1}/{ITERATIONS} ===")
        
        with PerformanceMonitor() as batch_mon:
            batch_results = run_batch(IMAGE_PATH, BATCH_SIZE)
        
        batch_duration = batch_mon.get_duration()
        batch_latencies.append(batch_duration)
        
        for result in batch_results:
            if 'error' in result:
                continue
            all_latencies.append(result['latency'])
            all_cpu_times.append(result['cpu_time'])
            all_memories.append(result['memory'])
        
        print(f"Batch-Gesamtzeit: {batch_duration:.2f}ms")
        print(f"Durchsatz: {BATCH_SIZE / (batch_duration / 1000):.2f} requests/sec")

    print("\n" + "="*60)
    print("BATCH-STATISTIKEN:")
    print("="*60)
    print(f"Durchschnittliche Batch-Zeit: {np.mean(batch_latencies):.2f}ms")
    print(f"Durchschnittlicher Durchsatz: {BATCH_SIZE / (np.mean(batch_latencies) / 1000):.2f} requests/sec")
    
    save_results(batch_latencies, all_latencies, all_cpu_times, all_memories)

if __name__ == "__main__":
    main()
