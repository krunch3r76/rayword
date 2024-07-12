from .mypad import MyPad


class LogWindow(MyPad):
    def __init__(
        self,
        stdscr,
        upper_left_y,
        upper_left_x,
        height,
        width,
        nlines=10000,
        ncols=1000,
    ):
        super().__init__(
            stdscr, upper_left_y, upper_left_x, height, width, nlines, ncols
        )

    def _write_and_wrap_segment(self, segment):
        return super()._write_and_wrap_segment(segment, wrap=True)
