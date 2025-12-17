import json
import os
import argparse
import matplotlib.pyplot as plt
import statistics

current_dir = os.path.dirname(os.path.abspath(__file__))

BENCHMARKS = {
    "local": "Local (In-Memory)",
    "local_minio_import": "Local + MinIO (Import)",
    "local_minio": "Local + MinIO (Subprocess)",
    "openwhisk": "OpenWhisk"
}

TEST_TYPES = ["single", "stream", "batch", "random"]

def get_latency(data):
    if "server_duration_ms" in data and data["server_duration_ms"] > 0:
        return data["server_duration_ms"]
    elif "client_latency_ms" in data:
        return data["client_latency_ms"]
    elif "latency_avg_ms" in data:
        return data["latency_avg_ms"]
    return data.get("latency_ms", 0)

def get_cpu_time(data):
    return data.get("cpu_time_ms", data.get("cpu_time_avg_ms", 0))

def get_memory(data):
    if "memory_limit_mb" in data and data["memory_limit_mb"] > 0:
        return data["memory_limit_mb"]
    return data.get("memory_mb", data.get("memory_avg_mb", 0))

def load_results(test_type):
    results = {}
    filename = f"results_{test_type}.json"
    
    for folder, label in BENCHMARKS.items():
        path = os.path.join(current_dir, folder, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                if data:
                    latencies = [get_latency(d) for d in data]
                    cpu_times = [get_cpu_time(d) for d in data]
                    memories = [get_memory(d) for d in data]
                    
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

def create_charts(results, test_type):
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
    fig.suptitle(f"Benchmark Comparison - {test_type.upper()} (Averages)", fontsize=14, fontweight='bold')
    
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    
    ax1 = axes[0]
    bars1 = ax1.bar(range(len(labels)), latencies, color=colors[:len(labels)], yerr=latency_stds, capsize=5)
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('Avg Latency')
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(labels)), cpu_times, color=colors[:len(labels)], yerr=cpu_stds, capsize=5)
    ax2.set_ylabel('CPU Time (ms)')
    ax2.set_title('Avg CPU Time')
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    
    ax3 = axes[2]
    bars3 = ax3.bar(range(len(labels)), memories, color=colors[:len(labels)], yerr=memory_stds, capsize=5)
    ax3.set_ylabel('Memory (MB)')
    ax3.set_title('Avg Memory')
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    
    plt.tight_layout()
    
    output_path = os.path.join(current_dir, f"benchmark_comparison_{test_type}_avg.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    plt.show()

def print_summary(results, test_type):
    print(f"\n{'='*90}")
    print(f"BENCHMARK COMPARISON - {test_type.upper()} (AVERAGES)")
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
    parser = argparse.ArgumentParser(description="Visualize benchmark results (averages)")
    parser.add_argument("--type", "-t", choices=TEST_TYPES, default="single",
                        help="Test type to visualize (single, stream, batch, random)")
    args = parser.parse_args()
    
    results = load_results(args.type)
    if results:
        print_summary(results, args.type)
        create_charts(results, args.type)
    else:
        print(f"No results found for test type: {args.type}")
        print(f"Looking for: results_{args.type}.json in each benchmark folder")
