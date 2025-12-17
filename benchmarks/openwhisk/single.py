import subprocess
import json
import time
import os
import sys
from datetime import datetime

# 1. Den absoluten Pfad zum 'metrics' Ordner finden
current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')

sys.path.append(metrics_dir)

from metrics import PerformanceMonitor, print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"
SIZE = "640"
RESULTS_FILE = current_dir + "/results_single.json"


def invoke_openwhisk(action_name=ACTION_NAME, image_key=IMAGE_KEY, size=SIZE):
    start = time.time()
    
    # Step 1: Invoke without --result to get activation ID
    invoke_cmd = [
        "wsk", "action", "invoke", action_name,
        "--param", "imageKey", image_key,
        "--param", "size", size
    ]
    
    try:
        result = subprocess.run(invoke_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error invoking action:", result.stderr)
            return None, None, None
        
        # Parse activation ID from output like: "ok: invoked /_/yolo-seq with id abc123"
        output = result.stdout.strip()
        activation_id = output.split("with id ")[-1].strip()
        print(f"Activation ID: {activation_id}")
        
        # Step 2: Wait and poll for activation result
        max_wait = 120  # seconds
        poll_interval = 1.0
        waited = 0
        activation_data = None
        
        while waited < max_wait:
            get_cmd = ["wsk", "activation", "get", activation_id]
            get_result = subprocess.run(get_cmd, capture_output=True, text=True)
            
            if get_result.returncode == 0:
                # Parse JSON from output (skip the "ok: got activation..." line)
                output_lines = get_result.stdout.strip().split('\n')
                json_start = None
                for i, line in enumerate(output_lines):
                    if line.strip().startswith('{'):
                        json_start = i
                        break
                
                if json_start is not None:
                    json_str = '\n'.join(output_lines[json_start:])
                    try:
                        activation_data = json.loads(json_str)
                        # Check if activation is complete (has 'end' field > 0)
                        if activation_data.get("end", 0) > 0:
                            break
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
            
            time.sleep(poll_interval)
            waited += poll_interval
            if waited % 10 == 0:
                print(f"  Waiting... ({waited}s)")
        
        end = time.time()
        client_latency = (end - start) * 1000
        
        if not activation_data:
            print("Timeout waiting for activation")
            return client_latency, None, None
        
        # Extract server-side metrics from activation
        server_duration = activation_data.get("duration", 0)
        
        # Memory limit is in the annotations
        annotations = activation_data.get("annotations", [])
        memory_limit_mb = 256  # default
        for ann in annotations:
            if ann.get("key") == "limits":
                limits = ann.get("value", {})
                memory_limit_mb = limits.get("memory", 256)
                break
        
        # Get the result
        response = activation_data.get("response", {})
        result_data = response.get("result", {})
        
        server_metrics = {
            "activation_id": activation_id,
            "server_duration_ms": server_duration,
            "memory_limit_mb": memory_limit_mb,
            "status": response.get("status", "unknown"),
            "result": result_data
        }
        
        return client_latency, server_metrics, result_data

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def save_results(client_latency, server_metrics, detections_count):
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "client_latency_ms": client_latency,
        "server_duration_ms": server_metrics.get("server_duration_ms", 0) if server_metrics else 0,
        "memory_limit_mb": server_metrics.get("memory_limit_mb", 0) if server_metrics else 0,
        "activation_id": server_metrics.get("activation_id", "") if server_metrics else "",
        "detections_count": detections_count
    }
    
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
    else:
        results = []
    
    results.append(result)
    
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {RESULTS_FILE}")


def main():
    print(f"Starte OpenWhisk Benchmark (1 Durchlauf)...")
    print("Stelle sicher, dass MinIO und OpenWhisk laufen!")

    client_latency, server_metrics, result_data = invoke_openwhisk()

    if client_latency and server_metrics:
        # Try to get detections count from result
        detections_count = 0
        if isinstance(result_data, dict):
            if "detections" in result_data:
                detections_count = len(result_data.get("detections", []))
            elif "results" in result_data:
                detections_count = len(result_data.get("results", []))

        print(f"\n=== Results ===")
        print(f"Client Round-Trip: {client_latency:.2f}ms")
        print(f"Server Duration:   {server_metrics['server_duration_ms']}ms")
        print(f"Memory Limit:      {server_metrics['memory_limit_mb']}MB")
        print(f"Activation ID:     {server_metrics['activation_id']}")
        print(f"Status:            {server_metrics['status']}")
        print(f"Detections:        {detections_count}")
        
        save_results(client_latency, server_metrics, detections_count)
    else:
        print("Run : FAILED")


if __name__ == "__main__":
    main()
