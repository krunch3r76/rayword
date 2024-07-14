# view/view.py
import curses
import curses.panel
from queue import Queue
import queue
from .log_window_group import LogWindowGroup
from .mywindow import (
    TextEntryBox,
    MyWindowSelectable,
)
from .panel_manager import PanelManager
import logging
from view.color_pairs import init_color_pairs
from enum import Enum, auto


class View:
    class ViewMode(Enum):
        LOG = auto()
        BROWSER = auto()
        PANEL = auto()
        PROMPT = auto()

    def __init__(self, to_controller: Queue, from_controller: Queue):
        try:
            self._stdscr = curses.initscr()
            curses.curs_set(0)
            self.to_controller = to_controller
            self.from_controller = from_controller
            curses.noecho()
            curses.cbreak()
            self._stdscr.keypad(True)
            curses.start_color()
            self._stdscr.nodelay(True)
            init_color_pairs()

            self.log_window_group = LogWindowGroup(self._stdscr)
            self._wordwin = MyWindowSelectable(
                self._stdscr, 2, upper_left_x=1, boxed=False
            )
            #        self.prompt_window =
            self.auto_scroll_active = True
            self._wordentrywin = TextEntryBox(
                self._stdscr, upper_left_y=0, upper_left_x=0, height=2, boxed=False
            )
            self._stdscr.refresh()
            self._wordentrywin.refresh()
            self._current_view = View.ViewMode.PROMPT
            self.current_word = ""
            self.panel_manager = PanelManager(self._stdscr)
        except Exception as e:
            logging.debug(f"\n\nexception: {e}\n\n")
            raise

    def _process_signal(self, signal: dict):
        # highlest level signal processing for all windows visible or not
        if signal["signal"] == "cmdstart":
            self.log_window_group.update_cmd_line(signal["msg"])
        elif signal["signal"] == "cmdend":
            pass
            # print(f"return code: {signal['msg']}")
        elif signal["signal"] == "cmdout":
            line = signal["msg"]
            self.log_window_group.add_log_line(line)
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
        elif signal["signal"] == "next word result":
            text = signal["msg"]["detail"]["text"]
            authors = signal["msg"]["detail"]["authors"]
            index = signal["msg"]["index"]
            newset = signal["msg"]["newset"]
            title = signal["msg"]["detail"]["title"]
            if newset:
                self.panel_manager.reset()
            if (
                index > len(self.panel_manager.panels) - 1
                or len(self.panel_manager.panels) == 0
            ):
                self.panel_manager.add_panel(
                    upper_left_y=5, upper_left_x=20, height=30, width=40
                )
                if index > 0:
                    self.panel_manager.switch_panel(index)

            for line in text:
                self.panel_manager.add_line_to_current_panel(line)

            self.panel_manager.add_title_and_authors(title, authors)

            self.panel_manager.draw_panels()

    def _update_browsermode(self):
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
            self._current_view = View.ViewMode.PANEL

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
            self.log_window_group.scroll_log_up()
            self.auto_scroll_active = False
            refresh_event = True
        elif ch == curses.KEY_DOWN:
            self.log_window_group.scroll_log_down()
            self.auto_scroll_active = False
        elif ch == -1:
            refresh_event = True
        # if refresh_event:
        #     # self._logwindow.refresh()
        #     refresh_event = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_signal(next_signal)

        if refresh_event:
            self.log_window_group.refresh_all_log()

    def _update_promptmode(self):
        asciicode = self._stdscr.getch()
        if asciicode == ord("q"):
            self.to_controller.put_nowait({"signal": "cmd", "msg": "quit"})
        elif asciicode in (curses.KEY_ENTER, 10, 13):
            self._current_view = View.ViewMode.LOG
            self.to_controller.put_nowait({"signal": "cmd", "msg": "start ray"})
        self.log_window_group.refresh_prompt_window()

    def _update_panelmode(self):
        asciicode = self._stdscr.getch()
        refresh_event = False
        if asciicode == -1:
            refresh_event = True
        elif asciicode == curses.KEY_UP:
            self.panel_manager.scroll_up()
        elif asciicode == curses.KEY_DOWN:
            self.panel_manager.scroll_down()
        elif asciicode == curses.KEY_RIGHT:
            self.to_controller.put_nowait(
                {
                    "signal": "lookupword",
                    "msg": self._wordwin._lines[self._wordwin._selected_line_index],
                }
            )
        if refresh_event:
            refresh_event = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            next_signal = None
            pass
        else:
            self._process_signal(next_signal)

        if refresh_event:
            pass
            # self._wordwin.refresh()
            # self._wordentrywin.refresh()

    def update(self):
        if self._current_view == View.ViewMode.BROWSER:
            self._update_browsermode()
        elif self._current_view == View.ViewMode.LOG:
            self._update_logmode()
        elif self._current_view == View.ViewMode.PANEL:
            self._update_panelmode()
        elif self._current_view == View.ViewMode.PROMPT:
            self._update_promptmode()
        else:
            raise Exception("Unknown view")

    def __del__(self):
        curses.nocbreak()
        self._stdscr.keypad(False)
        curses.echo()
        curses.endwin()
