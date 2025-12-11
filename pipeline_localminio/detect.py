import numpy as np
import onnxruntime as ort
import os, requests
import io
import json
import boto3
from botocore.config import Config
from dotenv import load_dotenv

# get current directory
load_dotenv()
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "yolov5s.onnx")
MODEL_PATH = os.getenv("MODEL_PATH", model_path)
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

def s3_client_from_env():
    endpoint = os.environ.get("MINIO_ENDPOINT")
    access = os.environ.get("MINIO_ACCESS_KEY")
    secret = os.environ.get("MINIO_SECRET_KEY")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=region,
        config=Config(signature_version="s3v4")
    )

def s3_get_bytes(s3, bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def s3_put_bytes(s3, bucket, key, data, content_type=None):
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    s3.put_object(Bucket=bucket, Key=key, Body=data, **extra)

if __name__ == "__main__":   
    image_key = "input/test.jpg"
    bucket = "imgreco"
    size = 640
    prefix = "tmp"

    # Compute keys produced by resize.py
    blob_key = f"{prefix}/blob.npy"
    meta_key = f"{prefix}/meta.json"

    # Download blob and meta from MinIO
    s3 = s3_client_from_env()
    blob_bytes = s3_get_bytes(s3, bucket, blob_key)
    meta_bytes = s3_get_bytes(s3, bucket, meta_key)
    try:
        meta = json.loads(meta_bytes.decode("utf-8"))
    except Exception:
        meta = {}

    # Load numpy blob and ensure dtype
    blob = np.load(io.BytesIO(blob_bytes), allow_pickle=False)
    if blob.dtype != np.float32:
        blob = blob.astype(np.float32)

    # Run inference
    outputs = session.run(output_names, {input_name: blob})
    raw = outputs[0]

    # Upload raw outputs to MinIO
    raw_key = f"{prefix}/raw_outputs.npy"
    buf = io.BytesIO()
    np.save(buf, raw)
    s3_put_bytes(s3, bucket, raw_key, buf.getvalue(), content_type="application/octet-stream")

    print(f"Downloaded blob from s3://{bucket}/{blob_key}")
    print(f"Downloaded meta from s3://{bucket}/{meta_key}")
    print(f"Uploaded raw detections to s3://{bucket}/{raw_key}")
