#!/bin/sh
set -eu
# Frozen Tango command sequence. Execution is blocked until swap is fully disabled.
# Every future batch must independently verify MemAvailable >= 8 GiB and swap == 0.
# Every worker/child must be launched with nice -n 19; maximum workers: 2.
exec nice -n 19 /home/hledirach/Documents/J2/.venv/bin/python tango/src/tango_campaign.py --root tango --max-workers 2 --operation-timeout 60
