# log_window_group.py
# manage the log view
from .mywindow import PromptWindow, LogWindow, CmdWindow
import curses
import logging


class LogWindowGroup:
    """
    view
        prompt_window: PromptWindow  -> start dialog box
        log_windows[]
            log_window:LogWindow -> show output of command running
            cmd_window:CmdWindow -> show command running
    """

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.prompt_window = PromptWindow(
            self.stdscr,
            upper_left_y=20,
            upper_left_x=20,
            height=10,
            width=40,
            boxed=True,
            padding=1,
        )

        BOTTOM_PADDING = 2
        TOP_PADDING = 3
        screen_height, screen_width = self.stdscr.getmaxyx()
        self.log_window = LogWindow(
            self.stdscr,
            TOP_PADDING,
            0,
            screen_height - BOTTOM_PADDING - TOP_PADDING,
            screen_width,
        )

        self.cmd_window = CmdWindow(self.stdscr, 0, 0)
        self.log_windows = [self.log_window, self.cmd_window]
        # self.add_lines_to_prompt_window()
        self.refresh_prompt_window()

    def send_key_to_prompt_window(self, asciicode):
        start_signal = self.prompt_window.handle_key(asciicode)
        return start_signal

    def add_lines_to_prompt_window(self):
        # consider making prompt_window remember this internally and just rewrite on refresh

        # self.prompt_window.add_line("Press enter to start ray")
        # self.prompt_window.refresh()
        self.prompt_window.draw()

    def hide(self):
        for window in self.log_windows:
            window.hide()
        self.prompt_window.hide()

    def show(self, include_prompt_window=False):
        for window in self.log_windows:
            window.show()
        if include_prompt_window:
            self.prompt_window.show()

    def clear(self):
        for window in self.log_windows:
            window.clear()
        self.prompt_window.clear()

    def resize(self):
        for window in self.log_windows:
            window.resize()

    def refresh_all_log(self):
        for window in self.log_windows:
            window.refresh()

    def add_log_line(self, line):
        self.log_window.add_line(line)

    def scroll_log_up(self):
        self.log_window.scroll_up()

    def scroll_log_down(self):
        self.log_window.scroll_down()

    def refresh_prompt_window(self):
        pass
        self.prompt_window.clear()
        self.add_lines_to_prompt_window()
        self.prompt_window.refresh()

    def update_cmd_line(self, line):
        self.cmd_window.update_command(line, 0)
