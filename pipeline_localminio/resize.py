import cv2
import numpy as np
import json
import os
import io
import uuid
import boto3
from botocore.config import Config

def s3_client_from_env():
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

def s3_put_bytes(s3, bucket, key, data, content_type=None):
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    s3.put_object(Bucket=bucket, Key=key, Body=data, **extra)

def preprocess_image(img, size=640):
    img_h, img_w = img.shape[:2]
    blob = cv2.resize(img, (size, size))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = blob.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))  # HWC -> CHW
    blob = np.expand_dims(blob, axis=0)   # add batch
    return img_h, img_w, blob

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("image_path", help="Path to input image")
    parser.add_argument("--bucket", default="imgreco", help="MinIO bucket name")
    parser.add_argument("--prefix", default=None, help="Output prefix in MinIO")
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    if img is None:
        raise ValueError(f"Could not load image: {args.image_path}")

    img_h, img_w, blob = preprocess_image(img)
    
    # Generate unique prefix if not provided
    if not args.prefix:
        base = os.path.splitext(os.path.basename(args.image_path))[0]
        args.prefix = f"tmp/{base}-{uuid.uuid4().hex[:8]}"
    
    # Upload to MinIO
    s3 = s3_client_from_env()
    blob_key = f"{args.prefix}/blob.npy"
    meta_key = f"{args.prefix}/meta.json"
    
    # Save blob to MinIO
    np_bytes = io.BytesIO()
    np.save(np_bytes, blob)
    s3_put_bytes(s3, args.bucket, blob_key, np_bytes.getvalue(), content_type="application/octet-stream")
    
    # Save metadata to MinIO
    meta = {"img_h": img_h, "img_w": img_w, "image_path": args.image_path, "prefix": args.prefix}
    s3_put_bytes(s3, args.bucket, meta_key, json.dumps(meta).encode("utf-8"), content_type="application/json")

    print(f"Uploaded preprocessed blob to s3://{args.bucket}/{blob_key}")
    print(f"Uploaded metadata to s3://{args.bucket}/{meta_key}")
    print(f"Prefix: {args.prefix}")
