import os, base64, uuid
import boto3
from botocore.config import Config
from mimetypes import guess_extension

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

def detect_extension(file_bytes):
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"):
        return ".gif"
    return ".bin"

def main(args):
    if "file" not in args:
        return {"error": "Missing required parameter: file (base64 image data)"}

    # Decode base64 image bytes
    try:
        file_bytes = base64.b64decode(args["file"])
    except Exception:
        return {"error": "Invalid base64 data"}

    # Detect extension based on magic bytes
    ext = detect_extension(file_bytes)
    filename = "input" + ext

    # Create random key
    uid = uuid.uuid4().hex[:8]
    key = f"tmp/{uid}/{filename}"

    bucket = args.get("bucket", "imgreco")

    # Upload to MinIO
    s3 = s3_client_from_env(args)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType="image/jpeg" if ext == ".jpg" else "application/octet-stream"
    )

    return {
        "ok": True,
        "bucket": bucket,
        "imageKey": key
    }
