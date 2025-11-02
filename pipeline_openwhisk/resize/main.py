import os, io, json, uuid
import numpy as np
import cv2
import boto3
from botocore.config import Config

# ---- MinIO/S3 helpers ----
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

# ---- Preprocess (from your resize.py, adapted) ----
def preprocess_image(img, size=640):
    img_h, img_w = img.shape[:2]
    blob = cv2.resize(img, (size, size))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = blob.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
    blob = np.expand_dims(blob, axis=0)   # add batch
    return img_h, img_w, blob

def main(args):
    # Inputs
    bucket = args.get("bucket", "imgreco")
    image_key = args["imageKey"]  # e.g., "input/cat.jpg"
    size = int(args.get("size", 640))
    out_prefix = args.get("outPrefix")  # optional
    if not out_prefix:
        base = os.path.splitext(os.path.basename(image_key))[0]
        out_prefix = f"tmp/{base}-{uuid.uuid4().hex[:8]}"

    # MinIO client
    s3 = s3_client_from_env(args)

    # Load image
    img_bytes = s3_get_bytes(s3, bucket, image_key)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": f"Could not decode image at s3://{bucket}/{image_key}"}

    # Preprocess
    img_h, img_w, blob = preprocess_image(img, size=size)

    # Save to MinIO
    blob_key = f"{out_prefix}/blob.npy"
    meta_key = f"{out_prefix}/meta.json"

    # np.save to bytes
    np_bytes = io.BytesIO()
    np.save(np_bytes, blob)
    s3_put_bytes(s3, bucket, blob_key, np_bytes.getvalue(), content_type="application/octet-stream")

    meta = {
        "img_h": img_h,
        "img_w": img_w,
        "size": size,
        "imageKey": image_key,
        "prefix": out_prefix
    }
    s3_put_bytes(s3, bucket, meta_key, json.dumps(meta).encode("utf-8"), content_type="application/json")

    return {
        "ok": True,
        "bucket": bucket,
        "blobKey": blob_key,
        "metaKey": meta_key,
        "width": img_w,
        "height": img_h,
        "size": size,
        "prefix": out_prefix
    }
