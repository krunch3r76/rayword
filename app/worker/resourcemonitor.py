# memorymonitor.py
# import ray
# import psutil
# import logging
# import time
import threading
import psutil
import os
import logging
import time


class ResourceMonitor:
    def __init__(self):
        self.max_memory_usage = 0
        self.max_disk_usage = 0
        self.monitoring = True
        self.node_pid = os.getpid()
        self.monitor_thread = threading.Thread(
            target=self.monitor_resources, daemon=True
        )
        self.monitor_thread.start()

    def monitor_resources(self):
        while self.monitoring:
            vm_stats = psutil.virtual_memory()
            current_memory_usage = vm_stats.used
            self.max_memory_usage = max(self.max_memory_usage, current_memory_usage)

            disk_stats = psutil.disk_usage("/root")
            current_disk_usage = disk_stats.used
            self.max_disk_usage = max(self.max_disk_usage, current_disk_usage)

            # logging.info(
            #     f"Node {self.node_pid} memory usage: {current_memory_usage / (1024 * 1024)} MB"
            # )
            # logging.info(
            #     f"Node {self.node_pid} disk usage: {current_disk_usage / (1024 * 1024)} MB"
            # )
            time.sleep(0.1)

    def stop(self):
        self.monitoring = False
        self.monitor_thread.join()


# @ray.remote
# class MemoryMemory:
#     def __init__(self):
#         self.max_memory_usage = 0
#         self.process = psutil.Process()

#     def monitor_memory(self):
#         while True:
#             current_memory_usage = self.process.memory_info().rss
#             self.max_memory_usage = max(self.max_memory_usage, current_memory_usage)
#             logging.info(
#                 f"Current memory usage: {current_memory_usage / (1024 * 1024)} MB"
#             )
#             time.sleep(0.1)

#     def get_max_memory_usage(self):
#         return self.max_memory_usage
