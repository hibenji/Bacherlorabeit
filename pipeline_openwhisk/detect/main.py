import os, io, json
import numpy as np
import boto3
from botocore.config import Config
import onnxruntime as ort
import requests

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/yolov5s.onnx")
MODEL_URL = os.environ.get("MODEL_URL", "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx")

_session = None
_input_name = None
_output_names = None

def ensure_model():
    global _session, _input_name, _output_names
    if _session is not None:
        return
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}, downloading from {MODEL_URL}...")
        r = requests.get(MODEL_URL, stream=True, timeout=60)
        r.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
    else:
        print(f"Model found at {MODEL_PATH}, skipping download.")
    _session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    _input_name = _session.get_inputs()[0].name
    _output_names = [o.name for o in _session.get_outputs()]

def s3_client_from_env(args):
    endpoint = os.environ.get("MINIO_ENDPOINT", args.get("endpoint", "http://192.168.49.1:9000"))
    access = os.environ.get("MINIO_ACCESS_KEY", args.get("accessKey"))
    secret = os.environ.get("MINIO_SECRET_KEY", args.get("secretKey"))
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

def main(args):
    bucket = args.get("bucket", "imgreco")
    blob_key = args["blobKey"]
    meta_key = args.get("metaKey")
    image_key = args.get("imageKey")  # pass-through traceability

    prefix = args.get("prefix") or os.path.dirname(blob_key) or "tmp"
    s3 = s3_client_from_env(args)

    blob_bytes = s3_get_bytes(s3, bucket, blob_key)
    blob = np.load(io.BytesIO(blob_bytes), allow_pickle=False)

    ensure_model()
    outputs = _session.run(_output_names, {_input_name: blob})
    raw = outputs[0]

    raw_key = f"{prefix}/raw_outputs.npy"
    buf = io.BytesIO()
    np.save(buf, raw)
    s3_put_bytes(s3, bucket, raw_key, buf.getvalue(), content_type="application/octet-stream")

    return {
        "ok": True,
        "bucket": bucket,
        "rawKey": raw_key,
        "blobKey": blob_key,
        "metaKey": meta_key,       # ✅ FIX: forward for postprocess
        "imageKey": image_key,     # ✅ forward original image too
        "prefix": prefix,
        "modelPath": MODEL_PATH,
        "outputShape": list(raw.shape)
    }
