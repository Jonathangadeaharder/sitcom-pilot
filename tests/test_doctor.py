from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from showrunner.cli.main import app
from showrunner.commands.doctor import (
    CheckResult,
    check_disk_space,
    check_ffmpeg,
    check_python,
    check_ram,
    check_uv,
    print_report,
    report_json,
    run_all,
)

runner = CliRunner()


class TestCheckResult:
    def test_construct(self):
        r = CheckResult("test", True, "detail")
        assert r.name == "test"
        assert r.passed is True
        assert r.detail == "detail"
        assert r.severity == "error"


class TestCheckPython:
    def test_ok(self):
        r = check_python()
        assert r.name == "python"
        assert r.passed is True
        assert f"{sys.version_info.major}" in r.detail


class TestCheckFfmpeg:
    def test_found(self):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0\n")
                r = check_ffmpeg()
        assert r.passed is True
        assert "6.0" in r.detail

    def test_found_subprocess_fails(self):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            with patch("subprocess.run", side_effect=RuntimeError):
                r = check_ffmpeg()
        assert r.passed is True
        assert "/usr/bin/ffmpeg" in r.detail

    def test_not_found(self):
        with patch("shutil.which", return_value=None):
            r = check_ffmpeg()
        assert r.passed is False
        assert "not found" in r.detail


class TestCheckUv:
    def test_found(self):
        with patch("shutil.which", return_value="/usr/bin/uv"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="uv 0.5.0\n")
                r = check_uv()
        assert r.passed is True
        assert "0.5.0" in r.detail

    def test_found_subprocess_fails(self):
        with patch("shutil.which", return_value="/usr/bin/uv"):
            with patch("subprocess.run", side_effect=RuntimeError):
                r = check_uv()
        assert r.passed is True
        assert "/usr/bin/uv" in r.detail

    def test_not_found(self):
        with patch("shutil.which", return_value=None):
            r = check_uv()
        assert r.passed is False
        assert "not found" in r.detail


class TestCheckDiskSpace:
    def test_enough_space(self):
        with patch("shutil.disk_usage") as mock_du:
            mock_du.return_value.total = 100 * 1024**3
            mock_du.return_value.used = 50 * 1024**3
            mock_du.return_value.free = 10 * 1024**3
            r = check_disk_space(min_gb=1)
        assert r.passed is True
        assert "GB free" in r.detail

    def test_low_space(self):
        with patch("shutil.disk_usage") as mock_du:
            mock_du.return_value.total = 100 * 1024**3
            mock_du.return_value.used = 99 * 1024**3
            mock_du.return_value.free = 512 * 1024**2
            r = check_disk_space(min_gb=1)
        assert r.passed is False

    def test_oserror(self):
        with patch("shutil.disk_usage", side_effect=OSError("no disk")):
            r = check_disk_space()
        assert r.passed is False
        assert "no disk" in r.detail


class TestCheckRam:
    def test_available(self):
        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        mock_mem.available = 4 * 1024**3
        mock_psutil.virtual_memory.return_value = mock_mem
        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            r = check_ram()
        assert r.passed is True
        assert "GB" in r.detail

    def test_low_ram(self):
        mock_psutil = MagicMock()
        mock_mem = MagicMock()
        mock_mem.available = 100 * 1024**2
        mock_psutil.virtual_memory.return_value = mock_mem
        with patch.dict("sys.modules", {"psutil": mock_psutil}):
            r = check_ram()
        assert r.passed is False

    def test_not_installed(self):
        r = check_ram()
        assert r.passed is True
        assert "skipped" in r.detail.lower()


class TestRunAll:
    def test_returns_all_checks(self):
        results = run_all()
        names = [r.name for r in results]
        assert "python" in names
        assert "ffmpeg" in names
        assert "uv" in names
        assert "disk_space" in names
        assert "ram" in names


class TestReportJson:
    def test_returns_valid_json(self):
        results = [CheckResult("a", True, "ok"), CheckResult("b", False, "fail")]
        text = report_json(results)
        data = json.loads(text)
        assert len(data) == 2
        assert data[0]["name"] == "a"
        assert data[0]["passed"] is True
        assert data[1]["name"] == "b"
        assert data[1]["passed"] is False


class TestPrintReport:
    def test_all_pass(self, capsys):
        results = [CheckResult("a", True, "ok")]
        print_report(results)
        captured = capsys.readouterr()
        assert "[PASS]" in captured.out
        assert "ok" not in captured.out

    def test_some_fail(self, capsys):
        results = [CheckResult("a", False, "missing")]
        print_report(results)
        captured = capsys.readouterr()
        assert "[FAIL]" in captured.out
        assert "missing" in captured.out

    def test_verbose_shows_detail(self, capsys):
        results = [CheckResult("a", True, "detail")]
        print_report(results, verbose=True)
        captured = capsys.readouterr()
        assert "[PASS]" in captured.out
        assert "detail" in captured.out


class TestDoctorCli:
    def test_doctor_all_pass(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("all", True, "ok")]
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "[PASS]" in result.output

    def test_doctor_some_fails(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [
                CheckResult("python", True, "3.11"),
                CheckResult("ffmpeg", False, "not found"),
            ]
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "[FAIL]" in result.output

    def test_doctor_json(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("python", True, "3.11")]
            result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["name"] == "python"
        assert data[0]["passed"] is True

    def test_doctor_json_fail(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("ffmpeg", False, "not found")]
            result = runner.invoke(app, ["doctor", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data[0]["passed"] is False

    def test_doctor_verbose(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("python", True, "3.11.0")]
            result = runner.invoke(app, ["doctor", "--verbose"])
        assert result.exit_code == 0
        assert "[PASS]" in result.output
        assert "3.11.0" in result.output
