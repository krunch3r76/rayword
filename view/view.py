# view/view.py
import curses
from queue import Queue
import queue
from .cmd_window import CmdWindow
from .log_window import LogWindow
from .mywindow import MyWindowLineBuffered, TextEntryBox
import logging
from view.color_pairs import init_color_pairs
from enum import Enum, auto


class View:
    class ViewMode(Enum):
        LOG = auto()
        BROWSER = auto()

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
        self._cmdwindow.clear()
        self._logwindow.clear()
        self._wordwin = MyWindowLineBuffered(self._stdscr, 3, upper_left_x=1)
        self.auto_scroll_active = True
        self._wordentrywin = TextEntryBox(
            self._stdscr, upper_left_y=0, upper_left_x=0, height=3
        )
        self._stdscr.refresh()
        self._wordentrywin.refresh()
        self._current_view = View.ViewMode.BROWSER

    def _process_signal(self, signal: dict):
        # logging.debug(signal)
        if signal["signal"] == "cmdstart":
            pass
            # self._cmdwindow.update_command(signal["msg"])
            # print(signal["msg"])
        elif signal["signal"] == "cmdend":
            pass
            # print(f"return code: {signal['msg']}")
        elif signal["signal"] == "cmdout":
            line = signal["msg"]
            # self._logwindow.add_line(line)

            # self._stdscr.addstr(signal["msg"])
            pass
            # print(f"msg: {signal['msg']}")
        elif signal["signal"] == "addword":
            line = signal["msg"]
            self._wordwin.add_line(line)
        elif signal["signal"] == "wake":
            self._wordwin.refresh()
        elif signal["signal"] == "wordlist":
            self._wordwin.clearlines()
            for word in signal["msg"]:
                self._wordwin.add_line(word)
            self._wordwin.refresh()
        elif signal["signal"] == "wordinfos":
            pass
            # logging.debug(signal["msg"])

    def _update_viewmode(self):
        # refresh view
        # check for inputs
        asciicode = self._stdscr.getch()
        refresh_event = False
        if asciicode == -1:
            refresh_event = True
        elif asciicode in (curses.KEY_BACKSPACE, 127, 8):
            self._wordentrywin.backspace()
            self.to_controller.put_nowait(
                {"signal": "search", "msg": self._wordentrywin._textbuffer}
            )
        elif asciicode in (curses.KEY_ENTER, 10, 13):
            self.to_controller.put_nowait(
                {
                    "signal": "lookupword",
                    "msg": self._wordwin._lines[self._wordwin._selected_line_index],
                }
            )
        elif 0 <= asciicode <= 255:
            try:
                self._wordentrywin.process_ascii(asciicode)
                self.to_controller.put_nowait(
                    {"signal": "search", "msg": self._wordentrywin._textbuffer}
                )
            except Exception as e:
                logging.debug(f"exception: {e}")
                raise
        else:
            if asciicode == curses.KEY_UP:
                self._wordwin.move_selection_up()
            elif asciicode == curses.KEY_DOWN:
                self._wordwin.move_selection_down()
                # if self._wordwin._selected_line_index <= len(self._wordwin.lines) - 1:
                #     self._wordwin.__current_line_index += 1

        if refresh_event:
            # self._logwindow.refresh()
            refresh_event = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            next_signal = None
            pass
        else:
            self._process_signal(next_signal)

        if refresh_event:
            # self._wordwin.refresh()
            self._wordentrywin.refresh()

    def _update_logmode(self):
        ch = self._stdscr.getch()
        refresh_event = False
        if ch == ord("q"):
            self.to_controller.put_nowait({"signal": "cmd", "msg": "quit"})
        elif ch == curses.KEY_UP:
            self._logwindow.scroll_up()
            self.auto_scroll_active = False
            refresh_event = True
        elif ch == curses.KEY_DOWN:
            self._logwindow.scroll_down()
            self.auto_scroll_active = False
        elif ch == -1:
            refresh_event = True
        if refresh_event:
            # self._logwindow.refresh()
            refresh_event = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_signal(next_signal)

        if refresh_event:
            self._wordwin.refresh()

    def update(self):
        if self._current_view == View.ViewMode.BROWSER:
            self._update_viewmode()
        elif self._current_view == View.ViewMode.LOG:
            self._update_logmode()
        else:
            raise Exception("Unknown view")

    def __del__(self):
        curses.nocbreak()
        self._stdscr.keypad(False)
        curses.echo()
        curses.endwin()
