import json
import os
import matplotlib.pyplot as plt
import statistics
import numpy as np

# Configuration
BENCHMARKS = {
    "local_minio": {
        "label": "Local + MinIO (Subprocess)",
        "json": "results_single.json",
        "color": "#3498db"
    },
    "openwhisk": {
        "label": "OpenWhisk (Single)",
        "json": "results_single.json",
        "color": "#e74c3c"
    }
}

current_dir = os.path.dirname(os.path.abspath(__file__))

def get_latency(data):
    if "latency_ms" in data:
        return data["latency_ms"]
    elif "server_duration_ms" in data and data["server_duration_ms"] > 0:
        return data["server_duration_ms"]
    return 0

def load_data():
    results = {}
    for folder, config in BENCHMARKS.items():
        path = os.path.join(current_dir, folder, config["json"])
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if data:
                    latencies = [get_latency(d) for d in data]
                    
                    results[config["label"]] = {
                        "latency_avg": statistics.mean(latencies),
                        "latency_std": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                        "color": config["color"]
                    }
    return results

def create_graph(results):
    if not results:
        print("No results found to visualize!")
        return

    labels = list(results.keys())
    latencies = [results[l]["latency_avg"] for l in labels]
    latency_stds = [results[l]["latency_std"] for l in labels]
    colors = [results[l]["color"] for l in labels]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Latency Comparison: OpenWhisk vs. Local MinIO Subprocess", fontsize=16, fontweight='bold')

    # Latency Chart
    ax.bar(labels, latencies, color=colors, yerr=latency_stds, capsize=10, alpha=0.8)
    ax.set_ylabel('Latency (ms)', fontsize=12)
    ax.set_title('Average Latency (Round-Trip)', fontsize=14)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    output_path = os.path.join(current_dir, "benchmark_comparison_single_custom.png")
    plt.savefig(output_path, dpi=150)
    print(f"Graph saved to: {output_path}")

if __name__ == "__main__":
    data = load_data()
    create_graph(data)
