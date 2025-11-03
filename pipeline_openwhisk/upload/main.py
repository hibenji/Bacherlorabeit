import os, uuid, boto3
from botocore.config import Config

PUBLIC_BASE_URL = "http://162.55.221.174:9000"  # ✅ same as postprocess

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

def save_file_to_minio(file_bytes, bucket, extension):
    uid = uuid.uuid4().hex[:8]
    key = f"tmp/{uid}/input{extension}"
    s3 = s3_client_from_env({})
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType="image/jpeg" if extension == ".jpg" else "application/octet-stream"
    )
    return key

def detect_extension(file_bytes):
    if file_bytes.startswith(b"\xff\xd8\xff"): return ".jpg"
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"): return ".png"
    if file_bytes.startswith(b"GIF87a") or file_bytes.startswith(b"GIF89a"): return ".gif"
    return ".jpg"   # default to JPG instead of .bin ✅

def main(args):
    # Web actions put raw HTTP body in __ow_body
    if "__ow_body" not in args:
        return {"error": "Must be invoked as web action with multipart form upload"}

    body = args["__ow_body"].encode("latin1")  # raw bytes
    content_type = args.get("__ow_headers", {}).get("content-type", "")

    if not content_type.startswith("multipart/form-data"):
        return {"error": "Content-Type must be multipart/form-data"}

    # Extract file payload (simple split; OpenWhisk always sends single file part)
    boundary = content_type.split("boundary=")[-1]
    parts = body.split(("--" + boundary).encode())

    file_bytes = None
    for part in parts:
        if b"filename=" in part:
            file_bytes = part.split(b"\r\n\r\n", 1)[-1].rsplit(b"\r\n", 1)[0]
            break

    if not file_bytes:
        return {"error": "No file part detected"}

    ext = detect_extension(file_bytes)
    bucket = args.get("bucket", "imgreco")

    key = save_file_to_minio(file_bytes, bucket, ext)
    public_url = f"{PUBLIC_BASE_URL}/{bucket}/{key}"

    return {
        "ok": True,
        "bucket": bucket,
        "imageKey": key,
        "publicUrl": public_url
    }
