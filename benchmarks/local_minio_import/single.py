import cv2
import numpy as np
import os
import sys
import io
import json
from datetime import datetime

# 1. Den absoluten Pfad zum 'src' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, '../../pipeline_localminio')
metrics_dir = os.path.join(current_dir, '../')

# 2. Den Pfad zu Python hinzufügen
sys.path.append(src_dir)
sys.path.append(metrics_dir)

# Import pipeline modules (loads ONNX model once!)
import resize as resize_mod
import detect as detect_mod
import postprocess as post_mod
from metrics import PerformanceMonitor, print_stats

# Konfiguration
IMAGE_PATH = current_dir + "/../test.jpg"
BUCKET = "imgreco"
PREFIX = "benchmark_tmp"
IMAGE_KEY = "input/test.jpg"
RESULTS_FILE = current_dir + "/results.json"

def run_pipeline_with_minio(s3):
    """
    Run the full pipeline using MinIO for data transfer between stages,
    but using imported modules (no subprocess overhead).
    """
    # === STAGE 1: RESIZE ===
    img_bytes = resize_mod.s3_get_bytes(s3, BUCKET, IMAGE_KEY)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    img_h, img_w, blob = resize_mod.preprocess_image(img)
    
    blob_key = f"{PREFIX}/blob.npy"
    meta_key = f"{PREFIX}/meta.json"
    
    np_bytes = io.BytesIO()
    np.save(np_bytes, blob)
    resize_mod.s3_put_bytes(s3, BUCKET, blob_key, np_bytes.getvalue(), content_type="application/octet-stream")
    
    meta = {"img_h": img_h, "img_w": img_w, "imageKey": IMAGE_KEY}
    resize_mod.s3_put_bytes(s3, BUCKET, meta_key, json.dumps(meta).encode("utf-8"), content_type="application/json")
    
    # === STAGE 2: DETECT ===
    blob_bytes = detect_mod.s3_get_bytes(s3, BUCKET, blob_key)
    blob = np.load(io.BytesIO(blob_bytes), allow_pickle=False)
    if blob.dtype != np.float32:
        blob = blob.astype(np.float32)
    
    outputs = detect_mod.session.run(detect_mod.output_names, {detect_mod.input_name: blob})
    raw = outputs[0]
    
    raw_key = f"{PREFIX}/raw_outputs.npy"
    buf = io.BytesIO()
    np.save(buf, raw)
    detect_mod.s3_put_bytes(s3, BUCKET, raw_key, buf.getvalue(), content_type="application/octet-stream")
    
    # === STAGE 3: POSTPROCESS ===
    meta_bytes = post_mod.s3_get_bytes(s3, BUCKET, meta_key)
    meta = json.loads(meta_bytes.decode("utf-8"))
    img_h, img_w = meta["img_h"], meta["img_w"]
    
    raw_bytes = post_mod.s3_get_bytes(s3, BUCKET, raw_key)
    detections = np.load(io.BytesIO(raw_bytes), allow_pickle=False)
    
    orig_bytes = post_mod.s3_get_bytes(s3, BUCKET, IMAGE_KEY)
    orig_array = np.frombuffer(orig_bytes, dtype=np.uint8)
    orig_img = cv2.imdecode(orig_array, cv2.IMREAD_COLOR)
    
    results = post_mod.postprocess(orig_img, img_h, img_w, detections)
    
    return results

def save_results(latency, cpu_time, memory, detections_count):
    """Save results to JSON file, appending to existing results."""
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "local_minio_import",
        "latency_ms": latency,
        "cpu_time_ms": cpu_time,
        "memory_mb": memory,
        "detections_count": detections_count
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

    print(f"Starte lokale MinIO Import Benchmark (1 Durchlauf)...")

    with PerformanceMonitor() as mon:
        detections = run_pipeline_with_minio(s3)
    
    latency = mon.get_duration()
    cpu_time = mon.get_cpu_time()
    memory = mon.get_memory()
    
    print(f"Run : {latency:.2f}ms")
    print(f"Memory Usage: {memory:.2f}MB")
    print(f"Detections: {len(detections)} objects found")
    
    save_results(latency, cpu_time, memory, len(detections))

if __name__ == "__main__":
    main()
