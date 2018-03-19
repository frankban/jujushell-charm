#!/bin/sh

# Parse and output metrics for jujucharms.
# This script is assumed to be executed from the charm root directory.

port=`grep port files/config.yaml | awk '{print $2}'`
url="https://localhost:$port/metrics"
fsteal=../.venv/bin/fsteal

echo fetching $url >> /tmp/fsteal.log
echo sample: $1 >> /tmp/fsteal.log

echo `$fsteal $url --no-verify --format values-only -m $1 2>> /tmp/fsteal.log`
