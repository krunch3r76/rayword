# start_indexing/controller.py

from view.view import View
from processqueue import ProcessQueue, ProcessTerminated
from queue import Queue, Empty
from main.model import MainModel
import queue
import logging
import time
from app.worker.util.resource_loader import load_resource
from wordbrowser.browse import extract_sentence_with_context


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
        # self._outputfile = open("output.txt", "w")
        # self.cmds = [["cat", "somewords.txt"]]
        self.model = MainModel("./data/main.db", "./data/paths.db")

    def _process_signal_from_view(self, signal_from_view):
        signal_quit = False
        if signal_from_view["signal"] == "cmd" and signal_from_view["msg"] == "quit":
            signal_quit = True
        elif signal_from_view["signal"] == "search":
            wordlist = self.model.search_words(signal_from_view["msg"])
            self.to_view.put_nowait({"signal": "wordlist", "msg": wordlist})
        elif signal_from_view["signal"] == "lookupword":
            IP_TO_GUTENBERG_TEXTS = "69.55.231.8"
            word = signal_from_view["msg"]
            wordinfos = self.model.get_paths_for_word(word)
            # path, textnum, offsets
            textnum_to_text_to_offsets = []
            for path, textnum, offsets in wordinfos:
                text, timedout = load_resource("http://" + IP_TO_GUTENBERG_TEXTS + path)
                if text is not None:
                    textnum_to_text_to_offsets.append(
                        (
                            textnum,
                            text,
                            offsets,
                        )
                    )
            textnum_to_contexts = []
            for textnum, text, offsets in textnum_to_text_to_offsets:
                for offset in offsets:
                    context = extract_sentence_with_context(text, offset)
                    textnum_to_contexts.append(
                        (
                            textnum,
                            context,
                        )
                    )
            for textnum, context in textnum_to_contexts:
                logging.debug(context)
                logging.debug("N E X T")
            self.to_view.put_nowait({"signal": "wordinfos", "msg": textnum_to_contexts})
        return signal_quit

    def __call__(self):
        last_return_code = 0
        signal_quit = False
        for cmd in self.cmds:
            if signal_quit:
                break
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
                    # self.to_view.put_nowait({"signal": "cmdout", "msg": line})
                    self.to_view.put_nowait({"signal": "addword", "msg": line.rstrip()})
                    self._outputfile.write(line + "\n")
                    # self.view.receive_signal({"signal": "cmdout", "msg": line})
                try:
                    signal_from_view = self.from_view.get_nowait()
                except queue.Empty:
                    pass
                else:
                    signal_quit = self._process_signal_from_view(signal_from_view)
                    if signal_quit:
                        break
                self.view.update()
                time.sleep(0.01)
            self.to_view.put_nowait({"signal": "wake", "msg": None})

        while True:
            try:
                signal_from_view = self.from_view.get_nowait()
            except queue.Empty:
                pass
            else:
                signal_quit = self._process_signal_from_view(signal_from_view)
                if signal_quit:
                    break
            self.view.update()
            time.sleep(0.01)

        def __del__(self):
            del self.view
            self._outputfile.close()
