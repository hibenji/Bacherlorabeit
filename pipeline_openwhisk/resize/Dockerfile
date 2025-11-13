FROM hibenji/openwhisk_base:latest

# System dependencies required for OpenCV headless
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    boto3
