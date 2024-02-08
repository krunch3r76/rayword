#!/bin/bash

main/update_or_insert_paths.py
main/prepare_unsearched_paths_json.py golem-cluster.yaml --batch-size 50
./rayword.py
main/import_ray_results.py

