import subprocess
import json
import time
import statistics
from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg" # Pfad im MinIO Bucket, nicht lokal!
ITERATIONS = 30

def invoke_openwhisk():
    start = time.time()
    
    # Aufruf via CLI (blocking mit --result)
    #
    cmd = [
        "wsk", "action", "invoke", ACTION_NAME,
        "--result",
        "--param", "imageKey", IMAGE_KEY,
        "--param", "size", "640"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        end = time.time()
        
        if result.returncode != 0:
            print("Error invoking action:", result.stderr)
            return None, None

        # Wir haben jetzt das JSON Resultat der Action
        # Um aber an die "annotations" (initTime etc.) zu kommen,
        # bräuchten wir die Activation ID. 
        # Da wir --result nutzen, kriegen wir nur den Output.
        
        # Strategie: Client-Side Latency messen wir hier (end - start)
        client_latency = (end - start) * 1000
        
        return client_latency, json.loads(result.stdout)
        
    except Exception as e:
        print(f"Exception: {e}")
        return None, None

def main():
    latencies = []
    
    print(f"Starte OpenWhisk Benchmark ({ITERATIONS} Durchläufe)...")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")

    for i in range(ITERATIONS):
        duration, result = invoke_openwhisk()
        
        if duration:
            latencies.append(duration)
            print(f"Run {i+1}: {duration:.2f}ms")
        else:
            print(f"Run {i+1}: FAILED")

    # OpenWhisk spezifische Ausgabe (nur Zeit, Memory ist hier schwer client-seitig zu messen)
    print_stats(latencies)
    print("Hinweis: Dies ist die Round-Trip-Time (Latenz) vom Client aus.")

if __name__ == "__main__":
    main()