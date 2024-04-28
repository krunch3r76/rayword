#!/usr/bin/env python3
# start_indexing_color.py

from start_indexing.color_pairs import init_color_pairs
from start_indexing.parse_ansi_sequences import parse_ansi_sequences
from start_indexing.render_command_header import render_command_header
from start_indexing.windows import WrappedWindow, WrappedPad
import threading
from queue import Queue, Empty

commands = [
    "echo 'Hello, worlds!'",
    "rm -rf app/output/*",
    "python3 main/update_or_insert_paths.py",
    "python3 main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 100",
    # "stdbuf -oL -eL ray up golem-cluster.yaml --yes --redirect-command-output --use-normal-shells",
    # "./run_ray_up.sh golem-cluster.yaml --yes --redirect-command-output --use-normal-shells 2>&1",
    "./run_ray_up.sh golem-cluster.yaml --yes",
    "ray rsync-up golem-cluster.yaml ./app/input/ /root/app/input/",
    "ray submit golem-cluster.yaml ./rayword.py --enable-console-logging",
    "ray rsync-down golem-cluster.yaml /root/app/output/ ./app/output",
    "python main/import_ray_results.py",
    "ray down golem-cluster.yaml --yes",
]

import asyncio
import curses
import re
import os
import logging
import subprocess
import signal
import socket

# Constants
CMD_WINDOW_HEIGHT = 2


# Set up logging
logging.basicConfig(
    filename="debug.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

update_event = asyncio.Event()


async def run_command(command, pad, pad_line):
    # Start the subprocess
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Read stdout and stderr concurrently
    await asyncio.gather(
        read_stream(proc.stdout, pad, pad_line), read_stream(proc.stderr, pad, pad_line)
    )

    # Wait for the process to finish
    return await proc.wait()


async def read_stream(stream, pad, pad_line):
    while True:
        line = await stream.readline()
        if line:
            line = line.decode("utf-8").rstrip()
            logging.debug(line)
            await process_data(line, pad, pad_line)
        else:
            break  # Exit the loop when no more data is available


async def process_data(text, pad, pad_line):
    lines = text.split("\n")
    for line in lines:
        pad_line[0] += 1
        pad.move(pad_line[0], 0)
        segments = parse_ansi_sequences(line)
        for txt, attr in segments:
            pad.addstr(pad_line[0], pad.getyx()[1], txt, attr)
            update_event.set()

    # Instead of refreshing here, just signal that an update is needed


async def handle_user_input_and_auto_scroll(stdscr, pad, pad_line, exit_event):
    current_line = 0
    auto_scroll_active = (
        True  # This flag is used to determine if the pad should auto-scroll
    )
    stdscr.nodelay(True)  # Non-blocking input

    try:
        while not exit_event.is_set():
            ch = stdscr.getch()
            if ch == curses.KEY_DOWN:
                if current_line < pad_line[0] - curses.LINES + CMD_WINDOW_HEIGHT + 1:
                    current_line += 1
                    auto_scroll_active = False
            elif ch == curses.KEY_UP:
                if current_line > 0:
                    current_line -= 1
                    auto_scroll_active = False
            elif ch == ord("q"):
                exit_event.set()
            elif ch == -1 and auto_scroll_active:  # No input and autoscroll is active
                # Auto-scroll to the most recent line that fits on screen
                current_line = max(
                    0, pad_line[0] - (curses.LINES - CMD_WINDOW_HEIGHT - 1)
                )

            # Refresh logic: only refresh if the update event is set or autoscrolling is active
            if update_event.is_set() or auto_scroll_active:
                # Calculate the portion of the pad to show based on the current_line
                pminrow = max(0, current_line)
                sminrow = (
                    CMD_WINDOW_HEIGHT  # Start showing pad just below the command window
                )
                smaxrow = curses.LINES - 1  # End at the last line of the screen

                # Perform the refresh to show the appropriate part of the pad
                pad.refresh(pminrow, 0, sminrow, 0, smaxrow, curses.COLS - 1)
                update_event.clear()

            await asyncio.sleep(0.05)  # Sleep to reduce CPU usage
    finally:
        stdscr.nodelay(False)


async def main_loop(stdscr, commands):
    cmd_window = WrappedWindow(CMD_WINDOW_HEIGHT, curses.COLS, 0, 0)
    pad = curses.newpad(10000, curses.COLS)
    pad_line = [0]
    exit_event = asyncio.Event()

    # Start user input handling task
    user_input_task = asyncio.create_task(
        handle_user_input_and_auto_scroll(stdscr, pad, pad_line, exit_event)
    )

    # Execute commands
    for command in commands:
        render_command_header(cmd_window, command)
        return_code = await run_command(
            command, pad, pad_line
        )  # This function now returns the return code
        cmd_window.refresh()
        if return_code != 0:  # Check if the return code is not zero
            logging.error(
                f"Command '{command}' failed with return code {return_code}. Stopping execution of further commands."
            )
            update_event.set()
            break  # Stop executing further commands

    cmd_window.refresh()
    # Wait until the user decides to exit
    await exit_event.wait()

    # Clean up
    user_input_task.cancel()

    # Optionally wait for the user input task to finish cleanly
    try:
        await user_input_task
    except asyncio.CancelledError:
        pass


def main():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    init_color_pairs()

    try:
        asyncio.run(main_loop(stdscr, commands))
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
