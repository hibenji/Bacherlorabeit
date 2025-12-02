import cv2
import numpy as np
import os
import sys
import time
import random as random

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
ITERATIONS = 30
MIN_DELAY_SECONDS = 60  # 1 minute
MAX_DELAY_SECONDS = 1200  # 20 minutes
RANDOM_SEED = 18  # Für reproduzierbare Randomness

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

def generate_random_delays(num_delays, min_delay, max_delay, seed):
    """
    Generiert eine Liste von zufälligen Verzögerungen in Sekunden.
    Die Delays sind reproduzierbar dank des Seeds.
    """
    rng = random.Random(seed)
    delays = [rng.uniform(min_delay, max_delay) for _ in range(num_delays)]
    return delays

def main():
    if not os.path.exists(IMAGE_PATH):
        print(f"Fehler: Bild {IMAGE_PATH} nicht gefunden.")
        return

    # Bild einmal laden (IO nicht messen)
    original_img = cv2.imread(IMAGE_PATH)
    
    # Generiere die vordefinierten zufälligen Delays
    delays = generate_random_delays(ITERATIONS - 1, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, RANDOM_SEED)
    
    latencies = []
    cpu_times = []
    memories = []
    timestamps = []

    print(f"Starte lokale Benchmark mit zufälligen Delays ({ITERATIONS} Durchläufe)...")
    print(f"Delays zwischen {MIN_DELAY_SECONDS}s ({MIN_DELAY_SECONDS/60:.1f}min) und {MAX_DELAY_SECONDS}s ({MAX_DELAY_SECONDS/60:.1f}min)")
    print(f"Random Seed: {RANDOM_SEED} (für Reproduzierbarkeit)")
    
    # Warmup (damit ONNX Session warm ist)
    print("\nWarming up...")
    run_pipeline(original_img)

    start_time = time.time()
    
    for i in range(ITERATIONS):
        current_time = time.time() - start_time
        timestamps.append(current_time)
        
        with PerformanceMonitor() as mon:
            _ = run_pipeline(original_img)
        
        latencies.append(mon.get_duration())
        cpu_times.append(mon.get_cpu_time())
        memories.append(mon.get_memory())
        
        print(f"Run {i+1} (t={current_time:.1f}s): {mon.get_duration():.2f}ms, Memory: {mon.get_memory():.2f}MB")
        
        # Warte die zufällige Zeit bis zum nächsten Request (außer beim letzten)
        if i < ITERATIONS - 1:
            delay = delays[i]
            print(f"  -> Nächster Request in {delay:.1f}s ({delay/60:.2f}min)")
            time.sleep(delay)

    total_time = time.time() - start_time
    print(f"\nGesamtzeit: {total_time:.1f}s ({total_time/60:.2f}min)")
    print(f"Durchschnittliche Zeit zwischen Requests: {total_time/(ITERATIONS-1):.1f}s")
    
    print("\n" + "="*50)
    print("Pipeline Performance Statistiken:")
    print("="*50)
    print_stats(latencies, cpu_times, memories)

if __name__ == "__main__":
    main()
