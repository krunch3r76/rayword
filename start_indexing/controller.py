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
    def __init__(self, cmds):
        self.cmds = cmds
        self.signal_start = False
        self.cmds_started = False
        self.from_view = Queue()
        self.to_view = Queue()
        self.view = View(self.from_view, self.to_view)
        self._outputfile = open("output.txt", "w")
        # self.cmds = [["cat", "somewords.txt"]]
        self.model = MainModel("./data/main.db", "./data/paths.db")
        self.result_generator = None
        self.result_word = ""

    def daisy_chain_offsets(self, ebook_details):
        # Flatten the list of details with offsets from all ebook_detail objects
        all_details = []
        for detail in ebook_details:
            for offset in detail["details"]["offsets"]:
                all_details.append(
                    {
                        "path": detail["details"]["path"],
                        "title": detail["details"]["title"],
                        "authors": detail["details"]["authors"],
                        "offset": offset,
                    }
                )

        IP_TO_GUTENBERG_TEXTS = "69.55.231.8"
        # Generator loop
        index = 0
        num_details = len(all_details)
        cache = {}
        consecutive_timeouts = 0
        import re

        pattern = r"\r?\n"
        while True:
            cache_index = index % num_details
            detail = all_details[cache_index]

            if cache_index in cache:
                # Retrieve from cache
                cached_detail = cache[cache_index]
                consecutive_timeouts = 0  # Reset timeouts on successful retrieval
            else:
                # Generate new entry
                url = f"http://{IP_TO_GUTENBERG_TEXTS}{detail['path']}"
                logging.debug(url)
                content, timedout = load_resource(url)

                if timedout:
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= num_details:
                        raise Exception("All indices have timed out.")
                    continue  # Skip incrementing the index and try the next one

                extracted_text = extract_sentence_with_context(
                    content, detail["offset"]
                )
                cached_detail = {
                    "index": index,  # This is the index that will be returned
                    "path": detail["path"],
                    "title": detail["title"],
                    "authors": detail["authors"],
                    "offset": detail["offset"],
                    "text": re.split(pattern, extracted_text),
                }
                cache[cache_index] = cached_detail
                consecutive_timeouts = 0  # Reset timeouts on successful download

            yield index, cached_detail
            index += 1

    def _process_signal_from_view(self, signal_from_view):
        signal_quit = False
        if signal_from_view["signal"] == "cmd" and signal_from_view["msg"] == "quit":
            signal_quit = True
        elif signal_from_view["signal"] == "search":
            wordlist = self.model.search_words(signal_from_view["msg"])
            self.to_view.put_nowait({"signal": "wordlist", "msg": wordlist})
        elif signal_from_view["signal"] == "lookupword":
            newset = False
            word = signal_from_view["msg"]
            if self.result_word != word:
                ebook_details, offset_count = self.model.get_ebook_details_for_word(
                    word, "./data/GUTINDEX.ALL"
                )
                self.result_word = word
                newset = True
                self.result_generator = self.daisy_chain_offsets(ebook_details)
            # logging.debug(ebook_details)

            # logging.debug(f"{ebook_details}")
            # logging.debug(f"total count: {offset_count}")
            # path, textnum, offsets
            index, cached_detail = next(self.result_generator)
            self.to_view.put_nowait(
                {
                    "signal": "next word result",
                    "msg": {"index": index, "detail": cached_detail, "newset": newset},
                }
            )
        elif (
            signal_from_view["signal"] == "cmd"
            and signal_from_view["msg"] == "start ray"
        ):
            self.signal_start = True
        return signal_quit

    def run_commands(self):
        self.cmds_started = True
        logging.debug("cmds started")
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
                    self.to_view.put_nowait({"signal": "cmdout", "msg": line})
                    # self.to_view.put_nowait({"signal": "addword", "msg": line.rstrip()})
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
                time.sleep(0.001)
            self.to_view.put_nowait({"signal": "wake", "msg": None})

    def __call__(self):
        while True:
            try:
                signal_from_view = self.from_view.get_nowait()
            except queue.Empty:
                pass
            else:
                signal_quit = self._process_signal_from_view(signal_from_view)
                if signal_quit:
                    break
                if self.signal_start and not self.cmds_started:
                    self.run_commands()
            self.view.update()
            time.sleep(0.01)

    def __del__(self):
        del self.view
        self._outputfile.close()
