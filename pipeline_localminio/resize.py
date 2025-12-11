import cv2
import numpy as np
import json
import os
import io
import uuid
import boto3
from botocore.config import Config
from dotenv import load_dotenv
import os
load_dotenv()  # loads .env automatically

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

def s3_put_bytes(s3, bucket, key, data, content_type=None):
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    s3.put_object(Bucket=bucket, Key=key, Body=data, **extra)

def s3_get_bytes(s3, bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

def preprocess_image(img, size=640):
    img_h, img_w = img.shape[:2]
    blob = cv2.resize(img, (size, size))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = blob.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
    blob = np.expand_dims(blob, axis=0)   # add batch
    return img_h, img_w, blob

if __name__ == "__main__":
    image_key = "input/test.jpg"
    bucket = "imgreco"
    size = 640
    out_prefix = "tmp"
    
    # Upload to MinIO
    s3 = s3_client_from_env()
    
    # Load image
    img_bytes = s3_get_bytes(s3, bucket, image_key)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        print({"error": f"Could not decode image at s3://{bucket}/{image_key}"})

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
    