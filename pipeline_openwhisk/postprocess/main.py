import os, io, json
import numpy as np
import cv2
import boto3
from botocore.config import Config

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

# ---- Postprocess (from your postprocess.py, adapted) ----
def scale_boxes(x, y, w, h, img_w, img_h, size=640):
    x1 = int((x - w / 2) * img_w / size)
    y1 = int((y - h / 2) * img_h / size)
    x2 = int((x + w / 2) * img_w / size)
    y2 = int((y + h / 2) * img_h / size)
    return x1, y1, x2, y2

def postprocess(img, img_h, img_w, detections, size=640, conf_threshold=0.25, iou_threshold=0.45):
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
                x1, y1, x2, y2 = scale_boxes(x, y, w, h, img_w, img_h, size=size)
                boxes.append([x1, y1, x2, y2])
                scores.append(score)
                class_ids.append(class_id)

    # NMS (OpenCV expects [x,y,w,h]; we have [x1,y1,x2,y2])
    # Convert to [x,y,w,h]
    rects = []
    for b in boxes:
        x, y, w, h = b[0], b[1], b[2]-b[0], b[3]-b[1]
        rects.append([x, y, w, h])

    indices = cv2.dnn.NMSBoxes(rects, scores, conf_threshold, iou_threshold)

    for i in (indices.flatten() if len(indices) else []):
        x, y, w, h = rects[i]
        class_id = class_ids[i]
        score = scores[i]
        results.append({"class_id": class_id, "score": float(score), "box": [int(x), int(y), int(x+w), int(y+h)]})

    return results

def draw_boxes(img, results):
    for r in results:
        x1, y1, x2, y2 = r["box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"ID:{r['class_id']} {r['score']:.2f}",
                    (x1, max(0, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)
    return img

def main(args):
    bucket = args.get("bucket", "imgreco")
    raw_key = args["rawKey"]    # from detect
    meta_key = args["metaKey"]  # from resize
    out_name = args.get("outName", "result.jpg")
    prefix = args.get("prefix") or os.path.dirname(raw_key) or "tmp"

    s3 = s3_client_from_env(args)

    # Load meta
    meta_bytes = s3_get_bytes(s3, bucket, meta_key)
    meta = json.loads(meta_bytes.decode("utf-8"))
    img_h, img_w = int(meta["img_h"]), int(meta["img_w"])
    size = int(meta.get("size", 640))
    image_key = meta["imageKey"]

    # Load original image
    img_bytes = s3_get_bytes(s3, bucket, image_key)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": f"Could not decode original image at s3://{bucket}/{image_key}"}

    # Load raw detections
    raw_bytes = s3_get_bytes(s3, bucket, raw_key)
    detections = np.load(io.BytesIO(raw_bytes), allow_pickle=False)

    # Postprocess + draw
    results = postprocess(img, img_h, img_w, detections, size=size)
    annotated = draw_boxes(img.copy(), results)

    # Save annotated image back to MinIO
    ok, jpg = cv2.imencode(".jpg", annotated)
    if not ok:
        return {"error": "Failed to encode annotated image."}

    result_key = f"{prefix}/{out_name}"
    s3_put_bytes(s3, bucket, result_key, jpg.tobytes(), content_type="image/jpeg")

    return {
        "ok": True,
        "bucket": bucket,
        "resultKey": result_key,
        "rawKey": raw_key,
        "metaKey": meta_key,
        "imageKey": image_key,
        "detections": results
    }
