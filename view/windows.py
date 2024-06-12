# windows.py
import curses


class WrappedWindow:
    def __init__(self, nlines, ncols, begin_y, begin_x):
        # Creating a new curses window internally
        self.win = curses.newwin(nlines, ncols, begin_y, begin_x)
        # self.width = ncols - 1  # To handle wrapping correctly
        self.current_line = 0  # Keep track of the current line for auto text addition

    @property
    def max_x(self):
        return self.win.getmaxyx()[1]

    @property
    def max_y(self):
        return self.win.getmaxyx()[0]

    def add_wrapped_text(self, text, attr=curses.A_NORMAL, split_words=False):
        """
        Adds text to the window with automatic line wrapping. Splits lines if they exceed the width.
        """
        if split_words:
            while len(text) > self.max_x:
                part = text[: self.max_x]
                self.win.addstr(self.current_line, 0, part, attr)
                text = text[self.max_x :]
                self.current_line += 1
            if text:
                self.win.addstr(self.current_line, 0, text, attr)
                self.current_line += 1
        else:
            words = text.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > self.max_x:
                    self.win.addstr(self.current_line, 0, current_line, attr)
                    self.current_line += 1
                    current_line = word + " "
                else:
                    current_line += word + " "
            if current_line:
                self.win.addstr(self.current_line, 0, current_line, attr)
                self.current_line += 1

    def insert_wrapped_text(self, y, x, text, attr=curses.A_NORMAL, split_words=True):
        """
        Inserts text at a given position and wraps text if necessary.
        """
        ncols = self.max_x + 1
        if split_words:
            while len(text) > ncols:
                part = text[: self.max_x - x]
                self.win.insstr(y, x, part, attr)
                text = text[self.max_x - x :]
                y += 1
            if text:
                self.win.insstr(y, x, text, attr)
        else:
            words = text.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > self.max_x - x + 1:
                    self.win.insstr(y, x, current_line, attr)
                    y += 1
                    current_line = word + " "
                else:
                    current_line += word + " "
            if current_line:
                self.win.insstr(y, x, current_line, attr)

    def refresh(self):
        """
        Refreshes the window display.
        """
        self.win.refresh()

    def clear(self):
        """
        Clears the window and resets the line counter.
        """
        self.win.clear()
        self.current_line = 0


class WrappedPad:
    def __init__(self, height, width):
        self.pad = curses.newpad(height, width)
        self.height = height
        self.max_x = (
            width - 1
        )  # Reserve one column to prevent automatic wrapping by curses
        self.line = 0

    def add_wrapped_text(self, text, attr=curses.A_NORMAL):
        """Add text to the pad with automatic line wrapping."""
        while len(text) > self.max_x:
            part = text[: self.max_x]
            self.pad.addstr(self.line, 0, part, attr)
            text = text[self.max_x :]
            self.line += 1
        if text:
            self.pad.addstr(self.line, 0, text, attr)
            self.line += 1

    def refresh(self, pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol):
        """Refresh the pad display."""
        self.pad.refresh(pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)

    def move(self, y, x):
        self.pad.move(y, x)

    def movetoline(self, line):
        """Move the cursor to a specific line."""
        self.line = line

    def clear(self):
        """Clear the pad."""
        self.pad.clear()
        self.line = 0
