#!/usr/bin/env python3
# start_indexing_color.py
import curses
import subprocess
import os
import select
import re

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


def parse_ansi_sequences(text):
    ANSI_ESCAPE_REGEX = re.compile(r"\x1B\[(\d+(?:;\d+)*)m")
    default_color = curses.color_pair(0)
    current_color = default_color
    last_pos = 0
    segments = []

    for match in ANSI_ESCAPE_REGEX.finditer(text):
        start, end = match.span()
        segments.append((text[last_pos:start], current_color))
        last_pos = end

        params = map(int, match.group(1).split(";"))
        for param in params:
            if param == 0:
                current_color = default_color
            elif 30 <= param <= 37:
                current_color = curses.color_pair(param - 30 + 1)
            elif 90 <= param <= 97:
                current_color = curses.color_pair(param - 90 + 9)

    segments.append((text[last_pos:], current_color))  # Append remaining text
    return segments


def execute_command(command, cmd_window, output_window, max_x):
    cmd_window.clear()
    cmd_window.addstr(command + "\n")
    cmd_window.hline(1, 0, "-", max_x)  # Draw a line
    cmd_window.refresh()

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        bufsize=1,  # Ensure line buffering
    )

    stdout_buffer = ""
    while True:
        output = proc.stdout.read(1)  # Read one character at a time
        if output == "" and proc.poll() is not None:
            break
        if output != "":
            stdout_buffer += output
            if output == "\n":
                for text, attr in parse_ansi_sequences(stdout_buffer):
                    output_window.addstr(text, attr)
                stdout_buffer = ""
                output_window.refresh()

    # Handle remaining buffer
    if stdout_buffer:
        for text, attr in parse_ansi_sequences(stdout_buffer):
            output_window.addstr(text, attr)
        output_window.refresh()

    proc.stdout.close()
    proc.stderr.close()


def main():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.start_color()
    curses.curs_set(0)
    init_color_pairs()

    max_y, max_x = stdscr.getmaxyx()
    cmd_window = curses.newwin(3, max_x, 0, 0)
    output_window = curses.newwin(max_y - 3, max_x, 2, 0)
    output_window.scrollok(True)
    output_window.idlok(True)

    for command in commands:
        execute_command(command, cmd_window, output_window, max_x)

    output_window.getch()
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


if __name__ == "__main__":
    main()
