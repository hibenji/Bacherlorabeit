import subprocess
import time
import json
import re

def run_cmd(cmd):
    """Run a shell command and return execution time + output"""
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    return end - start, result.stdout, result.stderr

if __name__ == "__main__":
    # Configuration
    image_path = "test.jpg"
    bucket = "imgreco"

    # --- Step 1: Resize (preprocess) ---
    print("=== Step 1: Resize (preprocess) ===")
    resize_cmd = f"python resize.py {image_path} --bucket {bucket}"
    resize_time, resize_out, resize_err = run_cmd(resize_cmd)
    print(resize_out)
    if resize_err:
        print("Resize.py errors:\n", resize_err)
    print(f"Resize time: {resize_time:.3f} seconds\n")
    
    # Extract prefix from output
    prefix_match = re.search(r"Prefix: (.+)", resize_out)
    if not prefix_match:
        print("ERROR: Could not extract prefix from resize output")
        exit(1)
    prefix = prefix_match.group(1)
    
    blob_key = f"{prefix}/blob.npy"
    meta_key = f"{prefix}/meta.json"

    # --- Step 2: Detect (inference) ---
    print("=== Step 2: Detect (inference) ===")
    detect_cmd = f"python detect.py --bucket {bucket} --blob_key {blob_key} --prefix {prefix}"
    detect_time, detect_out, detect_err = run_cmd(detect_cmd)
    print(detect_out)
    if detect_err:
        print("Detect.py errors:\n", detect_err)
    print(f"Detection time: {detect_time:.3f} seconds\n")
    
    raw_key = f"{prefix}/raw_outputs.npy"

    # --- Step 3: Postprocess (rescale + NMS) ---
    print("=== Step 3: Postprocess (rescale + NMS) ===")
    post_cmd = f"python postprocess.py --bucket {bucket} --raw_key {raw_key} --meta_key {meta_key} --prefix {prefix}"
    post_time, post_out, post_err = run_cmd(post_cmd)
    print(post_out)
    if post_err:
        print("Postprocess.py errors:\n", post_err)
    print(f"Postprocess time: {post_time:.3f} seconds\n")

    # --- Summary ---
    total_time = resize_time + detect_time + post_time
    print("====== Benchmark Summary ======")
    print(f"Resize:      {resize_time:.3f} s")
    print(f"Detection:   {detect_time:.3f} s")
    print(f"Postprocess: {post_time:.3f} s")
    print(f"TOTAL:       {total_time:.3f} s")
    print(f"\nResults stored in MinIO bucket '{bucket}' under prefix '{prefix}'")
