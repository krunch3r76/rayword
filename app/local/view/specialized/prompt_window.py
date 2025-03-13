# prompt_window.py
# move this outside of mywindow because it is a specialized version of it

import curses
from ..mywindow.mywindow import MyWindow
import logging
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
        self.field_store = {
            "version": "x.y.z",
            "texts per worker": "-1",
            "network": "WHATEVERNETWORK",
            "max workers": "-10",
            "count indexable texts": "-1",
            "count unindexed texts": "-1",
            "minimum memory": "-1 GiB",
            "minimum cpu threads": "-1",
            "minimum storage": "-1 GiB",
            "max cpu per hour price": "-0.05",
            "max env per hour price": "-0.005",
            "shortcuts": "F2 : this screen / F3 : word browser",
        }

        # Map field_store keys to Config attributes
        self.field_mapping = {
            "version": "version",
            "texts per worker": "texts_per_worker",
            "network": "network",
            "max workers": "max_workers",
            "count indexable texts": "count_indexable_texts",
            "count unindexed texts": "count_unindexed_texts",
            "minimum memory": "min_mem_gib",
            "minimum cpu threads": "min_cpu_threads",
            "minimum storage": "min_storage_gib",
            "max cpu per hour price": "max_cpu_per_hour_price",
            "max env per hour price": "max_env_per_hour_price",
        }

        self.fields_modified = set()

        self.field_keys = list(self.field_store.keys())
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
            config_attr = self.field_mapping.get(field_name)
            if config_attr:
                value = self.field_store[field_name]
                if config_attr.endswith('_gib'):
                    value = value.replace(' GiB', '')
                self.pending_config_changes[config_attr] = value
        return self.pending_config_changes

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        """
        Set the configuration for the prompt window and update the field store.

        This method sets the internal configuration object and updates the field store
        with values from the new configuration. It also redraws the window to reflect
        the changes.

        Args:
            config: The configuration object to set. If None, no updates are performed.

        Side effects:
            - Updates self._config
            - Updates self.field_store with values from config
            - Calls self.draw() to redraw the window
        """
        self._config = config

        if config is not None:
            for field_key, config_attr in self.field_mapping.items():
                if hasattr(self.config, config_attr):
                    value = getattr(self.config, config_attr)
                    if config_attr.endswith('_gib'):
                        value = f"{value} GiB"
                    self.field_store[field_key] = str(value)
            self.draw()
            logging.debug(f"config updated with: {self.config}")

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
            field_value = self.field_store[field_key]
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
                        self.field_store[field_name] = self.temp_keyboard_input
                    self.edit_mode = False
                    self.select_mode = True
                    self.draw()
                elif field_name == "network":
                    if key == 32:
                        if self.field_store[field_name] == "MAINNET":
                            self.field_store[field_name] = "TESTNET"
                        else:
                            self.field_store[field_name] = "MAINNET"
                    self.draw()
                elif field_name in ["texts per worker", "max workers"]:
                    if key == curses.KEY_BACKSPACE or key == 127:
                        self.temp_keyboard_input = self.temp_keyboard_input[:-1]
                    elif chr(key).isdigit():
                        self.temp_keyboard_input += chr(key)
                    self.pending_config_changes[field_name] = self.temp_keyboard_input
                    self.field_store[field_name] = self.temp_keyboard_input
                    self.draw()

        field_being_edited = self.field_keys[self.current_field_index]
        logging.debug(f"current field being edited: {field_being_edited}")
        return start_signal
