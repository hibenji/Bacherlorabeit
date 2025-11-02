import cv2
import numpy as np
import json

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
    parser.add_argument("--raw", default="raw_outputs.npy", help="Path to raw outputs .npy")
    parser.add_argument("--meta", default="meta.json", help="Path to metadata json")
    parser.add_argument("--out_img", default="result.jpg")
    args = parser.parse_args()

    detections = np.load(args.raw)
    with open(args.meta) as f:
        meta = json.load(f)

    img = cv2.imread(meta["image_path"])
    img_h, img_w = meta["img_h"], meta["img_w"]

    results = postprocess(img, img_h, img_w, detections)

    # Draw boxes
    for r in results:
        x1, y1, x2, y2 = r["box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img, f"ID:{r['class_id']} {r['score']:.2f}",
                    (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)

    cv2.imwrite(args.out_img, img)
    print("Final results:", results)
    print(f"Saved image with detections to {args.out_img}")
