import cv2
import numpy as np
import os
import sys
import io
import json
import time
import random
from datetime import datetime

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
ITERATIONS = 30
MIN_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 1200
RANDOM_SEED = 18
RESULTS_FILE = current_dir + "/results_random.json"

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

def generate_random_delays(num, min_d, max_d, seed):
    return [random.Random(seed).uniform(min_d, max_d) for _ in range(num)]

def save_results(latencies, cpu_times, memories, total_time):
    import statistics
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio_import",
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
    s3 = resize_mod.s3_client_from_env()
    delays = generate_random_delays(ITERATIONS - 1, MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, RANDOM_SEED)
    latencies, cpu_times, memories = [], [], []

    print(f"Starte local_minio_import Random Benchmark ({ITERATIONS} Durchläufe)...")
    print("Warming up...")
    run_pipeline_with_minio(s3)

    start_time = time.time()
    for i in range(ITERATIONS):
        with PerformanceMonitor() as mon:
            run_pipeline_with_minio(s3)
        latencies.append(mon.get_duration())
        cpu_times.append(mon.get_cpu_time())
        memories.append(mon.get_memory())
        print(f"Run {i+1}: {mon.get_duration():.2f}ms")
        if i < ITERATIONS - 1:
            print(f"  -> Delay: {delays[i]:.1f}s")
            time.sleep(delays[i])

    total_time = time.time() - start_time
    print_stats(latencies, cpu_times, memories)
    save_results(latencies, cpu_times, memories, total_time)

if __name__ == "__main__":
    main()
