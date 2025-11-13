FROM hibenji/openwhisk_base:latest

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    boto3 \
    onnxruntime

RUN mkdir -p /app

# Download YOLO model
RUN wget -O /app/yolov5s.onnx \
    https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx

ENV MODEL_PATH=/app/yolov5s.onnx
