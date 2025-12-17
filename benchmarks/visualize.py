import json
import os
import argparse
import matplotlib.pyplot as plt

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
                    results[label] = data[-1]
    return results

def create_charts(results, test_type):
    if not results:
        print("No results found!")
        return
    
    labels = list(results.keys())
    latencies = [get_latency(results[l]) for l in labels]
    cpu_times = [get_cpu_time(results[l]) for l in labels]
    memories = [get_memory(results[l]) for l in labels]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Benchmark Comparison ({test_type.upper()})", fontsize=14, fontweight='bold')
    
    colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
    
    ax1 = axes[0]
    bars1 = ax1.bar(range(len(labels)), latencies, color=colors[:len(labels)])
    ax1.set_ylabel('Latency (ms)')
    ax1.set_title('End-to-End Latency')
    ax1.set_xticks(range(len(labels)))
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars1, latencies):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    ax2 = axes[1]
    bars2 = ax2.bar(range(len(labels)), cpu_times, color=colors[:len(labels)])
    ax2.set_ylabel('CPU Time (ms)')
    ax2.set_title('CPU Time')
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars2, cpu_times):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    ax3 = axes[2]
    bars3 = ax3.bar(range(len(labels)), memories, color=colors[:len(labels)])
    ax3.set_ylabel('Memory (MB)')
    ax3.set_title('Peak Memory')
    ax3.set_xticks(range(len(labels)))
    ax3.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    for bar, val in zip(bars3, memories):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                 f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    output_path = os.path.join(current_dir, f"benchmark_comparison_{test_type}.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")
    plt.show()

def print_summary(results, test_type):
    print(f"\n{'='*70}")
    print(f"BENCHMARK COMPARISON ({test_type.upper()})")
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
    parser = argparse.ArgumentParser(description="Visualize benchmark results")
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
