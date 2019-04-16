#! /usr/bin/env bash 

rsync -avz --exclude .git --exclude __pycache__ --exclude .pyc . $1:~/$(pwd | awk -F'/' '{print $NF}')