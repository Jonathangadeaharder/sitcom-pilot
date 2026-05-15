from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from showrunner.cli.main import app
from showrunner.commands.doctor import CheckResult

runner = CliRunner()

V2_EPISODE = {
    "show": "TestShow",
    "season": 1,
    "episode": 1,
    "title": "Test Episode",
    "schema_version": "2.0",
    "cast": {
        "alice": {
            "name": "Alice",
            "visual": "a tall woman with red hair",
            "reference_images": [],
            "voice": {
                "provider": "mlx-audio",
                "voice_id": "alice_v1",
                "seed": 42,
                "temperature": 0.8,
                "language": "en",
            },
        },
    },
    "environments": {
        "office": {
            "trigger_word": "office",
            "style": "modern tech office",
        },
    },
    "scenes": [
        {
            "scene_id": "S01",
            "environment": "office",
            "characters_present": ["alice"],
            "beats": [
                {
                    "beat_id": "S01_B01",
                    "kind": "speech",
                    "speaker": "alice",
                    "text": "Hello world",
                    "action": "Alice enters the office",
                    "duration_sec": 3.0,
                    "seed": 100,
                },
                {
                    "beat_id": "S01_B02",
                    "kind": "silent",
                    "action": "Alice looks around",
                    "duration_sec": 2.0,
                    "seed": 101,
                },
            ],
        },
    ],
}


def _write_episode(tmp_path: Path, data: dict | None = None) -> Path:
    ep = tmp_path / "episode.json"
    payload = V2_EPISODE if data is None else data
    ep.write_text(json.dumps(payload))
    return ep


# ---------------------------------------------------------------------------
# E7.1: validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_episode(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["validate", str(ep)])
        assert result.exit_code == 0
        assert "Valid:" in result.output

    def test_invalid_episode_missing_cast(self, tmp_path: Path):
        bad = {"schema_version": "2.0", "show": "X", "title": "Y", "environments": {}, "scenes": []}
        ep = _write_episode(tmp_path, bad)
        result = runner.invoke(app, ["validate", str(ep)])
        assert result.exit_code == 1

    def test_invalid_json(self, tmp_path: Path):
        ep = tmp_path / "bad.json"
        ep.write_text("not json{{{")
        result = runner.invoke(app, ["validate", str(ep)])
        assert result.exit_code == 1

    def test_nonexistent_file(self, tmp_path: Path):
        result = runner.invoke(app, ["validate", str(tmp_path / "nope.json")])
        assert result.exit_code == 1

    def test_strict_mode(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["validate", str(ep), "--strict"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# E7.2: plan
# ---------------------------------------------------------------------------


class TestPlan:
    def test_plan_shows_beats(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["plan", str(ep)])
        assert result.exit_code == 0
        assert '"beat_number": 1' in result.output
        assert '"beat_number": 2' in result.output
        assert '"type": "speech"' in result.output
        assert '"type": "silent"' in result.output

    def test_plan_verbose(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["plan", str(ep), "--verbose"])
        assert result.exit_code == 0

    def test_plan_bad_file(self, tmp_path: Path):
        result = runner.invoke(app, ["plan", str(tmp_path / "nope.json")])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# E7.3: bootstrap
# ---------------------------------------------------------------------------


class TestBootstrap:
    def test_creates_correct_structure(self, tmp_path: Path):
        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["bootstrap", "my-episode"])
        finally:
            os.chdir(old)
        assert result.exit_code == 0
        d = tmp_path / "my-episode"
        assert d.is_dir()
        assert (d / "episode.json").is_file()
        assert (d / "scenes").is_dir()
        assert (d / "output").is_dir()
        assert (d / "assets").is_dir()

    def test_writes_valid_json_that_passes_validate(self, tmp_path: Path):
        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["bootstrap", "my-episode"])
        finally:
            os.chdir(old)
        assert result.exit_code == 0
        ep = tmp_path / "my-episode" / "episode.json"
        result2 = runner.invoke(app, ["validate", str(ep)])
        assert result2.exit_code == 0
        assert "Valid" in result2.output

    def test_force_overwrites(self, tmp_path: Path):
        d = tmp_path / "my-episode"
        d.mkdir()
        (d / "old.txt").write_text("old")
        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["bootstrap", "my-episode", "--force"])
        finally:
            os.chdir(old)
        assert result.exit_code == 0
        assert not (d / "old.txt").exists()
        assert (d / "episode.json").is_file()

    def test_no_assets_omits_assets_dir(self, tmp_path: Path):
        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["bootstrap", "my-episode", "--no-assets"])
        finally:
            os.chdir(old)
        assert result.exit_code == 0
        d = tmp_path / "my-episode"
        assert d.is_dir()
        assert (d / "scenes").is_dir()
        assert (d / "output").is_dir()
        assert not (d / "assets").exists()

    def test_invalid_name_rejected(self, tmp_path: Path):
        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["bootstrap", "my/episode"])
        finally:
            os.chdir(old)
        assert result.exit_code == 1
        assert "/" in result.output or "Error" in result.output

        old = Path.cwd()
        try:
            os.chdir(tmp_path)
            result2 = runner.invoke(app, ["bootstrap", "my\\episode"])
        finally:
            os.chdir(old)
        assert result2.exit_code == 1


