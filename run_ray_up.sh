#!/bin/bash
# run_ray_up.sh

unbuffer ray up "$@" &
exit $?

# Use a FIFO (named pipe) to capture output for line-by-line processing
output_fifo="/tmp/ray_up_output_fifo.$$"
mkfifo "$output_fifo"

# Clean up FIFO on script exit
trap 'rm -f "$output_fifo"' EXIT

# Run the 'ray up' command and redirect output to FIFO in the background
# stdbuf -oL -eL ray up "$@" > "$output_fifo" 2>&1 &
ray up "$@" > "$output_fifo" 2>&1 &

ray_pid=$!

# Read from FIFO line by line
while IFS= read -r line; do
    echo "$line"
    # Optionally process each line, e.g., send to another process or log file
done < "$output_fifo"

# Wait for the command to finish and capture its exit code
wait $ray_pid
exit_code=$?

# Return the exit code
exit $exit_code
