import subprocess
import time

def run_cmd(cmd):
    """Run a shell command and return execution time + output"""
    start = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end = time.time()
    return end - start, result.stdout, result.stderr

if __name__ == "__main__":
    # Change this to your test image
    image_path = "test.jpg"

    # Intermediate files
    blob_file = "blob.npy"
    meta_file = "meta.json"
    raw_file = "raw_outputs.npy"
    out_img = "result.jpg"

    # --- Step 1: Resize (preprocess) ---
    resize_cmd = f"python resize.py {image_path} --out_blob {blob_file} --meta {meta_file}"
    resize_time, resize_out, resize_err = run_cmd(resize_cmd)
    print("Resize.py output:\n", resize_out)
    if resize_err:
        print("Resize.py errors:\n", resize_err)
    print(f"Resize time: {resize_time:.3f} seconds\n")

    # --- Step 2: Detect (inference) ---
    detect_cmd = f"python detect.py --blob {blob_file} --out_raw {raw_file}"
    detect_time, detect_out, detect_err = run_cmd(detect_cmd)
    print("Detect.py output:\n", detect_out)
    if detect_err:
        print("Detect.py errors:\n", detect_err)
    print(f"Detection time: {detect_time:.3f} seconds\n")

    # --- Step 3: Postprocess (rescale + NMS) ---
    post_cmd = f"python postprocess.py --raw {raw_file} --meta {meta_file} --out_img {out_img}"
    post_time, post_out, post_err = run_cmd(post_cmd)
    print("Postprocess.py output:\n", post_out)
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
