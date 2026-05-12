from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "error"


Check = Callable[[], CheckResult]


def check_python() -> CheckResult:
    ok = sys.version_info >= (3, 10)
    detail = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return CheckResult("python", ok, detail)


def check_ffmpeg() -> CheckResult:
    path = shutil.which("ffmpeg")
    if path:
        try:
            r = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
            ver = r.stdout.split("\n")[0] if r.stdout else path
        except Exception:
            ver = path
        return CheckResult("ffmpeg", True, ver)
    return CheckResult("ffmpeg", False, "not found")


def check_uv() -> CheckResult:
    path = shutil.which("uv")
    if path:
        try:
            r = subprocess.run([path, "version"], capture_output=True, text=True, timeout=10)
            ver = r.stdout.strip() if r.stdout else path
        except Exception:
            ver = path
        return CheckResult("uv", True, ver)
    return CheckResult("uv", False, "not found")


def check_disk_space(min_gb: int = 1) -> CheckResult:
    tmp = Path(tempfile.gettempdir())
    try:
        usage = shutil.disk_usage(tmp)
        free_gb = usage.free / (1024**3)
        ok = free_gb >= min_gb
        return CheckResult("disk_space", ok, f"{free_gb:.1f} GB free in {tmp}")
    except OSError as exc:
        return CheckResult("disk_space", False, str(exc))


def check_ram() -> CheckResult:
    try:
        import psutil

        mem = psutil.virtual_memory()
        avail_gb = mem.available / (1024**3)
        ok = avail_gb >= 0.5
        return CheckResult("ram", ok, f"{avail_gb:.1f} GB available")
    except ImportError:
        return CheckResult("ram", True, "psutil not installed — skipped")


def run_all() -> list[CheckResult]:
    return [
        check_python(),
        check_ffmpeg(),
        check_uv(),
        check_disk_space(),
        check_ram(),
    ]


def report_json(results: list[CheckResult]) -> str:
    rows = [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results]
    return json.dumps(rows, indent=2)


def print_report(results: list[CheckResult], verbose: bool = False) -> None:
    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        line = f"[{icon}] {r.name}"
        if verbose or not r.passed:
            line += f" — {r.detail}"
        print(line)
