#!/usr/bin/env python3

import logging
import traceback

from controller import Controller

# Explicitly get the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.handlers = []

# Create a file handler to write logs to a file
file_handler = logging.FileHandler("debug.log", mode="w")
file_handler.setLevel(logging.DEBUG)

# Create a formatter and set it for the handler
formatter = logging.Formatter("%(filename)s %(lineno)d %(message)s")
file_handler.setFormatter(formatter)

# Add the handler to the root logger
root_logger.addHandler(file_handler)

try:
    controller = Controller()
    controller()
except Exception as e:
    import curses

    curses.endwin()
    logging.debug(f"an exception {e} of type {type(e)} occurred")
    logging.debug(traceback.format_exc())
    raise
