# prompt_window.py
# move this outside of mywindow because it is a specialized version of it

import curses
from .mywindow import MyWindow
import logging
from config import Config
from queue import Queue


class PromptWindow(MyWindow):
    def __init__(
        self,
        to_controller: Queue,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = None,
        width: int = None,
        boxed: bool = False,
        padding=None,
        x_padding: int = 0,
        y_padding: int = 0,
    ):
        self.to_controller = to_controller
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
        self.y_offset = 0

        # Initialize the fields dictionary with default values
        self.fields = {
            "version": "x.y.z",
            "texts per worker": "-1",
            "network": "WHATEVERNETWORK",
            "max workers": "-10",
            "count indexable texts": "-1000",
            "count unindexed texts": "-10000",
            "minimum memory": "-1 GiB",
            "minimum cpu threads": "-1",
            "minimum storage": "-1 GiB",
            "max cpu per hour price": "-0.05",
            "max env per hour price": "-0.005",
            "shortcuts": "F2 : this screen / F3 : word browser",
        }

        self.fields_modified = set()

        self.field_keys = list(self.fields.keys())
        self.current_field_index = (
            0  # Start at the first modifiable field (texts per worker)
        )
        self._edit_mode = False
        self.select_mode = False
        self.temp_keyboard_input = ""
        self._config = None
        self.last_mode_was_edit = False
        self.pending_config_changes = dict()

    def get_fields_modified(self):
        # iterate over list of field names modified and assign values to dict
        self.pending_config_changes = dict()
        for field_name in self.fields_modified:
            self.pending_config_changes[field_name] = self.fields[field_name]
        return self.pending_config_changes

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        self.update_fields()

    def update_fields(self):
        if self.config is not None:
            for key in self.fields:
                # Replace spaces with underscores for the attribute check
                attr_key = key.replace(" ", "_")

                # Check if the transformed key (attr_key) is an attribute of the named tuple (self.config)
                if hasattr(self.config, attr_key):
                    # Retrieve the value using the transformed key and update the dictionary
                    self.fields[key] = getattr(self.config, attr_key)
            self.draw()

    # def update_fields(self, field_dict):
    #     """Update the fields based on the provided dictionary."""
    #     for key, value in field_dict.items():
    #         if key in self.fields:
    #             self.fields[key] = value
    #     self.draw()

    @property
    def edit_mode(self):
        return self._edit_mode

    @edit_mode.setter
    def edit_mode(self, newval):
        self._edit_mode = newval
        self.select_mode = False
        if newval is False:
            for key, value in self.pending_config_changes.items():
                self.to_controller.put_nowait(
                    {"signal": "update config", "msg": {"key": key, "value": value}}
                )

    def clear(self):
        self.y_offset = 0
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
            # titecased
            field_name = field_key.replace("_", " ").title()
            field_value = self.fields[field_key]
            field = f"{field_name}: {field_value}"
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
            self.y_offset += 1
        self.y_offset += 1
        self.add_line("PRESS ENTER TO BEGIN INDEXING", self.y_offset)
        self.y_offset += 1
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
                    "max workers"
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
                    "max workers"
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
                self.fields_modified.add(field_name)
                if key in (curses.KEY_ENTER, 10, 13):
                    if field_name in [ "texts per worker", "max workers" ]:
                        self.fields[field_name] = self.temp_keyboard_input
                    self.edit_mode = False
                    self.select_mode = True
                    self.draw()
                elif field_name == "network":
                    if key == 32:
                        if self.fields[field_name] == "MAINNET":
                            self.fields[field_name] = "TESTNET"
                        else:
                            self.fields[field_name] = "MAINNET"
                    self.draw()
                elif field_name in ["texts per worker", "max workers"]:
                    if key == curses.KEY_BACKSPACE or key == 127:
                        self.temp_keyboard_input = self.temp_keyboard_input[:-1]
                    elif chr(key).isdigit():
                        self.temp_keyboard_input += chr(key)
                    self.pending_config_changes[field_name] = self.temp_keyboard_input
                    self.fields[field_name] = self.temp_keyboard_input
                    self.draw()

        field_being_edited = self.field_keys[self.current_field_index]
        logging.debug(f"current field being edited: {field_being_edited}")
        return start_signal
