import logging
import psutil
import subprocess
import inspect


def log_memory_and_disk_usage():
    """
    Logs the current memory and disk usage.
    """
    # Get the caller's frame
    caller_frame = inspect.stack()[1]
    caller_filename = caller_frame.filename
    caller_lineno = caller_frame.lineno

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
        logging.error(
            f"Error running du: {e.output.decode()} (called from {caller_filename}:{caller_lineno})"
        )

    logging.info(
        f"Memory usage: {current_memory_usage / (1024 * 1024)} MB / {total_memory / (1024 * 1024)} MB (called from {caller_filename}:{caller_lineno})"
    )
    logging.info(
        f"Disk usage for /root: {du_size} / {total_disk_root / (1024 * 1024)} MB (called from {caller_filename}:{caller_lineno})"
    )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log_memory_and_disk_usage()
