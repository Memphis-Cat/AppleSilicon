#!/usr/bin/env bash

set -uo pipefail

VERSION="0.2.0.0.0.0"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"

mkdir -p "${LOG_DIR}"

TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-${TIMESTAMP}-$$.log"

if [[ $# -eq 0 ]]; then
    {
        echo "AppleSilicon logged runner"
        echo "Version: ${VERSION}"
        echo "Error: no command was provided"
        echo "Usage: $0 <command> [arguments...]"
    } | tee "${LOG_FILE}"
    exit 64
fi

print_command() {
    local arg
    local first=1

    for arg in "$@"; do
        if [[ ${first} -eq 0 ]]; then
            printf ' '
        fi

        case "${arg,,}" in
            *password=*|*passwd=*|*token=*|*secret=*|*private-key=*|*private_key=*|*ticket=*)
                printf '<redacted>'
                ;;
            *)
                printf '%q' "${arg}"
                ;;
        esac

        first=0
    done

    printf '\n'
}

set +e
{
    echo "============================================================"
    echo "AppleSilicon run log"
    echo "============================================================"
    echo "Version: ${VERSION}"
    echo "Timestamp UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
    echo "Host release: $(uname -r 2>/dev/null || echo unknown)"
    echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
    echo "Working directory: $(pwd)"
    echo "Log file: ${LOG_FILE}"
    printf 'Command: '
    print_command "$@"
    echo "------------------------------------------------------------"

    "$@"
    COMMAND_STATUS=$?

    echo "------------------------------------------------------------"
    echo "Exit code: ${COMMAND_STATUS}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "============================================================"

    exit "${COMMAND_STATUS}"
} 2>&1 | tee "${LOG_FILE}"

RUN_STATUS=${PIPESTATUS[0]}
set -e

exit "${RUN_STATUS}"
