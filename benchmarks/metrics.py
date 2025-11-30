import time
import resource
import statistics

class PerformanceMonitor:
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.start_cpu = None
        self.end_cpu = None
        self.peak_memory_mb = 0

    def __enter__(self):
        self.start_time = time.time()
        self.start_cpu = resource.getrusage(resource.RUSAGE_SELF)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        self.end_cpu = resource.getrusage(resource.RUSAGE_SELF)
        
        # Memory in MB (Linux gibt KB zurück)
        self.peak_memory_mb = self.end_cpu.ru_maxrss / 1024 

    def get_duration(self):
        return (self.end_time - self.start_time) * 1000  # ms

    def get_cpu_time(self):
        # User Time + System Time
        u = self.end_cpu.ru_utime - self.start_cpu.ru_utime
        s = self.end_cpu.ru_stime - self.start_cpu.ru_stime
        return (u + s) * 1000 # ms

    def get_memory(self):
        return self.peak_memory_mb

def print_stats(latencies, cpu_times=None, memories=None):
    print("\n--- RESULTS ---")
    print(f"Count: {len(latencies)}")
    print(f"Avg Duration:   {statistics.mean(latencies):.2f} ms")
    print(f"StdDev Duration:{statistics.stdev(latencies):.2f} ms")
    
    if cpu_times:
        print(f"Avg CPU Time:   {statistics.mean(cpu_times):.2f} ms")
    if memories:
        print(f"Max Memory:     {max(memories):.2f} MB")