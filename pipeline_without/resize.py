import cv2
import numpy as np
import json

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
    parser.add_argument("--out_blob", default="blob.npy")
    parser.add_argument("--meta", default="meta.json")
    args = parser.parse_args()

    img = cv2.imread(args.image_path)
    if img is None:
        raise ValueError(f"Could not load image: {args.image_path}")

    img_h, img_w, blob = preprocess_image(img)
    np.save(args.out_blob, blob)

    with open(args.meta, "w") as f:
        json.dump({"img_h": img_h, "img_w": img_w, "image_path": args.image_path}, f)

    print(f"Saved preprocessed blob to {args.out_blob}")
    print(f"Saved metadata to {args.meta}")
