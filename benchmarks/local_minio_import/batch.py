import cv2
import numpy as np
import os
import sys
import io
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../../pipeline_localminio')
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(src_dir)
sys.path.append(metrics_dir)

import resize as resize_mod
import detect as detect_mod
import postprocess as post_mod
from metrics import PerformanceMonitor, print_stats

# Konfiguration
BUCKET = "imgreco"
PREFIX = "benchmark_tmp"
IMAGE_KEY = "input/test.jpg"
BATCH_SIZE = 50
ITERATIONS = 30
RESULTS_FILE = current_dir + "/results_batch.json"

def run_pipeline_with_minio(s3):
    img_bytes = resize_mod.s3_get_bytes(s3, BUCKET, IMAGE_KEY)
    img = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    img_h, img_w, blob = resize_mod.preprocess_image(img)
    
    blob_key, meta_key = f"{PREFIX}/blob.npy", f"{PREFIX}/meta.json"
    np_bytes = io.BytesIO()
    np.save(np_bytes, blob)
    resize_mod.s3_put_bytes(s3, BUCKET, blob_key, np_bytes.getvalue())
    resize_mod.s3_put_bytes(s3, BUCKET, meta_key, json.dumps({"img_h": img_h, "img_w": img_w, "imageKey": IMAGE_KEY}).encode())
    
    blob = np.load(io.BytesIO(detect_mod.s3_get_bytes(s3, BUCKET, blob_key)), allow_pickle=False).astype(np.float32)
    raw = detect_mod.session.run(detect_mod.output_names, {detect_mod.input_name: blob})[0]
    raw_key = f"{PREFIX}/raw_outputs.npy"
    buf = io.BytesIO()
    np.save(buf, raw)
    detect_mod.s3_put_bytes(s3, BUCKET, raw_key, buf.getvalue())
    
    meta = json.loads(post_mod.s3_get_bytes(s3, BUCKET, meta_key).decode())
    detections = np.load(io.BytesIO(post_mod.s3_get_bytes(s3, BUCKET, raw_key)), allow_pickle=False)
    orig_img = cv2.imdecode(np.frombuffer(post_mod.s3_get_bytes(s3, BUCKET, IMAGE_KEY), dtype=np.uint8), cv2.IMREAD_COLOR)
    return post_mod.postprocess(orig_img, meta["img_h"], meta["img_w"], detections)

def process_single_request(s3, request_id):
    with PerformanceMonitor() as mon:
        run_pipeline_with_minio(s3)
    return {'request_id': request_id, 'latency': mon.get_duration(), 'cpu_time': mon.get_cpu_time(), 'memory': mon.get_memory()}

def run_batch(s3, batch_size):
    results = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [executor.submit(process_single_request, s3, i) for i in range(batch_size)]
        for future in as_completed(futures):
            results.append(future.result())
    return results

def save_results(batch_latencies, all_latencies, all_cpu_times, all_memories):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio_import",
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
    s3 = resize_mod.s3_client_from_env()
    all_latencies, all_cpu_times, all_memories, batch_latencies = [], [], [], []

    print(f"Starte local_minio_import Batch-Benchmark ({ITERATIONS} Batches à {BATCH_SIZE} Requests)...")
    print("Warming up...")
    run_pipeline_with_minio(s3)

    for batch_num in range(ITERATIONS):
        print(f"\n=== Batch {batch_num+1}/{ITERATIONS} ===")
        with PerformanceMonitor() as batch_mon:
            batch_results = run_batch(s3, BATCH_SIZE)
        batch_latencies.append(batch_mon.get_duration())
        for r in batch_results:
            all_latencies.append(r['latency'])
            all_cpu_times.append(r['cpu_time'])
            all_memories.append(r['memory'])
        print(f"Batch-Zeit: {batch_mon.get_duration():.2f}ms, Durchsatz: {BATCH_SIZE / (batch_mon.get_duration() / 1000):.2f} req/s")

    save_results(batch_latencies, all_latencies, all_cpu_times, all_memories)

if __name__ == "__main__":
    main()
