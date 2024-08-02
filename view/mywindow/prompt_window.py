# prompt_window.py

import curses
from .mywindow import MyWindow
import logging


class PromptWindow(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
        padding=None,
        x_padding: int = 0,
        y_padding: int = 0,
        ray_on_golem_version: str = "x.y.z",
        texts_per_worker: int = 0,
        network: str = "WHATEVERNETWORK",
        max_workers: int = 10,
        total_indexable_texts: int = 1000,
        total_text_count: int = 10000,
    ):
        super().__init__(
            stdscr,
            upper_left_y,
            upper_left_x,
            height,
            width,
            boxed,
            padding,
            x_padding,
            y_padding,
        )
        self.y_offset = y_padding + 1 if boxed else 0  # relative y offset

        self.ray_on_golem_version = ray_on_golem_version
        self._text_per_worker = texts_per_worker
        self.texts_per_worker = texts_per_worker
        self.network = network
        self.max_workers = max_workers
        self.total_indexable_texts = 1000
        self.total_index_texts = total_indexable_texts
        self.total_text_count = total_text_count

        self.field_keys = list(self.fields.keys())
        self.current_field_index = (
            0  # Start at the first modifiable field (texts_per_worker)
        )
        self._edit_mode = False
        self.select_mode = False
        self.temp_keyboard_input = ""

    @property
    def edit_mode(self):
        return self._edit_mode

    @edit_mode.setter
    def edit_mode(self, newval):
        self._edit_mode = newval
        self.select_mode = False

    @property
    def texts_per_worker(self):
        return self._texts_per_worker

    @texts_per_worker.setter
    def texts_per_worker(self, newval):
        if isinstance(newval, str):
            newval = int(newval)
        self._texts_per_worker = newval

    @property
    def fields(self):
        fields = {
            "version": f"Ray-on-Golem Version: {self.ray_on_golem_version}",
            "texts per worker": f"Texts per Worker: {self.texts_per_worker}",
            "network": f"Network: {self.network}",
            "max workers": f"Max Workers: {self.max_workers}",
            "total indexable texts": f"Total Indexable Texts: {self.total_indexable_texts}",
            "total text count": f"Total Text Count: {self.total_text_count}",
        }
        return fields

    def clear(self):
        self.y_offset = self.y_padding + 1 if self._boxed else 0
        super().clear()

    def draw(self):
        self.clear()
        highlight_attribute = curses.A_NORMAL
        highlight_edit_attribute = curses.A_NORMAL
        if self.select_mode:
            highlight_attribute = curses.A_REVERSE
        elif self.edit_mode:
            logging.debug("EDIT MODE")
            highlight_edit_attribute = curses.A_UNDERLINE
        else:
            highlight_attribute = curses.A_NORMAL

        for i, field_key in enumerate(self.field_keys):
            field = self.fields[field_key]
            colon_index = field.find(":")
            if i == self.current_field_index:
                if colon_index != -1:
                    segments = [
                        (field[:colon_index], highlight_attribute),
                        (": ", curses.A_NORMAL),
                        (field[colon_index + 2 :], highlight_edit_attribute),
                    ]
                else:
                    segments = [(field, curses.A_BOLD)]
            else:
                segments = [(field, curses.A_NORMAL)]
            self.add_line(segments, self.y_offset)
        self.refresh()

    def handle_key(self, key):
        start_signal = False
        if not self.edit_mode:
            if key == curses.KEY_UP:
                self.current_field_index = (self.current_field_index - 1) % len(
                    self.field_keys
                )
                while self.field_keys[self.current_field_index] not in [
                    "texts per worker",
                    "network",
                ]:
                    self.current_field_index = (self.current_field_index - 1) % len(
                        self.field_keys
                    )
            elif key == curses.KEY_DOWN:
                self.current_field_index = (self.current_field_index + 1) % len(
                    self.field_keys
                )
                while self.field_keys[self.current_field_index] not in [
                    "texts per worker",
                    "network",
                ]:
                    self.current_field_index = (self.current_field_index + 1) % len(
                        self.field_keys
                    )
            elif key == curses.KEY_RIGHT:
                field_being_edited = self.field_keys[self.current_field_index]
                logging.debug(
                    f"key right, current field being edited: {field_being_edited}"
                )
                self.edit_mode = True
            elif key in (curses.KEY_ENTER, 10, 13):
                start_signal = True
            if key in [curses.KEY_UP, curses.KEY_DOWN]:
                self.select_mode = True
            if key in [curses.KEY_UP, curses.KEY_DOWN] or key == curses.KEY_RIGHT:
                self.draw()
        else:  # edit mode
            if key in [curses.KEY_LEFT, curses.KEY_UP, curses.KEY_DOWN]:
                self.edit_mode = False
                self.select_mode = True
                self.draw()
            else:
                field_name = self.field_keys[self.current_field_index]
                if key in (curses.KEY_ENTER, 10, 13):
                    if field_name == "texts per worker":
                        self.texts_per_worker = self.temp_keyboard_input
                    self.edit_mode = False
                    self.select_mode = True
                    self.draw()
                elif field_name == "network":
                    if key == 32:
                        if self.network == "MAINNET":
                            self.network = "TESTNET"
                        else:
                            self.network = "MAINNET"
                    self.draw()
                elif field_name == "texts per worker":
                    self.temp_keyboard_input += chr(key)
                    self.texts_per_worker = self.temp_keyboard_input
                    self.draw()

        field_being_edited = self.field_keys[self.current_field_index]
        logging.debug(f"current field being edited: {field_being_edited}")
        return start_signal


def main(stdscr):
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    stdscr.refresh()

    prompt_window = PromptWindow(stdscr)
    prompt_window.draw()

    while True:
        key = stdscr.getch()
        if key == ord("q"):
            break
        prompt_window.handle_key(key)
        prompt_window.draw()
