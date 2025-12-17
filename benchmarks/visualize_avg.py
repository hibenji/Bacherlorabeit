import json
import os
import matplotlib.pyplot as plt
import numpy as np
import statistics

current_dir = os.path.dirname(os.path.abspath(__file__))

BENCHMARKS = {
    "local": "Local (In-Memory)",
    "local_minio_import": "Local + MinIO (Import)",
    "local_minio": "Local + MinIO (Subprocess)",
    "openwhisk": "OpenWhisk"
}

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

def load_results():
    results = {}
    for folder, label in BENCHMARKS.items():
        path = os.path.join(current_dir, folder, "results.json")
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if data:
                    latencies = [get_latency(d) for d in data]
                    cpu_times = [get_cpu_time(d) for d in data]
                    memories = [get_memory(d) for d in data]
                    
                    # Filter out zeros for cpu_times
                    cpu_times_valid = [c for c in cpu_times if c > 0]
                    
                    results[label] = {
                        "count": len(data),
                        "latency_avg": statistics.mean(latencies),
                        "latency_std": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                        "cpu_time_avg": statistics.mean(cpu_times_valid) if cpu_times_valid else 0,
                        "cpu_time_std": statistics.stdev(cpu_times_valid) if len(cpu_times_valid) > 1 else 0,
                        "memory_avg": statistics.mean(memories),
                        "memory_std": statistics.stdev(memories) if len(memories) > 1 else 0,
                    }
    return results

def create_charts(results):
    if not results:
        print("No results found!")
        return
    
    labels = list(results.keys())
    latencies = [results[l]["latency_avg"] for l in labels]
    latency_stds = [results[l]["latency_std"] for l in labels]
    cpu_times = [results[l]["cpu_time_avg"] for l in labels]
    cpu_stds = [results[l]["cpu_time_std"] for l in labels]
    memories = [results[l]["memory_avg"] for l in labels]
    memory_stds = [results[l]["memory_std"] for l in labels]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Benchmark Comparison (Averages)", fontsize=14, fontweight='bold')
    
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    
    # Latency chart with error bars
    ax1 = axes[0]
    bars1 = ax1.bar(range(len(labels)), latencies, color=colors[:len(labels)], yerr=latency_stds, capsize=5)
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Avg End-to-End Latency')
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars1, latencies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    # CPU Time chart
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(labels)), cpu_times, color=colors[:len(labels)], yerr=cpu_stds, capsize=5)
    ax2.set_ylabel('CPU Time (ms)')
    ax2.set_title('Avg CPU Time')
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars2, cpu_times):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    # Memory chart
    ax3 = axes[2]
    bars3 = ax3.bar(range(len(labels)), memories, color=colors[:len(labels)], yerr=memory_stds, capsize=5)
    ax3.set_ylabel('Memory (MB)')
    ax3.set_title('Avg Peak Memory')
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars3, memories):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    output_path = os.path.join(current_dir, "benchmark_comparison_avg.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    
    plt.show()

def print_summary(results):
    print("\n" + "="*90)
    print("BENCHMARK COMPARISON SUMMARY (AVERAGES)")
    print("="*90)
    print(f"{'Benchmark':<30} {'Count':>6} {'Latency':>16} {'CPU Time':>16} {'Memory':>14}")
    print("-"*90)
    for label, data in results.items():
        lat_std = f"±{data['latency_std']:.0f}" if data['latency_std'] > 0 else ""
        latency_str = f"{data['latency_avg']:.1f}{lat_std}ms"
        cpu_std = f"±{data['cpu_time_std']:.0f}" if data['cpu_time_std'] > 0 else ""
        cpu_str = f"{data['cpu_time_avg']:.1f}{cpu_std}ms" if data['cpu_time_avg'] > 0 else "N/A"
        mem_std = f"±{data['memory_std']:.1f}" if data['memory_std'] > 0 else ""
        mem_str = f"{data['memory_avg']:.1f}{mem_std}MB"
        print(f"{label:<30} {data['count']:>6} {latency_str:>16} {cpu_str:>16} {mem_str:>14}")
    print("="*90)

if __name__ == "__main__":
    results = load_results()
    print_summary(results)
    create_charts(results)
