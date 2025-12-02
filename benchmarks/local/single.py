import cv2
import numpy as np
import os
import sys

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

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"Fehler: Bild {IMAGE_PATH} nicht gefunden.")
        return

    # Bild einmal laden (IO nicht messen)
    original_img = cv2.imread(IMAGE_PATH)
    
    latencies = []
    cpu_times = []
    memories = []

    print(f"Starte lokale Benchmark (1 Durchlauf)...")

    with PerformanceMonitor() as mon:
        _ = run_pipeline(original_img)
    
    latencies.append(mon.get_duration())
    cpu_times.append(mon.get_cpu_time())
    memories.append(mon.get_memory())
    
    print(f"Run : {mon.get_duration():.2f}ms")
    print(f"Memory Usage: {mon.get_memory():.2f}MB")

if __name__ == "__main__":
    main()