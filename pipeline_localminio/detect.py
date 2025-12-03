import numpy as np
import onnxruntime as ort
import os, requests
import io
import boto3
from botocore.config import Config

# get current directory
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
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://192.168.49.1:9000")
    access = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default="imgreco", help="MinIO bucket name")
    parser.add_argument("--blob_key", required=True, help="MinIO key for blob")
    parser.add_argument("--prefix", required=True, help="Output prefix in MinIO")
    args = parser.parse_args()

    # Download blob from MinIO
    s3 = s3_client_from_env()
    blob_bytes = s3_get_bytes(s3, args.bucket, args.blob_key)
    blob = np.load(io.BytesIO(blob_bytes), allow_pickle=False)
    
    # Run inference
    outputs = session.run(output_names, {input_name: blob})
    raw = outputs[0]
    
    # Upload raw outputs to MinIO
    raw_key = f"{args.prefix}/raw_outputs.npy"
    buf = io.BytesIO()
    np.save(buf, raw)
    s3_put_bytes(s3, args.bucket, raw_key, buf.getvalue(), content_type="application/octet-stream")

    print(f"Downloaded blob from s3://{args.bucket}/{args.blob_key}")
    print(f"Uploaded raw detections to s3://{args.bucket}/{raw_key}")
