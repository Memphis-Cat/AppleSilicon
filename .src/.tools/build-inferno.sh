#!/usr/bin/env bash

set -Eeuo pipefail

VERSION="0.2.0.0.0.0"
EXPECTED_INFERNO_REVISION="cc4302a99167abec69b714cfd00c38caece7e7de"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${APPLESILICON_INFERNO_SOURCE:-${ROOT_DIR}/.src/.upstream/.inferno}"
BUILD_DIR="${APPLESILICON_INFERNO_BUILD_DIR:-${ROOT_DIR}/.build/inferno}"
LOG_DIR="${APPLESILICON_LOG_DIR:-${ROOT_DIR}/.logs}"
TARGETS="${APPLESILICON_BUILD_TARGETS:-aarch64-softmmu,x86_64-softmmu}"
MODE="build"

if [[ ${1:-} == "--preflight-only" ]]; then
    MODE="preflight"
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--preflight-only]" >&2
    exit 64
fi

mkdir -p "${LOG_DIR}"
TIMESTAMP="$(date -u +"%Y%m%d-%H%M%S")"
LOG_FILE="${LOG_DIR}/AppleSilicon-build-inferno-${TIMESTAMP}-$$.log"
STARTED_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
FINAL_STAGE="startup"

exec > >(tee "${LOG_FILE}") 2>&1

on_exit() {
    local status=$?
    trap - EXIT
    echo "------------------------------------------------------------"
    echo "Final stage: ${FINAL_STAGE}"
    echo "Exit code: ${status}"
    echo "Finished UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "Log file: ${LOG_FILE}"
    echo "============================================================"
    exit "${status}"
}
trap on_exit EXIT

quote_command() {
    local arg
    for arg in "$@"; do printf '%q ' "${arg}"; done
    printf '\n'
}

require_command() {
    local command_name="$1"
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Missing required command: ${command_name}" >&2
        return 1
    fi
}

version_of() {
    local label="$1"
    shift
    printf '%s: ' "${label}"
    "$@" 2>&1 | head -n 1 || true
}

detect_jobs() {
    local jobs
    if [[ -n ${APPLESILICON_JOBS:-} ]]; then
        jobs="${APPLESILICON_JOBS}"
    elif command -v nproc >/dev/null 2>&1; then
        jobs="$(nproc)"
    elif command -v sysctl >/dev/null 2>&1; then
        jobs="$(sysctl -n hw.logicalcpu 2>/dev/null || true)"
    else
        jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)"
    fi
    [[ "${jobs}" =~ ^[0-9]+$ ]] && (( jobs >= 1 )) || {
        echo "Parallel job count must be a positive integer; observed: ${jobs:-<empty>}" >&2
        return 1
    }
    printf '%s\n' "${jobs}"
}

run_stage() {
    local name="$1"
    shift
    local status
    FINAL_STAGE="${name}"
    echo "------------------------------------------------------------"
    echo "Stage: ${name}"
    printf 'Command: '
    quote_command "$@"
    set +e
    "$@"
    status=$?
    set -e
    echo "Stage exit code: ${status}"
    return "${status}"
}

safe_reset_build_directory() {
    local normalized_build normalized_root
    normalized_build="$(python3 - "${BUILD_DIR}" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || return 1
    normalized_root="$(python3 - "${ROOT_DIR}/.build" <<'PY'
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve(strict=False))
PY
)" || return 1
    case "${normalized_build}" in
        ""|"/"|"${ROOT_DIR}"|"${HOME}"|"${normalized_root}")
            echo "Refusing unsafe build directory reset: ${BUILD_DIR}" >&2
            return 1
            ;;
    esac
    if [[ "${normalized_build}" != "${normalized_root}/"* ]]; then
        echo "Refusing to delete build directory outside ${normalized_root}: ${BUILD_DIR}" >&2
        echo "Use the default project build directory for the reproducible baseline." >&2
        return 1
    fi
    BUILD_DIR="${normalized_build}"
    rm -rf -- "${BUILD_DIR}"
    mkdir -p "${BUILD_DIR}"
}

echo "============================================================"
echo "AppleSilicon Inferno build baseline"
echo "============================================================"
echo "AppleSilicon version: ${VERSION}"
echo "Started UTC: ${STARTED_UTC}"
echo "Mode: ${MODE}"
echo "Host OS: $(uname -s 2>/dev/null || echo unknown)"
echo "Host release: $(uname -r 2>/dev/null || echo unknown)"
echo "Host architecture: $(uname -m 2>/dev/null || echo unknown)"
echo "Project root: ${ROOT_DIR}"
echo "Inferno source: ${SOURCE_DIR}"
echo "Build directory: ${BUILD_DIR}"
echo "Target list: ${TARGETS}"
echo "Expected Inferno revision: ${EXPECTED_INFERNO_REVISION}"
echo "Log file: ${LOG_FILE}"

FINAL_STAGE="tool-preflight"
require_command git
require_command python3
require_command make
require_command meson
require_command ninja

if command -v pkg-config >/dev/null 2>&1; then
    PKG_CONFIG_BIN="pkg-config"
