# source_window.py
from .mywindow import MyWindow
import curses


class SourceWindow(MyWindow):
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
        # self.y_offset = 1 if self._boxed else 0  # relative y offset
        self.y_offset = 0

    def add_line(self, line, attr=curses.A_NORMAL):
        try:
            super().add_line(line, self.y_offset, wrapped=False)
        except:
            pass
        self.y_offset += 1
