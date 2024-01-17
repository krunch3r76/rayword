# rayword/util/ray.py
import logging
import subprocess
from constants import RAY_DEBUG_LOGFILE, RAYCMD_TIMEOUT


def ray_down(timeout=RAYCMD_TIMEOUT):
    """call ray down to shutdown any existing cluster

    :param timeout: number of seconds to wait before giving up
    """
    command = ["ray", "down", "golem-cluster.yaml", "--yes"]
    logging.debug(f"running {' '.join(command)}")
    timedout = True
    timedout_count = 0
    while timedout and timedout_count < 1:
        try:
            subprocess.run(command, timeout=timeout, check=True)
            timedout = False
        except subprocess.TimeoutExpired:
            logging.debug("ray down timed out")
            timedout_count += 1
        except subprocess.CalledProcessError as e:
            logging.debug(f"ray down failed with return code {e.returncode}")
            timedout_count += 1
        else:
            logging.debug("ray shut down")

    # proceed to ray up even if timedout


def ray_up(timeout=RAYCMD_TIMEOUT):
    """start a new ray instance, shutting down any existing cluster first

    :param timeout: number of seconds to wait for the process to complete before retrying

    returns: the suggested ssh line along with arguments to connect to the head node
    """
    # shut down any existing cluster
    ray_down()
    # TODO: capture provider info on bad exit code
    process_successful = False
    ssh_line = None
    while not process_successful:
        try:
            # Run the command and capture output
            command = ["ray", "up", "golem-cluster.yaml", "--yes"]
            logging.debug(f"running {' '.join(command)}")

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            # Capture and stream stdout
            stdout_lines = []
            while True:
                line_output = process.stdout.readline()
                if line_output == "" and process.poll() is not None:
                    break
                if line_output:
                    print(
                        f"{line_output.strip()}", end="\r", flush=True
                    )  # Stream to console
                    print()
                    stdout_lines.append(line_output.strip())  # Capture for later

            # Wait for the process to finish and get the exit code
            try:
                returncode = process.wait(timeout=timeout)
                if returncode == 0:
                    logging.debug("ray_up exited with 0 status")
                    process_successful = True
            except subprocess.TimeoutExpired:
                continue
            if returncode != 0:
                # Process did not succeed
                logging.error(f"ray up failed with error: {process.stderr.read()}")
            else:
                process_successful = True
        except Exception as e:
            logging.debug(f"ray up failed {type(e)} with error: {e.stderr}")
            continue

        # load the ray_on_golem debug file into memory
        with open(RAY_DEBUG_LOGFILE) as f:
            for line in f:
                if line.startswith("ssh"):
                    ssh_line = line

    return ssh_line
