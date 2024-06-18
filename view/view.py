# view/view.py
import curses
from queue import Queue
import queue
from .cmd_window import CmdWindow
from .log_window import LogWindow
import logging
from view.color_pairs import init_color_pairs


class View:
    def __init__(self, to_controller: Queue, from_controller: Queue):
        self._stdscr = curses.initscr()
        curses.curs_set(0)
        self.to_controller = to_controller
        self.from_controller = from_controller
        curses.noecho()
        curses.cbreak()
        self._stdscr.keypad(True)
        curses.start_color()
        self._stdscr.nodelay(True)
        self._cmdwindow = CmdWindow(self._stdscr, 0, 0)
        screen_height, screen_width = self._stdscr.getmaxyx()
        self._logwindow = LogWindow(self._stdscr, 2, 0, screen_height - 2, screen_width)
        init_color_pairs()
        self.current_line_offset = 0
        self.padline_at_keyup = 1
        self.auto_scroll_active = True

    def _process_signal(self, signal: dict):
        if signal["signal"] == "cmdstart":
            self._cmdwindow.update_command(signal["msg"])
            # print(signal["msg"])
        elif signal["signal"] == "cmdend":
            pass
            # print(f"return code: {signal['msg']}")
        elif signal["signal"] == "cmdout":
            line = signal["msg"]
            self._logwindow.add_line(line)

            # self._stdscr.addstr(signal["msg"])
            pass
            # print(f"msg: {signal['msg']}")

    def get_signal(self) -> dict:
        pass

    def update(self):
        # refresh view
        # check for inputs
        ch = self._stdscr.getch()
        if ch == ord("q"):
            self.to_controller.put_nowait({"signal": "cmd", "msg": "quit"})
        elif ch == curses.KEY_UP:
            if self.current_line_offset == 0:
                self.padline_at_keyup = self._logwindow._padline
            if self._logwindow._pminrow - self.current_line_offset >= 0:
                self.current_line_offset += 1
                self.auto_scroll_active = False
        if not self.auto_scroll_active:
            logging.debug(
                f"refresh({self._logwindow._pminrow} - {self.current_line_offset}"
            )
            self._logwindow.refresh(self._logwindow._pminrow - self.current_line_offset)
        else:
            self._logwindow.refresh()
        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_signal(next_signal)

    def __del__(self):
        curses.nocbreak()
        self._stdscr.keypad(False)
        curses.echo()
        curses.endwin()
