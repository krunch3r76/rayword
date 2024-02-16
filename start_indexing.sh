#!/bin/bash
set -e
rm -rf app/output/*
main/update_or_insert_paths.py
main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 100
ray up golem-cluster.yaml --yes
ray rsync-up golem-cluster.yaml ./app/input/ /root/app/input/
ray submit golem-cluster.yaml ./rayword.py --enable-console-logging
ray rsync-down golem-cluster.yaml /root/app/output/ ./app/output
main/import_ray_results.py

