import queue
import subprocess
import threading
import os
import pty


class ProcessTerminated(Exception):
    pass


class ProcessQueue:
    """Execute a subprocess and queue its output line by line non-blocking using a pseudo-terminal"""

    def __init__(self, cmdline):
        """Initialize ProcessQueue with a shared queue and invoke the function to launch the command

        Args:
            cmdline: a sequence (e.g., list) of text commands representing the full command line to execute
        """
        self._queue = queue.Queue()
        self.master_fd, self.slave_fd = pty.openpty()  # Create a pseudo-terminal pair

        self._process = subprocess.Popen(
            cmdline,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            stdin=self.slave_fd,  # Use the slave end of the PTY for stdin
            bufsize=1,
            text=True,
            close_fds=True,
            env=os.environ,  # Ensure the subprocess inherits the current environment
        )
        os.close(self.slave_fd)  # Close the slave end in the parent process

        self.return_code = None

        # Start a thread to read from the master end of the PTY
        threading.Thread(target=self._enqueue_output, daemon=True).start()

    def _enqueue_output(self):
        """Helper function to read lines from the subprocess output and enqueue them"""
        while True:
            try:
                output = os.read(self.master_fd, 1024).decode()
                if output == "":
                    break
                for line in output.splitlines():
                    self._queue.put_nowait(line + "\n")
            except OSError:
                break
        os.close(self.master_fd)

    def get_nowait(self):
        """Return a line from the queue or throw one of two exceptions

        Returns:
            A line of text terminated by a newline

        Raises:
            queue.Empty: There is currently no line to read from the queue
            ProcessTerminated: There cannot be any more lines to read from the queue; the process has terminated.
        """
        if self.return_code is None:
            self.return_code = self._process.poll()

        try:
            line = self._queue.get_nowait()
        except queue.Empty as exc:
            if self.return_code is not None:
                raise ProcessTerminated from exc
            raise
        else:
            return line

    def get_return_code(self):
        """Return the return code of the subprocess if it has terminated, else None"""
        if self.return_code is None:
            self.return_code = self._process.poll()
        return self.return_code


# Custom exception to handle process termination
class ProcessTerminated(Exception):
    pass
