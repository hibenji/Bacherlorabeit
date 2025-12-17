import cv2
import numpy as np
import os
import sys
import time
import random
import json
from datetime import datetime

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
ITERATIONS = 30
MIN_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 1200
RANDOM_SEED = 18
RESULTS_FILE = current_dir + "/results_random.json"

def run_pipeline(img):
    h, w, blob = resize_mod.preprocess_image(img)
    input_name = detect_mod.input_name
    output_names = detect_mod.output_names
    outputs = detect_mod.session.run(output_names, {input_name: blob})
    detections = outputs[0]
    img_copy = img.copy() 
    results = post_mod.postprocess(img_copy, h, w, detections)
    return results

def generate_random_delays(num_delays, min_delay, max_delay, seed):
    rng = random.Random(seed)
    delays = [rng.uniform(min_delay, max_delay) for _ in range(num_delays)]
    return delays

def save_results(latencies, cpu_times, memories, total_time):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local",
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
    if not os.path.exists(IMAGE_PATH):
        print(f"Fehler: Bild {IMAGE_PATH} nicht gefunden.")
        return

    original_img = cv2.imread(IMAGE_PATH)
    delays = generate_random_delays(ITERATIONS - 1, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, RANDOM_SEED)
    
    latencies = []
    cpu_times = []
    memories = []

    print(f"Starte lokale Benchmark mit zufälligen Delays ({ITERATIONS} Durchläufe)...")
    print(f"Delays zwischen {MIN_DELAY_SECONDS}s und {MAX_DELAY_SECONDS}s")
    
    print("\nWarming up...")
    run_pipeline(original_img)

    start_time = time.time()
    
    for i in range(ITERATIONS):
        current_time = time.time() - start_time
        
        with PerformanceMonitor() as mon:
            _ = run_pipeline(original_img)
        
        latencies.append(mon.get_duration())
        cpu_times.append(mon.get_cpu_time())
        memories.append(mon.get_memory())
        
        print(f"Run {i+1} (t={current_time:.1f}s): {mon.get_duration():.2f}ms")
        
        if i < ITERATIONS - 1:
            delay = delays[i]
            print(f"  -> Nächster Request in {delay:.1f}s")
            time.sleep(delay)

    total_time = time.time() - start_time
    print(f"\nGesamtzeit: {total_time:.1f}s")
    
    print_stats(latencies, cpu_times, memories)
    save_results(latencies, cpu_times, memories, total_time)

if __name__ == "__main__":
    main()
