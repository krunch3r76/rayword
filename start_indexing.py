#!/usr/bin/env python3

import logging
import traceback

logging.basicConfig(
    filename="wtf.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(filename)s %(lineno)s %(msg)s",
)
from start_indexing.controller import Controller

controller = Controller()
try:
    controller()
except Exception as e:
    logging.debug(f"an exception {e} of type {type(e)} occurred")
    logging.debug(traceback.format_exc())
    del controller
