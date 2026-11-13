#!/bin/sh
# Apply the exact A0-R2 -> A2d item 1 frameGenerator diff to an explicit copy.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh apply_frameGenerator_patch.sh /path/to/YaDyGaGa-copy" >&2
    exit 2
fi
target=$1
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -f "$target/yadygaga/frameGenerator.py" ]; then
    echo "target must contain yadygaga/frameGenerator.py" >&2
    exit 2
fi
base64 -d "$script_dir/frameGenerator.patch.gz.b64" | gzip -dc | patch --dry-run -p1 -d "$target"
base64 -d "$script_dir/frameGenerator.patch.gz.b64" | gzip -dc | patch -p1 -d "$target"
