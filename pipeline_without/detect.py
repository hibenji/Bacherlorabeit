import numpy as np
import onnxruntime as ort
import os, requests

MODEL_PATH = os.getenv("MODEL_PATH", "./yolov5s.onnx")
MODEL_URL = "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx"

# Ensure model file exists
if not os.path.exists(MODEL_PATH):
    print(f"Downloading YOLOv5 model from {MODEL_URL} ...")
    resp = requests.get(MODEL_URL, stream=True)
    resp.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

# Init session
session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
output_names = [o.name for o in session.get_outputs()]

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--blob", default="blob.npy", help="Path to preprocessed blob")
    parser.add_argument("--out_raw", default="raw_outputs.npy")
    args = parser.parse_args()

    blob = np.load(args.blob)
    outputs = session.run(output_names, {input_name: blob})
    np.save(args.out_raw, outputs[0])

    print(f"Saved raw detections to {args.out_raw}")
