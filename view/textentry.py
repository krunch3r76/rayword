from .mywindow import MyWindow
import curses


class TextEntryBox(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int = 0,
        upper_left_x: int = 0,
        height: int = 2,
        width: int = None,
        boxed: bool = True,
    ):
        super().__init__(stdscr, upper_left_y, upper_left_x, height, width, boxed)
        self._textbuffer = ""
        self._stdscr.refresh()  # kludge for display

    def _add_line(self, line):
        self.clear()
        super()._add_line(
            line,
            self._upper_left_y + 1 if self._boxed else 0,
            self._upper_left_x + 1 if self._boxed else 0,
        )

    def refresh(self):
        self._add_line(self._textbuffer)
        self._stdscr.refresh()
        super().refresh()
        # self._stdscr.refresh()

    def process_ascii(self, asciicode):
        self._textbuffer = self._textbuffer + chr(asciicode)
        self.refresh()

    def backspace(self):
        self._textbuffer = self._textbuffer[:-1]
        self.refresh()
