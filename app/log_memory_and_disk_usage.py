import subprocess
import psutil
import logging


def log_memory_and_disk_usage():
    """
    Logs the current memory and disk usage.
    """
    # memory
    vm_stats = psutil.virtual_memory()
    current_memory_usage = vm_stats.used
    total_memory = vm_stats.total

    # disk
    du_size = "?"
    total_disk_root = "?"
    try:
        du_output = subprocess.check_output(
            ["du", "-sh", "/root"], stderr=subprocess.STDOUT
        )
        du_size = du_output.decode().split()[0]

        # total disk
        disk_stats_root = psutil.disk_usage("/root")
        total_disk_root = disk_stats_root.total
    except subprocess.CalledProcessError as e:
        logging.error(f"Error dunning du: {e.output.decode()}")

    logging.info(
        f"Memory usage: {current_memory_usage / (1024*1024)} MB / {total_memory / (1024 * 1024)} MB"
    )
    logging.info(
        f"Disk usage for /root: {du_size} / {total_disk_root / (1024 * 1024)} MB"
    )
