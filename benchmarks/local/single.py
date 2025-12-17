import cv2
import numpy as np
import os
import sys
import json
from datetime import datetime

# 1. Den absoluten Pfad zum 'src' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../../pipeline_without')
metrics_dir = os.path.join(current_dir, '../')

# 2. Den Pfad zu Python hinzufügen
sys.path.append(src_dir)
sys.path.append(metrics_dir)

# Importiere deine Module direkt
import resize as resize_mod
import detect as detect_mod
import postprocess as post_mod
from metrics import PerformanceMonitor, print_stats

# Konfiguration
IMAGE_PATH = current_dir + "/../test.jpg"
RESULTS_FILE = current_dir + "/results.json"

def run_pipeline(img):
    # 1. Resize
    h, w, blob = resize_mod.preprocess_image(img)
    
    # 2. Detect
    input_name = detect_mod.input_name
    output_names = detect_mod.output_names
    outputs = detect_mod.session.run(output_names, {input_name: blob})
    detections = outputs[0]
    
    # 3. Postprocess
    img_copy = img.copy() 
    results = post_mod.postprocess(img_copy, h, w, detections)
    return results

def save_results(latency, cpu_time, memory, detections_count):
    """Save results to JSON file, appending to existing results."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local",
        "latency_ms": latency,
        "cpu_time_ms": cpu_time,
        "memory_mb": memory,
        "detections_count": detections_count
    }
    
    # Load existing results or create new list
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

    # Bild einmal laden (IO nicht messen)
    original_img = cv2.imread(IMAGE_PATH)

    print(f"Starte lokale Benchmark (1 Durchlauf)...")

    with PerformanceMonitor() as mon:
        detections = run_pipeline(original_img)
    
    latency = mon.get_duration()
    cpu_time = mon.get_cpu_time()
    memory = mon.get_memory()
    
    print(f"Run : {latency:.2f}ms")
    print(f"Memory Usage: {memory:.2f}MB")
    print(f"Detections: {len(detections)} objects found")
    
    save_results(latency, cpu_time, memory, len(detections))

if __name__ == "__main__":
    main()