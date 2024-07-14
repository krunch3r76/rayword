# log_window_group.py
# manage the log view
from .mywindow import PromptWindow, LogWindow, CmdWindow


class LogWindowGroup:
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
        TOP_PADDING = 2
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

    def refresh_all_log(self):
        for window in self.log_windows:
            window.refresh()

    def add_log_line(self, line):
        self.log_window.add_line(line)

    def scroll_log_up(self):
        self.logwindow.scroll_up()

    def scroll_log_down(self):
        self.logwindow.scroll_down()

    def refresh_prompt_window(self):
        self.prompt_window.refresh()

    def update_cmd_line(self, line):
        self.cmd_window.update_command(line, 0)
