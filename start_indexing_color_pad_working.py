#!/usr/bin/env python3
# start_indexing_color.py
import curses
import subprocess
import os
import select
import re
import time
import pty

commands = [
    "rm -rf app/output/*",
    "python main/update_or_insert_paths.py",
    "python main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 100",
    "unbuffer ray up golem-cluster.yaml --yes",
    "ray rsync-up golem-cluster.yaml ./app/input/ /root/app/input/",
    "ray submit golem-cluster.yaml ./rayword.py --enable-console-logging",
    "ray rsync-down golem-cluster.yaml /root/app/output/ ./app/output",
    "python main/import_ray_results.py",
    "ray down golem-cluster.yaml --yes",
]


def init_color_pairs():
    curses.use_default_colors()
    for i, color in enumerate(
        [
            curses.COLOR_BLACK,
            curses.COLOR_RED,
            curses.COLOR_GREEN,
            curses.COLOR_YELLOW,
            curses.COLOR_BLUE,
            curses.COLOR_MAGENTA,
            curses.COLOR_CYAN,
            curses.COLOR_WHITE,
        ],
        start=1,
    ):
        curses.init_pair(i, color, -1)


def get_color_pair(ansi_code):
    if 30 <= ansi_code <= 37:
        return curses.color_pair(ansi_code - 29)  # Standard colors 1-8
    elif 90 <= ansi_code <= 97:
        return curses.color_pair(ansi_code - 81 + 8)  # Bright colors 9-16
    return curses.color_pair(0)  # Default color


ANSI_ESCAPE_REGEX = re.compile(r"\x1B\[(\d+(?:;\d+)*)m")


def parse_ansi_sequences(text):
    segments = []
    current_attr = curses.A_NORMAL
    last_pos = 0

    for match in ANSI_ESCAPE_REGEX.finditer(text):
        start, end = match.span()
        segments.append((text[last_pos:start], current_attr))
        last_pos = end

        params = map(int, match.group(1).split(";"))
        for code in params:
            if code == 0:  # Reset
                current_attr = curses.A_NORMAL
            elif 30 <= code <= 37 or 90 <= code <= 97:
                current_attr = get_color_pair(code)

    segments.append((text[last_pos:], current_attr))
    return segments


def execute_command(command, output_pad, pad_line, max_x):
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        bufsize=1,  # Small buffer size for nearly real-time processing
        text=True,
    )

    # Continuously read output from the process
    try:
        line_buffer = ""
        while True:
            char = proc.stdout.read(1)
            while char != "" and char != "\n":
                line_buffer += char
                char = proc.stdout.read(1)
            if char == "" and proc.poll() is not None:
                break

            if char:
                # Directly print characters to the pad with the correct attribute
                # Check if it's part of an ANSI sequence or normal text
                if char == "\n":
                    pad_line += 1  # Increment line counter on new lines
                    output_pad.move(
                        pad_line, 0
                    )  # Move cursor to the start of the new line on the pad
                # Here you would typically parse ANSI sequences and apply attributes
                # For simplicity, we're directly adding text here
                segments = parse_ansi_sequences(line_buffer)
                for text, attr in segments:
                    output_pad.addstr(
                        pad_line,
                        output_pad.getyx()[1],
                        text,
                        attr,
                    )  # Example with fixed attribute
                line_buffer = ""
            output_pad.refresh(
                pad_line - curses.LINES + 3,
                0,
                3,
                0,
                curses.LINES - 1,
                curses.COLS - 1,
            )

    finally:
        proc.stdout.close()
        proc.stderr.close()
    return pad_line


def setup_cmd_window(cmd_window, command):
    cmd_window.clear()
    cmd_window.addstr(command + "\n")
    cmd_window.hline(1, 0, "-", cmd_window.getmaxyx()[1])
    cmd_window.refresh()


def main():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    curses.curs_set(0)
    max_y, max_x = stdscr.getmaxyx()
    init_color_pairs()

    cmd_window = curses.newwin(3, max_x, 0, 0)
    output_pad = curses.newpad(1000, max_x)
    pad_line = 0

    # commands = ["echo 'Hello, world!'", "ls -l", "uname -a", "ls -l"]
    for command in commands:
        setup_cmd_window(cmd_window, command)
        stdscr.noutrefresh()
        pad_line = execute_command(command, output_pad, pad_line, max_x)

    current_line = 0
    stdscr.timeout(100)  # Non-blocking getch every 100 ms
    try:
        while True:
            output_pad.refresh(current_line, 0, 3, 0, max_y - 1, max_x - 1)
            ch = stdscr.getch()
            if ch == curses.KEY_DOWN:
                if current_line < pad_line[0] - max_y + 3:
                    current_line += 1
            elif ch == curses.KEY_UP:
                if current_line > 0:
                    current_line -= 1
            elif ch == ord("q"):
                break
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    main()
