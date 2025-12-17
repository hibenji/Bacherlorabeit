import time
import resource
import statistics

class PerformanceMonitor:
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.start_cpu_self = None
        self.end_cpu_self = None
        self.start_cpu_children = None
        self.end_cpu_children = None
        self.peak_memory_mb = 0

    def __enter__(self):
        self.start_time = time.time()
        self.start_cpu_self = resource.getrusage(resource.RUSAGE_SELF)
        self.start_cpu_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        self.end_cpu_self = resource.getrusage(resource.RUSAGE_SELF)
        self.end_cpu_children = resource.getrusage(resource.RUSAGE_CHILDREN)
        
        # Memory in MB (Linux gibt KB zurück)
        # Take max of self and children peak memory
        self.peak_memory_mb = max(
            self.end_cpu_self.ru_maxrss / 1024,
            self.end_cpu_children.ru_maxrss / 1024
        )

    def get_duration(self):
        return (self.end_time - self.start_time) * 1000  # ms

    def get_cpu_time(self):
        # User Time + System Time for both self and children
        u_self = self.end_cpu_self.ru_utime - self.start_cpu_self.ru_utime
        s_self = self.end_cpu_self.ru_stime - self.start_cpu_self.ru_stime
        u_children = self.end_cpu_children.ru_utime - self.start_cpu_children.ru_utime
        s_children = self.end_cpu_children.ru_stime - self.start_cpu_children.ru_stime
        return (u_self + s_self + u_children + s_children) * 1000  # ms

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