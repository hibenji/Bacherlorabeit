import subprocess
import os
import sys
import time

# --- Configuration ---
# Number of times to run EACH script
ITERATIONS = 20

# Wait time between OpenWhisk single.py invocations for cold starts (12 minutes)
OPENWHISK_COLD_START_WAIT_SECONDS = 720

# Configurations to test
CONFIGS = ["openwhisk"]

BENCHMARKS = [
    # "single.py",
    "stream.py", 
    # "batch.py",
    # "randoms.py"
]

# Path to the virtual environment python
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv/bin/python3")
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable  # Fallback to current python if venv not found

def run_benchmark(config, benchmark, iteration):
    script_path = os.path.join(config, benchmark)
    if not os.path.exists(script_path):
        print(f"Skipping {script_path} (not found)")
        return

    print(f"\n{'='*60}")
    print(f"CONFIG: {config} | SCRIPT: {benchmark} | RUN: {iteration}/{ITERATIONS}")
    print(f"{'='*60}")

    start_time = time.time()
    try:
        # Run from the benchmarks directory
        subprocess.run([VENV_PYTHON, script_path], check=True)
        duration = time.time() - start_time
        print(f"Done in {duration:.2f}s")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(1)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print(f"Starting benchmark suite: {CONFIGS}")
    print(f"Benchmarks: {BENCHMARKS}")
    print(f"Iterations per script: {ITERATIONS}")
    print(f"Using Python: {VENV_PYTHON}")
    
    total_start = time.time()
    
    try:
        for benchmark in BENCHMARKS:
            for config in CONFIGS:
                for i in range(1, ITERATIONS + 1):
                    # For OpenWhisk single.py, wait 12 minutes between invocations for cold starts
                    if config == "openwhisk" and benchmark == "single.py" and i > 1:
                        print(f"\n*** Waiting {OPENWHISK_COLD_START_WAIT_SECONDS // 60} minutes for OpenWhisk container to become cold... ***")
                        for remaining in range(OPENWHISK_COLD_START_WAIT_SECONDS, 0, -60):
                            print(f"  Time remaining: {remaining // 60} minute(s)...")
                            time.sleep(min(60, remaining))
                        print("Wait complete. Invoking function (should be cold start)...")
                    
                    run_benchmark(config, benchmark, i)
    except KeyboardInterrupt:
        print("\nSuite aborted.")
    
    total_duration = time.time() - total_start
    print(f"\nAll requested benchmarks finished in {total_duration/60:.2f} minutes.")

if __name__ == "__main__":
    main()
