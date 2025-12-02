import subprocess
import json
import time
import random as random
import os
import sys

# 1. Den absoluten Pfad zum 'metrics' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)

from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"  # Pfad im MinIO Bucket, nicht lokal!
ITERATIONS = 30
MIN_DELAY_SECONDS = 60  # 1 minute
MAX_DELAY_SECONDS = 1200  # 20 minutes
RANDOM_SEED = 18  # Für reproduzierbare Randomness
SIZE = "640"

def invoke_openwhisk(action_name=ACTION_NAME, image_key=IMAGE_KEY, size=SIZE):
    start = time.time()
    
    # Aufruf via CLI (blocking mit --result)
    cmd = [
        "wsk", "action", "invoke", action_name,
        "--result",
        "--param", "imageKey", image_key,
        "--param", "size", size
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        end = time.time()
        
        if result.returncode != 0:
            print("Error invoking action:", result.stderr)
            return None, None

        # Client-Side Latency messen
        client_latency = (end - start) * 1000
        
        # Try parse JSON result
        try:
            parsed = json.loads(result.stdout)
        except Exception:
            parsed = result.stdout
        
        return client_latency, parsed
        
    except Exception as e:
        print(f"Exception: {e}")
        return None, None

def generate_random_delays(num_delays, min_delay, max_delay, seed):
    """
    Generiert eine Liste von zufälligen Verzögerungen in Sekunden.
    Die Delays sind reproduzierbar dank des Seeds.
    """
    rng = random.Random(seed)
    delays = [rng.uniform(min_delay, max_delay) for _ in range(num_delays)]
    return delays

def main():
    # Generiere die vordefinierten zufälligen Delays
    delays = generate_random_delays(ITERATIONS - 1, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, RANDOM_SEED)
    
    latencies = []
    timestamps = []

    print(f"Starte OpenWhisk Benchmark mit zufälligen Delays ({ITERATIONS} Durchläufe)...")
    print(f"Delays zwischen {MIN_DELAY_SECONDS}s ({MIN_DELAY_SECONDS/60:.1f}min) und {MAX_DELAY_SECONDS}s ({MAX_DELAY_SECONDS/60:.1f}min)")
    print(f"Random Seed: {RANDOM_SEED} (für Reproduzierbarkeit)")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")
    
    # Warmup
    print("\nWarming up...")
    invoke_openwhisk()

    start_time = time.time()
    
    for i in range(ITERATIONS):
        current_time = time.time() - start_time
        timestamps.append(current_time)
        
        duration, result = invoke_openwhisk()
        
        if duration:
            latencies.append(duration)
            print(f"Run {i+1} (t={current_time:.1f}s): {duration:.2f}ms")
        else:
            print(f"Run {i+1} (t={current_time:.1f}s): FAILED")
        
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
    if latencies:
        print_stats(latencies)
        print("\nHinweis: Dies ist die Round-Trip-Time (Latenz) vom Client aus.")
    else:
        print("Keine erfolgreichen Requests zum Ausgeben der Statistiken.")

if __name__ == "__main__":
    main()
