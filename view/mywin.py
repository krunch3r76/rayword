# view/mywin.py
import curses


class MyWin:
    # base class for line based custom ncurses windows
    def __init__(self, stdscr, upper_left_y, upper_left_x, height=0, width=0):
        self._stdscr = stdscr
        self._upper_left_y = upper_left_y
        self._upper_left_x = upper_left_x

        screen_height, screen_width = self._stdscr.getmaxyx()
        if height == 0:
            # calculate the remaining height based on upper_left_y
            height = screen_height - upper_left_y
        if width == 0:
            width = screen_width - upper_left_x

        self._height = height
        self._width = width

        self._win = curses.newwin(
            self._height, self._width, self._upper_left_y, self._upper_left_x
        )
        self._refresh()

    def _calculate_viewable_width_and_height(self):
        # the internally defined height (ideal) might be greater than the sized window (viewable dimensions)
        screen_height, screen_width = self._stdscr.getmaxyx()
        drawable_height = screen_height - self._upper_left_y
        drawable_width = screen_width - self._upper_left_x
        viewable_height = min(self._height, drawable_height)
        viewable_width = min(self._width, drawable_width)
        return viewable_height, viewable_width

    def refresh(self):
        self._win.refresh()

    def add_line(self, line, wrap=False, attr=curses.A_NORMAL):
        # move the cursor to next line and write the line
        viewable_height, viewable_width = self._calculate_viewable_width_and_height()
        current_y, _ = self.getyx()
        if current_y > viewable_height - 1:
            raise Exception("Cannot write past last line of window")
        next_y = current_y + 1
        self._win.move(next_y, 0)
        if next_y > viewable_height - 1:
            raise Exception("Cannot write past last line of window")
        if wrap:
            raise Exception("wrapping not implemented")
        if not wrap:
            truncated_line = line[:viewable_width]
            if truncated_line[-1] == "\n":
                truncated_line = truncated_line[:-1]
            self._win.addstr(truncated_line, attr)

    class WordBrowserWin:
        """ui frame for browsing listing words in db

        receives a list of words to display
        """
