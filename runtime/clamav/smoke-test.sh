#!/usr/bin/env bash
set -eu
# CHECK:blocked_guard CHECK:clamd_socket CHECK:signature_freshness
echo "STATUS: BLOCKED"
exit 10
