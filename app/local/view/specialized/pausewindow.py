from ..mywindow import MyWindow
import curses
import logging

class PauseWindow(MyWindow):
    def __init__(self, stdscr: curses.window, upper_left_y: int = 0, upper_left_x: int = 0, 
                 height: int = None, width: int = None, boxed: bool = False, 
                 initial_seconds: int = 10):
        super().__init__(stdscr, upper_left_y, upper_left_x, height, width, boxed)
        self._initial_seconds = initial_seconds
        self._seconds_remaining = initial_seconds
        
    @classmethod
    def create_centered(cls, stdscr: curses.window, height: int = 3, width: int = 30, 
                       boxed: bool = True, initial_seconds: int = 10):
        """Create a centered PauseWindow"""
        screen_height, screen_width = stdscr.getmaxyx()
        upper_left_y = (screen_height - height) // 2
        upper_left_x = (screen_width - width) // 2
        
        return cls(
            stdscr=stdscr,
            upper_left_y=upper_left_y,
            upper_left_x=upper_left_x,
            height=height,
            width=width,
            boxed=boxed,
            initial_seconds=initial_seconds
        )
        
    def reset(self, seconds: int = None):
        """Reset the countdown timer. Optionally specify a new duration."""
        if seconds is not None:
            self._initial_seconds = seconds
        self._seconds_remaining = self._initial_seconds
        self.show()  # In case it was hidden
        
    def update(self) -> bool:
        """
        Updates the countdown display and waits one second.
        Returns True when countdown is complete, False otherwise.
        """
        logging.debug(f"Pause window update: {self._seconds_remaining} seconds remaining")
        if self._seconds_remaining <= 0:
            logging.debug("Countdown complete")
            return True
            
        message = f"Pausing for {self._seconds_remaining} seconds"
        self.clear()
        y_pos = 0
        x_pos = (self._width - len(message)) // 2
        self.add_line(message, y_pos, wrapped=False)
        self.refresh()
        
        curses.napms(1000)  # Wait for 1 second
        self._seconds_remaining -= 1
        return False