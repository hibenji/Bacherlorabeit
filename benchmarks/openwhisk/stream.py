import subprocess
import json
import time
import statistics
import os
import sys
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
metrics_dir = os.path.join(current_dir, '../')
sys.path.append(metrics_dir)
from metrics import print_stats

# Konfiguration
ACTION_NAME = "yolo-seq"
IMAGE_KEY = "input/test.jpg"
ITERATIONS = 30
RESULTS_FILE = current_dir + "/results_stream.json"

def invoke_openwhisk():
    start = time.time()
    
    # Step 1: Invoke without --result to get activation ID
    invoke_cmd = [
        "wsk", "action", "invoke", ACTION_NAME,
        "--param", "imageKey", IMAGE_KEY,
        "--param", "size", "640"
    ]
    
    try:
        result = subprocess.run(invoke_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error invoking action:", result.stderr)
            return None, None
        
        # Parse activation ID from output like: "ok: invoked /_/yolo-seq with id abc123"
        output = result.stdout.strip()
        activation_id = output.split("with id ")[-1].strip()
        
        # Step 2: Wait and poll for activation result
        max_wait = 120  # seconds
        poll_interval = 1.0
        waited = 0
        activation_data = None
        
        while waited < max_wait:
            get_cmd = ["wsk", "activation", "get", activation_id]
            get_result = subprocess.run(get_cmd, capture_output=True, text=True)
            
            if get_result.returncode == 0:
                # Parse JSON from output
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
                        if activation_data.get("end", 0) > 0:
                            break
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
            
            time.sleep(poll_interval)
            waited += poll_interval
        
        end = time.time()
        client_latency = (end - start) * 1000
        
        if not activation_data:
            print("Timeout waiting for activation")
            return client_latency, None
        
        # Extract server-side metrics
        server_duration = activation_data.get("duration", 0)
        
        # Memory limit is in the annotations
        annotations = activation_data.get("annotations", [])
        memory_limit_mb = 256  # default
        for ann in annotations:
            if ann.get("key") == "limits":
                limits = ann.get("value", {})
                memory_limit_mb = limits.get("memory", 256)
                break
        
        metrics = {
            "server_duration_ms": server_duration,
            "memory_limit_mb": memory_limit_mb
        }
        
        return client_latency, metrics
        
    except Exception as e:
        print(f"Exception: {e}")
        return None, None

def save_results(latencies, server_durations, memory_limit_mb):
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_type": "openwhisk",
        "test_type": "stream",
        "iterations": len(latencies),
        "latency_avg_ms": statistics.mean(latencies),
        "latency_std_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "server_duration_avg_ms": statistics.mean(server_durations) if server_durations else 0,
        "memory_limit_mb": memory_limit_mb
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
    latencies = []
    server_durations = []
    memory_limit_mb = 0
    
    print(f"Starte OpenWhisk Stream Benchmark ({ITERATIONS} Durchläufe)...")

    for i in range(ITERATIONS):
        client_latency, metrics = invoke_openwhisk()
        
        if client_latency and metrics:
            latencies.append(client_latency)
            server_durations.append(metrics["server_duration_ms"])
            memory_limit_mb = metrics["memory_limit_mb"]
            print(f"Run {i+1}: Client {client_latency:.2f}ms, Server {metrics['server_duration_ms']}ms")
        else:
            print(f"Run {i+1}: FAILED")

    if latencies:
        print_stats(latencies)
        save_results(latencies, server_durations, memory_limit_mb)
    else:
        print("Benchmark failed: No successful runs.")

if __name__ == "__main__":
    main()