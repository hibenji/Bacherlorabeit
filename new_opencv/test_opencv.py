import cv2
import numpy as np
import onnxruntime as ort
import base64
import os
import requests


# Default model path inside container (use /tmp, writable in OpenWhisk)
MODEL_PATH = os.getenv("MODEL_PATH", "/tmp/yolov5s.onnx")
MODEL_URL = "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx"

# Ensure model is present
if not os.path.exists(MODEL_PATH):
    print(f"Downloading YOLOv5 model from {MODEL_URL} ...")
    resp = requests.get(MODEL_URL, stream=True)
    resp.raise_for_status()
    with open(MODEL_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive chunks
                f.write(chunk)

session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name
output_names = [o.name for o in session.get_outputs()]

def preprocess_image(img_b64):
    """Decode base64 image -> preprocessed tensor"""
    img_data = base64.b64decode(img_b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image input")

    img_h, img_w = img.shape[:2]
    blob = cv2.resize(img, (640, 640))
    blob = cv2.cvtColor(blob, cv2.COLOR_BGR2RGB)
    blob = blob.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)
    return img, img_h, img_w, blob

def postprocess(img, img_h, img_w, outputs, conf_threshold=0.25):
    """Draw detections + return structured results"""
    results = []
    for det in outputs[0]:
        conf = det[4].item()
        if conf > conf_threshold:
            scores = det[5:]
            class_id = int(np.argmax(scores))
            score = float(scores[class_id])
            if score > conf_threshold:
                x = det[0].item()
                y = det[1].item()
                w = det[2].item()
                h = det[3].item()

                x1 = int((x - w / 2) * img_w / 640)
                y1 = int((y - h / 2) * img_h / 640)
                x2 = int((x + w / 2) * img_w / 640)
                y2 = int((y + h / 2) * img_h / 640)

                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, f"ID:{class_id} {score:.2f}",
                            (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 2)

                results.append({
                    "class_id": class_id,
                    "score": score,
                    "box": [x1, y1, x2, y2]
                })
    return img, results


def main(params):
    """
    OpenWhisk entrypoint
    Input params:
      - image_b64: Base64 encoded image
    Output:
      - result_b64: Base64 encoded annotated image
      - detections: List of boxes + scores
    """
    try:
        if "image_b64" not in params:
            return {"error": "Missing parameter: image_b64"}

        img, img_h, img_w, blob = preprocess_image(params["image_b64"])
        outputs = session.run(output_names, {input_name: blob})
        img_out, detections = postprocess(img, img_h, img_w, outputs)

        # Encode result image
        _, buffer = cv2.imencode(".jpg", img_out)
        result_b64 = base64.b64encode(buffer).decode("utf-8")

        return {
            "status": "success",
            "detections": detections,
            "result_b64": result_b64
        }

    except Exception as e:
        return {"error": str(e)}
