import cv2
import numpy as np
import json
import os
import io
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

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

def scale_boxes(x, y, w, h, img_w, img_h, size=640):
    x1 = int((x - w / 2) * img_w / size)
    y1 = int((y - h / 2) * img_h / size)
    x2 = int((x + w / 2) * img_w / size)
    y2 = int((y + h / 2) * img_h / size)
    return x1, y1, x2, y2

def postprocess(img, img_h, img_w, detections, conf_threshold=0.25, iou_threshold=0.45):
    results = []
    if len(detections.shape) == 3:
        detections = detections[0]

    boxes_xyxy, boxes_xywh, scores, class_ids = [], [], [], []
    for det in detections:
        conf = float(det[4])
        if conf > conf_threshold:
            scores_cls = det[5:]
            if scores_cls.size == 0:
                continue
            class_id = int(np.argmax(scores_cls))
            score = float(scores_cls[class_id]) * conf
            if score > conf_threshold:
                x, y, w, h = det[0:4]
                x1, y1, x2, y2 = scale_boxes(x, y, w, h, img_w, img_h)
                boxes_xyxy.append([int(x1), int(y1), int(x2), int(y2)])
                boxes_xywh.append([int(x1), int(y1), int(x2) - int(x1), int(y2) - int(y1)])
                scores.append(float(score))
                class_ids.append(class_id)

    if len(boxes_xywh) == 0:
        return results

    indices = cv2.dnn.NMSBoxes(boxes_xywh, scores, conf_threshold, iou_threshold)
    if indices is None or len(indices) == 0:
        return results

    try:
        iter_indices = indices.flatten()
    except Exception:
        iter_indices = [i[0] if isinstance(i, (list, tuple, np.ndarray)) else int(i) for i in indices]

    for i in iter_indices:
        i = int(i)
        x1, y1, x2, y2 = boxes_xyxy[i]
        class_id = class_ids[i]
        score = scores[i]
        results.append({"class_id": class_id, "score": score, "box": [x1, y1, x2, y2]})

    return results

if __name__ == "__main__":
    # Defaults (match other scripts)
    image_key = "input/test.jpg"
    bucket = "imgreco"
    prefix = "tmp"
    raw_key = f"{prefix}/raw_outputs.npy"
    meta_key = f"{prefix}/meta.json"
    out_name = "result.jpg"

    # Download from MinIO
    s3 = s3_client_from_env()

    # Load metadata
    meta_bytes = s3_get_bytes(s3, bucket, meta_key)
    meta = json.loads(meta_bytes.decode("utf-8"))
    img_h, img_w = meta.get("img_h"), meta.get("img_w")

    # Determine image key/path from meta (support different key names)
    image_key_from_meta = meta.get("imageKey") or meta.get("image_key") or meta.get("imagePath") or meta.get("image_path")
    if image_key_from_meta:
        image_key = image_key_from_meta

    # Load original image from S3/MinIO
    try:
        img_bytes = s3_get_bytes(s3, bucket, image_key)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not decode image from s3://{bucket}/{image_key}")
    except Exception:
        # Fallback: try local path if image_key looks like a local path
        img = cv2.imread(image_key)
        if img is None:
            raise

    # Load raw detections
    raw_bytes = s3_get_bytes(s3, bucket, raw_key)
    detections = np.load(io.BytesIO(raw_bytes), allow_pickle=False)

    results = postprocess(img, img_h, img_w, detections)

    # Draw boxes
    for r in results:
        x1, y1, x2, y2 = r["box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"ID:{r['class_id']} {r['score']:.2f}",
                    (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)

    # Upload result to MinIO
    ok, jpg = cv2.imencode(".jpg", img)
    if not ok:
        raise ValueError("Failed to encode annotated image.")
    
    result_key = f"{prefix}/{out_name}"
    s3_put_bytes(s3, bucket, result_key, jpg.tobytes(), content_type="image/jpeg")
    
    print("Final results:", results)
    print(f"Uploaded image with detections to s3://{bucket}/{result_key}")
