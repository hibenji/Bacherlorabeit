import cv2
import numpy as np
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 1. Den absoluten Pfad zum 'src' Ordner finden
# Wir gehen vom aktuellen Datei-Pfad (benchmark_local.py) einen Ordner hoch (..) und dann in 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../../pipeline_without')
metrics_dir = os.path.join(current_dir, '../')

# 2. Den Pfad zu Python hinzufügen
sys.path.append(src_dir)
sys.path.append(metrics_dir)

# Importiere deine Module direkt
import resize as resize_mod      #
import detect as detect_mod      #
import postprocess as post_mod   #
from metrics import PerformanceMonitor, print_stats

# Konfiguration
IMAGE_PATH = current_dir + "/../test.jpg"  # Lokaler Pfad zum Testbild
BATCH_SIZE = 50  # Anzahl gleichzeitiger Requests
ITERATIONS = 30  # Anzahl der Batch-Durchläufe

def run_pipeline(img):
    # 1. Resize
    h, w, blob = resize_mod.preprocess_image(img)
    
    # 2. Detect
    # Wir nutzen die session, die beim Import von detect.py erstellt wurde
    input_name = detect_mod.input_name
    output_names = detect_mod.output_names
    outputs = detect_mod.session.run(output_names, {input_name: blob})
    detections = outputs[0]
    
    # 3. Postprocess
    # Achtung: Postprocess modifiziert das Bild für Boxen, 
    # daher hier kopieren, um Caching-Effekte zu vermeiden
    img_copy = img.copy() 
    results = post_mod.postprocess(img_copy, h, w, detections)
    return results

def process_single_request(img, request_id):
    """Verarbeitet eine einzelne Anfrage und gibt die Latenz zurück"""
    with PerformanceMonitor() as mon:
        result = run_pipeline(img)
    
    return {
        'request_id': request_id,
        'latency': mon.get_duration(),
        'cpu_time': mon.get_cpu_time(),
        'memory': mon.get_memory(),
        'result': result
    }

def run_batch(img, batch_size):
    """Führt einen Batch von Requests gleichzeitig aus"""
    results = []
    
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        # Alle Requests gleichzeitig starten
        futures = [executor.submit(process_single_request, img, i) for i in range(batch_size)]
        
        # Warte auf alle Ergebnisse
        for future in as_completed(futures):
            results.append(future.result())
    
    return results

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"Fehler: Bild {IMAGE_PATH} nicht gefunden.")
        return

    # Bild einmal laden (IO nicht messen)
    original_img = cv2.imread(IMAGE_PATH)
    
    all_latencies = []
    all_cpu_times = []
    all_memories = []
    batch_latencies = []  # Zeit für kompletten Batch

    print(f"Starte lokale Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")

    # Warmup (damit ONNX Session warm ist)
    print("Warming up...")
    run_pipeline(original_img)

    for batch_num in range(ITERATIONS):
        print(f"\n=== Batch {batch_num+1}/{ITERATIONS} ===")
        
        # Messe die Zeit für den gesamten Batch
        with PerformanceMonitor() as batch_mon:
            batch_results = run_batch(original_img, BATCH_SIZE)
        
        batch_duration = batch_mon.get_duration()
        batch_latencies.append(batch_duration)
        
        # Sammle individuelle Request-Metriken
        for result in batch_results:
            all_latencies.append(result['latency'])
            all_cpu_times.append(result['cpu_time'])
            all_memories.append(result['memory'])
        
        print(f"Batch-Gesamtzeit: {batch_duration:.2f}ms")
        print(f"Durchschnittliche Request-Latenz: {np.mean([r['latency'] for r in batch_results]):.2f}ms")
        print(f"Durchsatz: {BATCH_SIZE / (batch_duration / 1000):.2f} requests/sec")

    print("\n" + "="*60)
    print("EINZELNE REQUEST-STATISTIKEN:")
    print("="*60)
    print_stats(all_latencies, all_cpu_times, all_memories)
    
    print("\n" + "="*60)
    print("BATCH-STATISTIKEN (Gesamtzeit pro Batch):")
    print("="*60)
    print(f"Durchschnittliche Batch-Zeit: {np.mean(batch_latencies):.2f}ms")
    print(f"Median Batch-Zeit: {np.median(batch_latencies):.2f}ms")
    print(f"Min Batch-Zeit: {np.min(batch_latencies):.2f}ms")
    print(f"Max Batch-Zeit: {np.max(batch_latencies):.2f}ms")
    print(f"Durchschnittlicher Durchsatz: {BATCH_SIZE / (np.mean(batch_latencies) / 1000):.2f} requests/sec")

if __name__ == "__main__":
    main()
