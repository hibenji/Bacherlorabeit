import json
import os
import matplotlib.pyplot as plt
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))

# Benchmark folders
BENCHMARKS = {
    "local": "Local (In-Memory)",
    "local_minio_import": "Local + MinIO (Import)",
    "local_minio": "Local + MinIO (Subprocess)",
    "openwhisk": "OpenWhisk"
}

def load_results():
    results = {}
    for folder, label in BENCHMARKS.items():
        path = os.path.join(current_dir, folder, "results.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if data:
                    results[label] = data[-1]
    return results

def get_latency(data):
    # if "server_duration_ms" in data and data["server_duration_ms"] > 0:
    #     return data["server_duration_ms"]
    if "client_latency_ms" in data:
        return data["client_latency_ms"]
    return data.get("latency_ms", 0)

def get_cpu_time(data):
    return data.get("cpu_time_ms", 0)

def get_memory(data):
    if "memory_limit_mb" in data and data["memory_limit_mb"] > 0:
        return data["memory_limit_mb"]
    return data.get("memory_mb", 0)

def create_charts(results):
    if not results:
        print("No results found!")
        return
    
    labels = list(results.keys())
    latencies = [get_latency(results[l]) for l in labels]
    cpu_times = [get_cpu_time(results[l]) for l in labels]
    memories = [get_memory(results[l]) for l in labels]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Benchmark Comparison", fontsize=14, fontweight='bold')
    
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    
    # Latency chart
    ax1 = axes[0]
    bars1 = ax1.bar(range(len(labels)), latencies, color=colors[:len(labels)])
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('End-to-End Latency')
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars1, latencies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    # CPU Time chart
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(labels)), cpu_times, color=colors[:len(labels)])
    ax2.set_ylabel('CPU Time (ms)')
    ax2.set_title('CPU Time (User + System)')
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars2, cpu_times):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Memory chart
    ax3 = axes[2]
    bars3 = ax3.bar(range(len(labels)), memories, color=colors[:len(labels)])
    ax3.set_ylabel('Memory (MB)')
    ax3.set_title('Peak Memory Usage')
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars3, memories):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Save to file
    output_path = os.path.join(current_dir, "benchmark_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    
    plt.show()

def print_summary(results):
    print("\n" + "="*70)
    print("BENCHMARK COMPARISON SUMMARY")
    print("="*70)
    print(f"{'Benchmark':<30} {'Latency':>12} {'CPU Time':>12} {'Memory':>10}")
    print("-"*70)
    for label, data in results.items():
        latency = get_latency(data)
        cpu_time = get_cpu_time(data)
        memory = get_memory(data)
        cpu_str = f"{cpu_time:.1f}ms" if cpu_time > 0 else "N/A"
        print(f"{label:<30} {latency:>10.1f}ms {cpu_str:>12} {memory:>8.1f}MB")
    print("="*70)

if __name__ == "__main__":
    results = load_results()
    print_summary(results)
    create_charts(results)