# ---------------------------------------------------------------------------
# E7.4: render commands
# ---------------------------------------------------------------------------


class TestRenderBeat:
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_render_beat_success(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app, ["render", "beat", str(ep), "S01_B01", "--output-dir", str(out)]
        )
        assert result.exit_code == 0

    def test_render_beat_not_found(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["render", "beat", str(ep), "NONEXISTENT"])
        assert result.exit_code == 1


class TestRenderScene:
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_render_scene_success(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(app, ["render", "scene", str(ep), "S01", "--output-dir", str(out)])
        assert result.exit_code == 0

    def test_render_scene_not_found(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["render", "scene", str(ep), "NONEXISTENT"])
        assert result.exit_code == 1


class TestRenderEpisode:
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_render_episode_success(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(app, ["render", "episode", str(ep), "--output-dir", str(out)])
        assert result.exit_code == 0
        assert "Done:" in result.output


# ---------------------------------------------------------------------------
# E7.5: assemble
# ---------------------------------------------------------------------------


class TestAssemble:
    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.assembler.generate_srt")
    def test_assemble_with_clips(self, mock_srt, mock_concat, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        run_dir = out / "test-run"
        beats_dir = run_dir / "beats" / "S01"
        beats_dir.mkdir(parents=True)

        (beats_dir / "S01_B01.mp4").write_bytes(b"fake")
        (beats_dir / "S01_B02.mp4").write_bytes(b"fake")
        assembly_dir = run_dir / "assembly"
        assembly_dir.mkdir(parents=True)

        mock_concat.return_value = assembly_dir / "episode_raw.mp4"
        mock_srt.return_value = assembly_dir / "episode.srt"

        result = runner.invoke(
            app, ["assemble", str(ep), "--output-dir", str(out), "--run-id", "test-run"]
        )
        assert result.exit_code == 0
        assert "Assembly complete" in result.output

    def test_assemble_no_runs(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "empty_output"
        result = runner.invoke(app, ["assemble", str(ep), "--output-dir", str(out)])
        assert result.exit_code == 1

    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.assembler.generate_srt")
    @patch("showrunner.assembler.burn_in_captions")
    def test_assemble_with_captions(self, mock_burn, mock_srt, mock_concat, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        run_dir = out / "test-run"
        beats_dir = run_dir / "beats" / "S01"
        beats_dir.mkdir(parents=True)
        (beats_dir / "S01_B01.mp4").write_bytes(b"fake")
        (beats_dir / "S01_B02.mp4").write_bytes(b"fake")
        assembly_dir = run_dir / "assembly"
        assembly_dir.mkdir(parents=True)

        mock_concat.return_value = assembly_dir / "episode_raw.mp4"
        mock_srt.return_value = assembly_dir / "episode.srt"
        mock_burn.return_value = assembly_dir / "episode.mp4"

        result = runner.invoke(
            app,
            ["assemble", str(ep), "--output-dir", str(out), "--run-id", "test-run", "--captions"],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# E9.4: showcase
# ---------------------------------------------------------------------------


class TestShowcase:
    @patch("showrunner.assembler.extract_thumbnail")
    @patch("showrunner.assembler.concat_clips")
    def test_showcase_scene_by_id(self, mock_concat, mock_thumb, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        run_dir = out / "test-run"
        beats_dir = run_dir / "beats" / "S01"
        beats_dir.mkdir(parents=True)
        (beats_dir / "S01_B01.mp4").write_bytes(b"fake")
        (beats_dir / "S01_B02.mp4").write_bytes(b"fake")
        showcase_dir = run_dir / "showcase"
        showcase_dir.mkdir(parents=True)

        mock_concat.return_value = showcase_dir / "S01.mp4"
        mock_thumb.return_value = showcase_dir / "S01.jpg"

        result = runner.invoke(
            app,
            [
                "showcase",
                str(ep),
                "--scene",
                "S01",
                "--output-dir",
                str(out),
                "--run-id",
                "test-run",
            ],
        )
        assert result.exit_code == 0
        assert "Showcase" in result.output

    @patch("showrunner.assembler.extract_thumbnail")
    @patch("showrunner.assembler.concat_clips")
    def test_showcase_scene_by_index(self, mock_concat, mock_thumb, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        run_dir = out / "test-run"
        beats_dir = run_dir / "beats" / "S01"
        beats_dir.mkdir(parents=True)
        (beats_dir / "S01_B01.mp4").write_bytes(b"fake")
        (beats_dir / "S01_B02.mp4").write_bytes(b"fake")
        showcase_dir = run_dir / "showcase"
        showcase_dir.mkdir(parents=True)

        mock_concat.return_value = showcase_dir / "S01.mp4"
        mock_thumb.return_value = showcase_dir / "S01.jpg"

        result = runner.invoke(
            app,
            ["showcase", str(ep), "--scene", "1", "--output-dir", str(out), "--run-id", "test-run"],
        )
        assert result.exit_code == 0
        assert "Showcase" in result.output

    def test_showcase_scene_not_found(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app,
            ["showcase", str(ep), "--scene", "NONEXISTENT", "--output-dir", str(out)],
        )
        assert result.exit_code == 1

    def test_showcase_no_rendered_clips(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "showcase",
                str(ep),
                "--scene",
                "S01",
                "--output-dir",
                str(out),
                "--run-id",
                "test-run",
            ],
        )
        assert result.exit_code == 1
        assert "No rendered clips" in result.output


# ---------------------------------------------------------------------------
# E7.6: doctor
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_all_ok(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("all", True, "ok")]
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "[PASS]" in result.output

    def test_doctor_missing_ffmpeg(self):
        with patch("showrunner.commands.doctor.run_all") as mock_run:
            mock_run.return_value = [CheckResult("ffmpeg", False, "not found")]
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "[FAIL]" in result.output


# ---------------------------------------------------------------------------
# E7.7: run (full pipeline)
# ---------------------------------------------------------------------------


class TestRun:
    @patch("showrunner.assembler.generate_srt")
    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_run_validates_and_renders(
        self, mock_client_cls, mock_concat, mock_srt, tmp_path: Path
    ):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client
        mock_concat.return_value = tmp_path / "output" / "run" / "assembly" / "episode_raw.mp4"
        mock_srt.return_value = tmp_path / "output" / "run" / "assembly" / "episode.srt"

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app,
            ["run", str(ep), "--output-dir", str(out), "--skip-bootstrap"],
        )
        assert result.exit_code == 0
        assert "Episode validated" in result.output
        assert "Bootstrap skipped" in result.output
        assert "Rendered" in result.output
        assert "Pipeline Summary" in result.output

    def test_run_fails_invalid_episode(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid")
        result = runner.invoke(app, ["run", str(bad), "--skip-bootstrap"])
        assert result.exit_code == 1

    @patch("showrunner.assembler.generate_srt")
    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_run_bootstrap_skipped(self, mock_client_cls, mock_concat, mock_srt, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client
        mock_concat.return_value = tmp_path / "output" / "run" / "assembly" / "episode_raw.mp4"
        mock_srt.return_value = tmp_path / "output" / "run" / "assembly" / "episode.srt"

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(app, ["run", str(ep), "--output-dir", str(out), "--skip-bootstrap"])
        assert "Bootstrap skipped" in result.output
        assert result.exit_code == 0

    @patch("showrunner.assembler.generate_srt")
    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_run_skip_validate(self, mock_client_cls, mock_concat, mock_srt, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client
        mock_concat.return_value = tmp_path / "output" / "run" / "assembly" / "episode_raw.mp4"
        mock_srt.return_value = tmp_path / "output" / "run" / "assembly" / "episode.srt"

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app,
            ["run", str(ep), "--output-dir", str(out), "--skip-validate", "--skip-bootstrap"],
        )
        assert "Validation skipped" in result.output
        assert result.exit_code == 0

    @patch("showrunner.assembler.generate_srt")
    @patch("showrunner.assembler.concat_clips")
    @patch("showrunner.aiservices_client.AIServicesClient")
    def test_run_verbose(self, mock_client_cls, mock_concat, mock_srt, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/img.png")
        mock_client.image2video.return_value = Path("/tmp/vid.mp4")
        mock_client_cls.return_value = mock_client
        mock_concat.return_value = tmp_path / "output" / "run" / "assembly" / "episode_raw.mp4"
        mock_srt.return_value = tmp_path / "output" / "run" / "assembly" / "episode.srt"

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(
            app,
            ["run", str(ep), "--output-dir", str(out), "--skip-bootstrap", "--verbose"],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# No-args shows help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0 or result.exit_code == 2
        assert "Usage" in result.output

    def test_help_has_no_provider_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--provider" not in result.output
        assert "--backend" not in result.output
        assert "--engine" not in result.output

    def test_subcommand_help_no_provider_flags(self):
        for cmd_args in [
            ["validate", "--help"],
            ["plan", "--help"],
            ["bootstrap", "--help"],
            ["render", "beat", "--help"],
            ["render", "scene", "--help"],
            ["render", "episode", "--help"],
            ["assemble", "--help"],
            ["doctor", "--help"],
        ]:
            result = runner.invoke(app, cmd_args)
            assert result.exit_code == 0, f"{cmd_args} failed: {result.output}"
            assert "--provider" not in result.output, f"{cmd_args} contains --provider"
            assert "--backend" not in result.output, f"{cmd_args} contains --backend"
            assert "--engine" not in result.output, f"{cmd_args} contains --engine"
