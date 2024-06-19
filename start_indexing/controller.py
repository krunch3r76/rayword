# start_indexing/controller.py

from view.view import View
from processqueue import ProcessQueue, ProcessTerminated
from queue import Queue, Empty
import queue
import logging
import time


class Controller:
    def __init__(self):
        self.cmds = [
            ["echo", "'Hello, worlds!'"],
            ["rm", "-f", "app/output/*"],
            ["python3", "main/update_or_insert_paths.py"],
            [
                "python3",
                "main/prepare_unsearched_paths_json.py",
                "golem-cluster.yaml",
                "--batch-size",
                "50",
            ],
            ["ray", "up", "golem-cluster.yaml", "--yes"],
            [
                "ray",
                "rsync-up",
                "golem-cluster.yaml",
                "./app/input/",
                "/root/app/input/",
            ],
            [
                "ray",
                "submit",
                "golem-cluster.yaml",
                "./rayword.py",
                "--enable-console-logging",
            ],
            [
                "ray",
                "rsync-down",
                "golem-cluster.yaml",
                "/root/app/output/",
                "./app/output",
            ],
            ["python3", "main/import_ray_results.py"],
            ["ray", "down", "golem-cluster.yaml", "--yes"],
        ]
        self.from_view = Queue()
        self.to_view = Queue()
        self.view = View(self.from_view, self.to_view)
        self._outputfile = open("output.txt", "w")

    def __call__(self):
        last_return_code = 0
        for cmd in self.cmds:
            if last_return_code != 0:
                break
            self.to_view.put_nowait({"signal": "cmdstart", "msg": " ".join(cmd)})
            # self.view.receive_signal({"signal": "cmdstart", "msg": " ".join(cmd)})
            pq = ProcessQueue(cmd)
            while True:
                try:
                    line = pq.get_nowait()
                except queue.Empty:
                    pass
                except ProcessTerminated:
                    last_return_code = pq.get_return_code()
                    self.to_view.put_nowait(
                        {"signal": "cmdend", "msg": last_return_code}
                    )
                    break
                    # self.view.receive_signal({"signal": "cmdend", "msg": rc})
                else:
                    self.to_view.put_nowait({"signal": "cmdout", "msg": line})
                    self._outputfile.write(line + "\n")
                    # self.view.receive_signal({"signal": "cmdout", "msg": line})
                try:
                    signal_from_view = self.from_view.get_nowait()
                except queue.Empty:
                    pass
                else:
                    if (
                        signal_from_view["signal"] == "cmd"
                        and signal_from_view["msg"] == "quit"
                    ):
                        break
                self.view.update()
                time.sleep(0.01)

        logging.debug("--------------------")
        while True:
            try:
                signal_from_view = self.from_view.get_nowait()
            except queue.Empty:
                pass
            else:
                if (
                    signal_from_view["signal"] == "cmd"
                    and signal_from_view["msg"] == "quit"
                ):
                    break
            self.view.update()
            time.sleep(0.01)

        def __del__(self):
            del self.view
            self._outputfile.close()
