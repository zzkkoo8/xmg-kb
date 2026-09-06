#!/usr/bin/env bash
set -eu
# CHECK:blocked_guard CHECK:prefect_api CHECK:postgres_dependency
echo "STATUS: BLOCKED"
exit 10
