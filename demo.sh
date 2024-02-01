#!/usr/bin/env bash

# demo.sh
# demonstration of rayword by the author krunc3r (https://www.github.com/krunch3r`)
# Define a cleanup function for ctrl-c
cleanup() {
    echo "Caught Interrupt. Exiting..."
    ray down golem-cluster.yaml --yes
    exit 1
}

# trap ctrl-c
trap cleanup SIGINT

run_with_retries() {
    set +x
    local max_retries=$1
    local cmd="${@:2}"
    local count=0

    while [ $count -lt $max_retries ]; do
        # echo "Attempt $(($count + 1)) of $max_retries: $cmd"
	$cmd &>/dev/null && return || echo "Failed! Retrying..."

        count=$(($count + 1))
        sleep 1  # Optional: Sleep for a brief period before retrying
    done

    echo "Command failed after $max_retries attempts."
    exit 1
}

pkill -9 ray-on-golem
# Exit immediately if a command exits with a non-zero status.
rm -f ./app/output/sample.wav
set -e
set -x
ray up golem-cluster.yaml --yes
ray exec golem-cluster.yaml 'pip3 install word_forms' &> /dev/null
ray exec golem-cluster.yaml 'mkdir -p /root/nltk_data/corpora' &> /dev/null
run_with_retries 5 ray rsync-up -v golem-cluster.yaml ./nltk_data/corpora/wordnet.zip /root/nltk_data/corpora/wordnet.zip
set -x
run_with_retries 5 ray rsync-up -v golem-cluster.yaml ./bin/espeak.tar.gz /
set -x
ray exec golem-cluster.yaml 'tar -xzf /espeak.tar.gz -C /'

# Check if argument $1 is provided
if [ -z "$1" ]; then
    ray submit golem-cluster.yaml rayword.py sobriquet --enable-console-logging --batch-size=50
else
    ray submit golem-cluster.yaml rayword.py "$@"
fi

ray rsync-down golem-cluster.yaml ./data/words.db ./data/words.db &> /dev/null
ray rsync-down golem-cluster.yaml ./app/output/sample.wav ./app/output/sample.wav &> /dev/null
aplay ./app/output/sample.wav
# implement logic to check whether any records were added and if not rerun, use output dir in manager
# ray attach golem-cluster.yaml
