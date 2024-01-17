#!/usr/bin/env bash

# demo.sh
# demonstration of rayword by the author krunc3r (https://www.github.com/krunch3r`)
# Define a cleanup function for ctrl-c
cleanup() {
    echo "Caught Interrupt. Exiting..."
    exit 1
}

# trap ctrl-c
trap cleanup SIGINT

pkill -9 ray-on-golem
# Exit immediately if a command exits with a non-zero status.
rm sample.wav
set -e
set -x
ray up golem-cluster.yaml --yes
ray exec golem-cluster.yaml 'mkdir -p /root/nltk_data/corpora'
ray exec golem-cluster.yaml 'pip3 install word_forms'
ray rsync-up golem-cluster.yaml ./nltk_data/corpora/wordnet.zip /root/nltk_data/corpora/wordnet.zip
ray rsync-up golem-cluster.yaml ./bin/espeak/ /espeak/

# Check if argument $1 is provided
if [ -z "$1" ]; then
    ray submit golem-cluster.yaml rayword.py sobriquet --enable-console-logging --batch-size=50
else
    ray submit golem-cluster.yaml rayword.py "$1"
fi

ray rsync-down golem-cluster.yaml ./data/words.db ./data/words.db
ray rsync-down golem-cluster.yaml ./app/output/sample.wav ./app/output/sample.wav
aplay ./app/output/sample.wav
# implement logic to check whether any records were added and if not rerun, use output dir in manager
# ray attach golem-cluster.yaml
