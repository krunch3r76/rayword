# cmd_window.py
import curses
import asyncio
from .mywindow import MyWindow


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
        _, width = self._viewable_height_and_width
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
        self._add_line(cmd_text, self._upper_left_y, attr=attr, truncated=True)
        # self._win.move(self._upper_left_y, self._upper_left_x)
        # self._win.addstr(cmd_text)
        self._redraw_border()
        self.refresh()
        self._current_cmd = cmd_text

    async def update_progress_meter(self):
        pass
        # while True:
        #     offset_to_progress_dots = len(self._current_cmd) + 1
        #     _, max_width = self._viewable_height_and_width
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
