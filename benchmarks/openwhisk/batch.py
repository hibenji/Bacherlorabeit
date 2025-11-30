import subprocess
import json
import time
import statistics
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. Den absoluten Pfad zum 'metrics' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)

from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"  # Pfad im MinIO Bucket, nicht lokal!
BATCH_SIZE = 25
ITERATIONS = 10
SIZE = "640"


def invoke_openwhisk(action_name=ACTION_NAME, image_key=IMAGE_KEY, size=SIZE):
    start = time.time()

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

        client_latency = (end - start) * 1000

        # Try parse JSON result, otherwise return raw stdout
        try:
            parsed = json.loads(result.stdout)
        except Exception:
            parsed = result.stdout

        return client_latency, parsed

    except Exception as e:
        print(f"Exception: {e}")
        return None, None


def process_single_invocation(request_id):
    latency, result = invoke_openwhisk()
    return {
        'request_id': request_id,
        'latency': latency,
        'result': result
    }


def run_batch(batch_size):
    results = []

    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_single_invocation, i) for i in range(batch_size)]

        for future in as_completed(futures):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"Invocation raised exception: {e}")

    return results


def main():
    print(f"Starte OpenWhisk Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")

    latencies = []
    batch_latencies = []

    # Warmup
    print("Warming up...")
    invoke_openwhisk()

    for i in range(ITERATIONS):
        print(f"\n=== Batch {i+1}/{ITERATIONS} ===")

        start_batch = time.time()
        batch_results = run_batch(BATCH_SIZE)
        end_batch = time.time()

        batch_duration = (end_batch - start_batch) * 1000
        batch_latencies.append(batch_duration)

        # Collect successful latencies
        successful = [r for r in batch_results if r.get('latency') is not None]
        failed = len(batch_results) - len(successful)

        for r in successful:
            latencies.append(r['latency'])

        if successful:
            mean_req = statistics.mean([r['latency'] for r in successful])
        else:
            mean_req = float('nan')

        throughput = (len(successful) / (batch_duration / 1000)) if batch_duration > 0 else float('inf')

        print(f"Batch-Gesamtzeit: {batch_duration:.2f}ms (failed: {failed})")
        print(f"Durchschnittliche Request-Latenz (erfolgreich): {mean_req:.2f}ms")
        print(f"Durchsatz: {throughput:.2f} requests/sec")

    print("\n" + "="*60)
    print("EINZELNE REQUEST-STATISTIKEN:")
    print("="*60)
    if latencies:
        print_stats(latencies)
    else:
        print("Keine erfolgreichen Requests zum Ausgeben der Statistiken.")

    print("\n" + "="*60)
    print("BATCH-STATISTIKEN (Gesamtzeit pro Batch):")
    print("="*60)
    if batch_latencies:
        print(f"Durchschnittliche Batch-Zeit: {statistics.mean(batch_latencies):.2f}ms")
        print(f"Median Batch-Zeit: {statistics.median(batch_latencies):.2f}ms")
        print(f"Min Batch-Zeit: {min(batch_latencies):.2f}ms")
        print(f"Max Batch-Zeit: {max(batch_latencies):.2f}ms")
        avg_throughput = (BATCH_SIZE / (statistics.mean(batch_latencies) / 1000)) if statistics.mean(batch_latencies) > 0 else float('inf')
        print(f"Durchschnittlicher Durchsatz: {avg_throughput:.2f} requests/sec")
    else:
        print("Keine Batch-Daten verfügbar.")


if __name__ == "__main__":
    main()
