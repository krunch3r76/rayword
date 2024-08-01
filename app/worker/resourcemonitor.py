import threading
import psutil
import os
import logging
import time
import subprocess


class ResourceMonitor:
    def __init__(self):
        self.max_memory_usage = 0
        self.min_memory_usage = float("inf")  # Initialize to positive infinity
        self.max_disk_usage = 0
        self.min_disk_usage = float("inf")  # Initialize to positive infinity
        self.monitoring = True
        self.node_pid = os.getpid()
        self.monitor_thread = threading.Thread(
            target=self.monitor_resources, daemon=True
        )
        self.monitor_thread.start()

    def monitor_resources(self):
        while self.monitoring:
            # Memory usage
            vm_stats = psutil.virtual_memory()
            current_memory_usage = vm_stats.used
            self.max_memory_usage = max(self.max_memory_usage, current_memory_usage)
            self.min_memory_usage = min(self.min_memory_usage, current_memory_usage)

            # Disk usage
            current_disk_usage = self.get_disk_usage()
            if current_disk_usage is not None:
                self.max_disk_usage = max(self.max_disk_usage, current_disk_usage)
                self.min_disk_usage = min(self.min_disk_usage, current_disk_usage)

            # Logging (Uncomment if needed)
            # logging.info(
            #     f"Node {self.node_pid} memory usage: {current_memory_usage / (1024 * 1024)} MB"
            # )
            # logging.info(
            #     f"Node {self.node_pid} disk usage: {current_disk_usage / (1024 * 1024)} MB"
            # )
            time.sleep(0.1)

    def get_disk_usage(self):
        try:
            du_output = subprocess.check_output(
                ["du", "-sh", "/root"], stderr=subprocess.STDOUT
            )
            du_size = du_output.decode().split()[0]

            # Convert du_size to bytes (assuming the size is in kilobytes for simplicity)
            # Note: `du` can return sizes with different units (e.g., K, M, G).
            # This example assumes kilobytes (K). You may need to handle other units as needed.
            if du_size.endswith("K"):
                return int(float(du_size[:-1]) * 1024)
            elif du_size.endswith("M"):
                return int(float(du_size[:-1]) * 1024 * 1024)
            elif du_size.endswith("G"):
                return int(float(du_size[:-1]) * 1024 * 1024 * 1024)
            else:
                return int(du_size)  # Handle if it's already in bytes
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running du: {e.output.decode()}")
            return None

    def stop(self):
        self.monitoring = False
        self.monitor_thread.join()


# # Example usage
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     monitor = ResourceMonitor()
#     try:
#         time.sleep(5)  # Monitor for a short while
#     finally:
#         monitor.stop()
#         logging.info(f"Max memory usage: {monitor.max_memory_usage / (1024 * 1024)} MB")
#         logging.info(f"Min memory usage: {monitor.min_memory_usage / (1024 * 1024)} MB")
#         logging.info(f"Max disk usage: {monitor.max_disk_usage / (1024 * 1024)} MB")
#         logging.info(f"Min disk usage: {monitor.min_disk_usage / (1024 * 1024)} MB")
