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
    """
    windows:
        log_window_group (includes start window): start / log ray session
        _wordwin: list words from search on wordentrywin
        _wordentrywin: input search word
        panel_manager: show results of word searches
    """

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
            self.view_changed = False

            # log window group
            self.log_window_group = LogWindowGroup(self.to_controller, self._stdscr)

            # word window
            self._wordwin = MyWindowSelectable(
                self._stdscr, 2, upper_left_x=1, boxed=False
            )

            self.auto_scroll_active = True
            self._wordentrywin = TextEntryBox(
                self._stdscr, upper_left_y=0, upper_left_x=0, height=2, boxed=False
            )
            self._stdscr.refresh()
            # self._wordentrywin.refresh()

            self.current_view = View.ViewMode.PROMPT

            self.current_word = ""
            self.panel_manager = PanelManager(self._stdscr)
            self.prompt_acknowledged = False

            self.log_window_group.refresh_prompt_window()

        except Exception as e:
            logging.debug(f"\n\nexception: {e}\n\n")
            raise

    @property
    def current_view(self):
        return self._current_view

    @current_view.setter
    def current_view(self, newval):
        self._current_view = newval
        self.view_changed = True
        if self._current_view == self.ViewMode.PROMPT:
            self.log_window_group.prompt_window_visible = True
        # handle case where viewmode is changed to BROWSER so that the view associated with PANEL is removed
        if self._current_view == self.ViewMode.BROWSER:
            # hide panel window
            self.log_window_group.hide()
            self.panel_manager.hide()
            self._wordwin.show()
            self._wordentrywin.show()
            self._wordwin.refresh()
            self._wordentrywin.refresh()
        else:
            self.log_window_group.prompt_window_visible = False
            self.log_window_group.resize()
        
        # if newval == View.ViewMode.BROWSER:
        #     self._wordentrywin._textbuffer = "<search word>"
        #     self._wordentrywin.refresh()

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
            logging.debug(f"wordlist: {signal['msg']}")
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
                    upper_left_y=5, upper_left_x=20, height=15, width=40
                )
                if index > 0:
                    self.panel_manager.switch_panel(index)

            for line in text:
                self.panel_manager.add_line_to_current_panel(line)

            self.panel_manager.add_title_and_authors(title, authors)

            self.panel_manager.draw_panels()
        elif signal["signal"] == "configupdate":
            self.log_window_group.update_prompt_window_with_new_config(signal["msg"])
            if self.current_view == self.ViewMode.PROMPT:
                self.log_window_group.refresh_prompt_window()

    def _update_browsermode(self, asciicode):
        # refresh view
        # check for inputs
        # asciicode = self._stdscr.getch()
        refresh_event = False
        if asciicode == -1:
            refresh_event = True
        elif asciicode in (curses.KEY_BACKSPACE, 127, 8):
            self._wordentrywin.backspace()
            self.to_controller.put_nowait(
                {"signal": "search", "msg": self._wordentrywin._textbuffer}
            )
        elif asciicode in (curses.KEY_ENTER, 10, 13):
            try:
                self.to_controller.put_nowait(
                    {
                        "signal": "lookupword",
                        "msg": self._wordwin._lines[self._wordwin._selected_line_index],
                    }
                )
                self.current_view = View.ViewMode.PANEL
            except Exception as e:
                logging.debug(
                    f"{e}: len->{len(self._wordwin._lines)} selected_index: -> self._wordwin._selected_line_index"
                )
                raise
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

    def _update_logmode(self, asciicode):
        # ch = self._stdscr.getch()
        refresh_event = False
        if asciicode == ord("q"):
            self.to_controller.put_nowait({"signal": "cmd", "msg": "quit"})
        elif asciicode == curses.KEY_RESIZE:
            curses.update_lines_cols()
            self.log_window_group.resize()
        elif asciicode == curses.KEY_UP:
            self.log_window_group.scroll_log_up()
            self.auto_scroll_active = False
            refresh_event = True
        elif asciicode == curses.KEY_DOWN:
            self.log_window_group.scroll_log_down()
            self.auto_scroll_active = False
        elif asciicode == -1:
            pass
            # refresh_event = True
        # if refresh_event:
        #     # self._logwindow.refresh()
        #     refresh_event = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            pass
        else:
            self._process_signal(next_signal)
            refresh_event = True

        if refresh_event:
            self.log_window_group.refresh_all_log()

    def _update_promptmode(self, asciicode):
        # asciicode = self._stdscr.getch()
        if asciicode == curses.KEY_RESIZE:
            curses.update_lines_cols()
            self.log_window_group.resize()
            curses.napms(100)
        elif asciicode == ord("q"):
            self.to_controller.put_nowait({"signal": "cmd", "msg": "quit"})
        elif asciicode in (curses.KEY_ENTER, 10, 13):
            start_signal = self.log_window_group.send_key_to_prompt_window(asciicode)
            if start_signal:
                self.current_view = View.ViewMode.LOG
                self.prompt_acknowledged = True
                # inspect log_window_group for fields that have changed
                pending_config_changes = (
                    self.log_window_group.get_fields_changed_from_prompt_window()
                )
                # construct dictionary of values to update controller
                self.to_controller.put_nowait(
                    {
                        "signal": "cmd",
                        "msg": "start ray",
                        "pending_config_changes": pending_config_changes,
                    }
                )
        elif asciicode != -1:
            self.log_window_group.send_key_to_prompt_window(asciicode)
        if self.view_changed:
            logging.debug("view changed to prompt view")
            # self.log_window_group.refresh_prompt_window()
            self.to_controller.put_nowait({"signal": "get config", "msg": None})
            self.view_changed = False

        try:
            next_signal = self.from_controller.get_nowait()
        except queue.Empty:
            next_signal = None
            pass
        else:
            self._process_signal(next_signal)

    def _update_panelmode(self, asciicode):
        # asciicode = self._stdscr.getch()
        refresh_event = False
        if asciicode == -1:
            pass
            # refresh_event = True
        elif asciicode == curses.KEY_RESIZE:
            self.panel_manager.draw_panels()
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
        elif asciicode == 27:
            self.current_view = View.ViewMode.BROWSER
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
        asciicode = self._stdscr.getch()
        if asciicode == curses.KEY_F2:
            # clear othe rgroup
            self._wordwin.hide()
            self._wordentrywin.hide()
            if self.prompt_acknowledged:
                self.current_view = View.ViewMode.LOG
                self.log_window_group.show()
            else:
                self.current_view = View.ViewMode.PROMPT
                self.log_window_group.show()

        elif asciicode == curses.KEY_F3:
            # self.log_window_group.hide()
            # self.log_window_group.clear()
            # self._wordwin.show()
            # self._wordentrywin.show()
            self.current_view = View.ViewMode.BROWSER
        if self.current_view == View.ViewMode.BROWSER:
            self._update_browsermode(asciicode)
        elif self.current_view == View.ViewMode.LOG:
            self._update_logmode(asciicode)
        elif self.current_view == View.ViewMode.PANEL:
            self._update_panelmode(asciicode)
        elif self.current_view == View.ViewMode.PROMPT:
            self._update_promptmode(asciicode)
        else:
            raise Exception("Unknown view")

    def __del__(self):
        curses.nocbreak()
        self._stdscr.keypad(False)
        curses.echo()
        curses.endwin()
