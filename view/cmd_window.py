# cmd_window.py
import curses
import asyncio


# status window that displays as much as it can of itself
class MyWindow:
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int,
        upper_left_x: int,
        internal_height: int = 5,
        internal_width: int = None,
        boxed: bool = False,
    ):
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x
        self._internal_height = internal_height
        self._internal_width = internal_width
        screen_height, screen_width = self._stdscr.getmaxyx()
        available_lines, available_cols = self._max_height_and_width
        self._win = curses.newwin(
            available_lines, available_cols, self._upper_left_y, self._upper_left_x
        )
        self._boxed = boxed

    @property
    def _max_height_and_width(self):
        screen_height, screen_width = self._stdscr.getmaxyx()
        max_height = min(self._internal_height, screen_height)
        if self._internal_width is not None:
            max_width = min(self._internal_width, screen_width)
        else:
            max_width = screen_width

        return max_height, max_width

    def refresh(self):
        if self._boxed:
            self._win.box()
        self._win.refresh()

    def clear(self):
        self._win.clear()

    def resize_deep(self):
        self.clear()
        available_lines, available_cols = self._max_height_and_width
        self._win.resize(available_lines, available_cols)
        self._win.touchwin()
        self._win.redrawwin()
        self.refresh()

    def resize(self):
        available_lines, available_cols = self._max_height_and_width
        self._win.erase()
        self._win.resize(available_lines, available_cols)
        self.refresh()

    def _add_line_truncated(self, line, y_offset, x_offset=0, attr=curses.A_NORMAL):
        max_height, max_width = self._max_height_and_width
        available_width = max_width - x_offset if x_offset is not None else max_width
        if y_offset > max_height - 1:
            raise Exception("Line written outside of height boundaries")
        truncated_line = line[:available_width]
        self._win.move(y_offset, x_offset)
        self._win.addstr(truncated_line, attr)


class CmdWindow(MyWindow):
    def __init__(
        self,
        stdscr: curses.window,
        upper_left_y: int,
        upper_left_x: int,
        internal_height: int = 2,
        internal_width: int = None,
    ):
        super().__init__(
            stdscr, upper_left_y, upper_left_x, internal_height, internal_width
        )
        self._progress_meter = 1
        self._current_cmd = ""
        self._failed_commands = []

    def _redraw_border(self):
        _, width = self._max_height_and_width
        self._win.move(1, 0)
        self._win.insstr("─" * (width - 1))
        # self._win.insstr(1, width - 1, "─")

    def resize(self):
        super().resize()
        self.update_command(self._current_cmd)

    def update_command(self, cmd_text: str, failed=False):
        self.clear()
        if failed or cmd_text in self._failed_commands:
            self._failed_commands.append(cmd_text)
            attr = curses.color_pair(2) | curses.A_BOLD
        else:
            attr = curses.color_pair(3) | curses.A_BOLD
        self._add_line_truncated(cmd_text, self._upper_left_y, attr=attr)
        # self._win.move(self._upper_left_y, self._upper_left_x)
        # self._win.addstr(cmd_text)
        self._redraw_border()
        self.refresh()
        self._current_cmd = cmd_text

    async def update_progress_meter(self):
        pass
        # while True:
        #     offset_to_progress_dots = len(self._current_cmd) + 1
        #     _, max_width = self._max_height_and_width
        #     available_cols = max_width - offset_to_progress_dots - 1
        #     if available_cols >= 3:
        #         self._win.move(0, offset_to_progress_dots)
        #         prev_cursor_state = curses.curs_set(0)
        #         self._win.addstr("   ")
        #         self._win.move(0, offset_to_progress_dots)
        #         self._win.addstr("." * (self._progress_meter % 4), curses.color_pair(3))
        #         curses.curs_set(prev_cursor_state)
        #         self._progress_meter += 1
        #         self.refresh()
        #     await asyncio.sleep(0.5)
