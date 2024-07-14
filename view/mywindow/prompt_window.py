# prompt_window.py

import curses
from .mywindow import MyWindow


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
        self.y_offset = 0  # relative y offset

    def add_line(self, line, attr=curses.A_NORMAL):
        try:
            super().add_line(line, self.y_offset, wrapped=False)
        except:
            pass
        self.y_offset += 1
