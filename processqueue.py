import subprocess
import queue
import select
import time
import os


class ProcessTerminated(Exception):
    """Indicate that an empty queue is no longer readable as it will never be filled further"""

    def __init__(self, message="Empty queue and process has terminated"):
        self.message = message


class ProcessQueue:
    """Execute a subprocess and queue its output line by line non-blocking"""

    def __init__(self, cmdline):
        """Initialize ProcessQueue with a shared queue and invoke the function to launch the command

        Args:
            cmdline: a sequence (e.g., list) of text commands representing the full command line to execute
        """
        self._queue = queue.Queue()
        self._process = subprocess.Popen(
            cmdline,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            text=True,
        )
        self.stdout_fd = self._process.stdout.fileno()
        self.stderr_fd = self._process.stderr.fileno()
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        self.return_code = None

    def _enqueue_output(self):
        """Helper function to read lines from the subprocess output and enqueue them"""
        ready_fds, _, _ = select.select([self.stdout_fd, self.stderr_fd], [], [], 0.1)

        for fd in ready_fds:
            try:
                if fd == self.stdout_fd:
                    data = os.read(self.stdout_fd, 1024).decode()
                    self.stdout_buffer += data
                    while "\n" in self.stdout_buffer:
                        line, self.stdout_buffer = self.stdout_buffer.split("\n", 1)
                        self._queue.put_nowait(line + "\n")
                elif fd == self.stderr_fd:
                    data = os.read(self.stderr_fd, 1024).decode()
                    self.stderr_buffer += data
                    while "\n" in self.stderr_buffer:
                        line, self.stderr_buffer = self.stderr_buffer.split("\n", 1)
                        self._queue.put_nowait(line + "\n")
            except UnicodeDecodeError:
                pass

    def get_nowait(self):
        """Return a line from a queue or throw one of two exceptions

        Returns:
            A line of text terminated by a newline

        Raises:
            queue.Empty: There is currently no line to read from the queue
            ProcessTerminated: There cannot be any more lines to read from the queue;
                the process has terminated.
        """
        # First, try to enqueue any new output
        self._enqueue_output()

        try:
            line = self._queue.get_nowait()
        except queue.Empty as exc:
            if self._process.poll() is not None:
                self.return_code = self._process.returncode
                raise ProcessTerminated from exc
            raise
        else:
            return line

    def get_return_code(self):
        """Return the return code of the subprocess if it has terminated, else None"""
        if self._process.poll() is not None:
            self.return_code = self._process.returncode
        return self.return_code


# Example usage
if __name__ == "__main__":
    processQueue = ProcessQueue(
        cmdline=["/home/golem/.local/bin/golemsp", "run", "--payment-network=testnet"]
    )

    while True:
        try:
            time.sleep(0.01)
            next_line = processQueue.get_nowait()
        except queue.Empty:
            pass
        except ProcessTerminated:
            print("Process terminated! and queue is empty")
            break
        else:
            print(next_line, end="")

    return_code = processQueue.get_return_code()
    print(f"Process exited with return code: {return_code}")
