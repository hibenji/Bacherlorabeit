import cv2
import numpy as np
import json
import os
import io
import boto3
from botocore.config import Config

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

    boxes, scores, class_ids = [], [], []
    for det in detections:
        conf = float(det[4])
        if conf > conf_threshold:
            scores_cls = det[5:]
            class_id = int(np.argmax(scores_cls))
            score = float(scores_cls[class_id]) * conf
            if score > conf_threshold:
                x, y, w, h = det[0:4]
                x1, y1, x2, y2 = scale_boxes(x, y, w, h, img_w, img_h)
                boxes.append([x1, y1, x2, y2])
                scores.append(score)
                class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
    for i in indices.flatten():
        x1, y1, x2, y2 = boxes[i]
        class_id = class_ids[i]
        score = scores[i]
        results.append({"class_id": class_id, "score": score, "box": [x1, y1, x2, y2]})

    return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", default="imgreco", help="MinIO bucket name")
    parser.add_argument("--raw_key", required=True, help="MinIO key for raw outputs")
    parser.add_argument("--meta_key", required=True, help="MinIO key for metadata")
    parser.add_argument("--prefix", required=True, help="Output prefix in MinIO")
    parser.add_argument("--out_name", default="result.jpg", help="Output image filename")
    args = parser.parse_args()

    # Download from MinIO
    s3 = s3_client_from_env()
    
    # Load metadata
    meta_bytes = s3_get_bytes(s3, args.bucket, args.meta_key)
    meta = json.loads(meta_bytes.decode("utf-8"))
    img_h, img_w = meta["img_h"], meta["img_w"]
    image_path = meta["image_path"]
    
    # Load original image (from local filesystem for now)
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Load raw detections
    raw_bytes = s3_get_bytes(s3, args.bucket, args.raw_key)
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
    
    result_key = f"{args.prefix}/{args.out_name}"
    s3_put_bytes(s3, args.bucket, result_key, jpg.tobytes(), content_type="image/jpeg")
    
    print("Final results:", results)
    print(f"Uploaded image with detections to s3://{args.bucket}/{result_key}")