elif command -v pkgconf >/dev/null 2>&1; then
    PKG_CONFIG_BIN="pkgconf"
else
    echo "Missing required command: pkg-config or pkgconf" >&2
    exit 1
fi

if command -v cc >/dev/null 2>&1; then
    CC_BIN="cc"
elif command -v clang >/dev/null 2>&1; then
    CC_BIN="clang"
elif command -v gcc >/dev/null 2>&1; then
    CC_BIN="gcc"
else
    echo "Missing C compiler: cc, clang, or gcc" >&2
    exit 1
fi

version_of "Git" git --version
version_of "Python" python3 --version
version_of "Make" make --version
version_of "Meson" meson --version
version_of "Ninja" ninja --version
version_of "pkg-config" "${PKG_CONFIG_BIN}" --version
version_of "C compiler" "${CC_BIN}" --version

FINAL_STAGE="submodule-initialization"
if [[ "${SOURCE_DIR}" == "${ROOT_DIR}/.src/.upstream/.inferno" ]]; then
    run_stage "submodule-initialization" git -C "${ROOT_DIR}" submodule update --init --recursive -- ".src/.upstream/.inferno"
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "Inferno source directory does not exist: ${SOURCE_DIR}" >&2
    exit 1
fi
if ! git -C "${SOURCE_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Inferno source path is not a Git work tree: ${SOURCE_DIR}" >&2
    exit 1
fi

FINAL_STAGE="revision-validation"
OBSERVED_REVISION="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
echo "Observed Inferno revision: ${OBSERVED_REVISION}"
if [[ "${OBSERVED_REVISION}" != "${EXPECTED_INFERNO_REVISION}" ]]; then
    echo "Inferno revision mismatch." >&2
    echo "Expected: ${EXPECTED_INFERNO_REVISION}" >&2
    echo "Observed: ${OBSERVED_REVISION}" >&2
    exit 1
fi
DIRTY_STATUS="$(git -C "${SOURCE_DIR}" status --porcelain --untracked-files=no)"
if [[ -n "${DIRTY_STATUS}" ]]; then
    echo "Inferno tracked source contains local modifications; refusing a baseline build." >&2
    printf '%s\n' "${DIRTY_STATUS}" >&2
    exit 1
fi

FINAL_STAGE="dependency-report"
for package in glib-2.0 pixman-1 gnutls nettle; do
    if "${PKG_CONFIG_BIN}" --exists "${package}" 2>/dev/null; then
        echo "Dependency ${package}: $("${PKG_CONFIG_BIN}" --modversion "${package}" 2>/dev/null || echo present)"
    else
        echo "Dependency ${package}: not visible through ${PKG_CONFIG_BIN}; configure will perform the authoritative check"
    fi
done

if [[ "${MODE}" == "preflight" ]]; then
    FINAL_STAGE="preflight-complete"
    echo "P1.02 preflight completed successfully."
    exit 0
fi

JOBS="$(detect_jobs)" || exit 1
echo "Parallel jobs: ${JOBS}"

FINAL_STAGE="build-directory-reset"
safe_reset_build_directory

COMMON_CONFIGURE=(
    "${SOURCE_DIR}/configure"
    "--target-list=${TARGETS}"
    "--disable-guest-agent"
    "--enable-slirp"
    "--enable-lzfse"
    "--enable-nettle"
    "--enable-gnutls"
    "--disable-werror"
)
HOST_OS="$(uname -s)"
if [[ "${HOST_OS}" == "Darwin" ]]; then
    require_command brew
    BREW_PREFIX="$(brew --prefix)"
    CONFIGURE_COMMAND=(
        env
        "LIBTOOL=glibtool"
        "${COMMON_CONFIGURE[@]}"
        "--enable-curses"
        "--enable-libssh"
        "--enable-virtfs"
        "--enable-zstd"
        "--disable-sdl"
        "--disable-gtk"
        "--enable-cocoa"
        "--extra-cflags=-DNCURSES_WIDECHAR=1 -I${BREW_PREFIX}/include"
        "--extra-ldflags=-L${BREW_PREFIX}/lib"
    )
elif [[ "${HOST_OS}" == "Linux" ]]; then
    CONFIGURE_COMMAND=("${COMMON_CONFIGURE[@]}")
else
    echo "P1.02 currently defines reference build profiles only for macOS and Linux." >&2
    exit 1
fi

pushd "${BUILD_DIR}" >/dev/null
run_stage "configure" "${CONFIGURE_COMMAND[@]}"
run_stage "compile" make -j"${JOBS}"
popd >/dev/null

QEMU_AARCH64="${BUILD_DIR}/qemu-system-aarch64"
FINAL_STAGE="artifact-verification"
if [[ ! -x "${QEMU_AARCH64}" ]]; then
    echo "Build completed without an executable qemu-system-aarch64 at ${QEMU_AARCH64}" >&2
    exit 1
fi
echo "qemu-system-aarch64: ${QEMU_AARCH64}"
"${QEMU_AARCH64}" --version
FINAL_STAGE="p1.02-complete"
echo "P1.02 reproducible Inferno build baseline completed successfully."
