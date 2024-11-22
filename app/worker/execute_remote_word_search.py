import ray
import logging
import os
from .wordsearch import WordSearcher
from .resourcemonitor import ResourceMonitor

@ray.remote
def execute_remote_word_search(paths_table, path_prefix=None, enable_logging=False):
    """
    Executes a search for words in the given paths, run as a Ray remote function.

    Args:
        paths_table (list): List of dictionaries representing path records.
        path_prefix (str, optional): Optional prefix for paths.
        enable_logging (bool): Flag to enable detailed logging.

    Returns:
        serialization of WordSearcher to compressed json
    
    Notes:
        called by app Controller via TaskSubmitter
    """

    runtime_context = ray.get_runtime_context()
    
    node_id = str(runtime_context.node_id)
    job_id = str(runtime_context.job_id)
    worker_id = os.getpid()
    node_ip = ray.util.get_node_ip_address()

    # Create a unique prefix for this worker's logs
    log_prefix = f"[Node:{node_id[:8]}|Worker:{worker_id}] "
    # Configure logging
    logger = logging.getLogger(f"worker_{worker_id}")
    if not logger.handlers:
        logger.propagate = False  # Prevent log propagation to avoid duplication
        if enable_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"%(asctime)s - {log_prefix}%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    logger.debug(f"Starting task. Node ID: {node_id}, Job ID: {job_id}, IP: {node_ip}")

    resource_monitor = ResourceMonitor()

    EXCLUSIONS_FILE = "/root/app/worker/exclusions.txt"
    current_directory = os.getcwd()
    try:
        with open(EXCLUSIONS_FILE, "r") as file:
            exclusions = {line.strip() for line in file}
    except FileNotFoundError:
        logger.error(f"Exclusions file '{EXCLUSIONS_FILE}' not found in directory '{current_directory}'.")
        exclusions = set()

    word_searcher = WordSearcher(
        paths_table, path_prefix=path_prefix, exclude_words=exclusions
    )

    word_search_results = word_searcher()

    resource_monitor.stop()

    word_search_results.details = { 
        "min_mem_mb": f"{resource_monitor.min_memory_usage / (1024 * 1024)}",
        "max_mem_mb": f"{resource_monitor.max_memory_usage / (1024 * 1024)}",
        "min_disk_mb": f"{resource_monitor.min_disk_usage / (1024 * 1024)}",
        "max_disk_mb": f"{resource_monitor.max_disk_usage / (1024 * 1024)}",
        "ip": f"{node_ip}",
        "pid": f"{os.getpid()}",
        "node_id": node_id,
        "job_id": job_id,
        "worker_id": worker_id
    }

    logger.debug(f"Task completed. PID: {os.getpid()}")
    return word_search_results.to_compressed_json()
