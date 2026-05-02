from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sitcom_pilot.cli.main import app

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
        assert "OK" in result.output

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
        assert "S01_B01" in result.output
        assert "S01_B02" in result.output
        assert "Total beats: 2" in result.output

    def test_plan_verbose(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["plan", str(ep), "--verbose"])
        assert result.exit_code == 0
        assert "Prompt" in result.output

    def test_plan_bad_file(self, tmp_path: Path):
        result = runner.invoke(app, ["plan", str(tmp_path / "nope.json")])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# E7.3: bootstrap
# ---------------------------------------------------------------------------


class TestBootstrap:
    @patch("sitcom_pilot.aiservices_client.AIServicesClient")
    def test_bootstrap_generates_refs(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.return_value = Path("/tmp/ref.png")
        mock_client_cls.return_value = mock_client

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(app, ["bootstrap", str(ep), "--output-dir", str(out)])
        assert result.exit_code == 0
        assert "Bootstrap complete" in result.output
        manifest_path = out / "bootstrap" / "cast_manifest.json"
        assert manifest_path.exists()

    @patch("sitcom_pilot.aiservices_client.AIServicesClient")
    def test_bootstrap_handles_failure(self, mock_client_cls, tmp_path: Path):
        mock_client = MagicMock()
        mock_client.text2image.side_effect = RuntimeError("boom")
        mock_client_cls.return_value = mock_client

        ep = _write_episode(tmp_path)
        out = tmp_path / "output"
        result = runner.invoke(app, ["bootstrap", str(ep), "--output-dir", str(out)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# E7.4: render commands
# ---------------------------------------------------------------------------


class TestRenderBeat:
    @patch("sitcom_pilot.aiservices_client.AIServicesClient")
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
    @patch("sitcom_pilot.aiservices_client.AIServicesClient")
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
    @patch("sitcom_pilot.aiservices_client.AIServicesClient")
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
    @patch("sitcom_pilot.assembler.concat_clips")
    @patch("sitcom_pilot.assembler.generate_srt")
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

    @patch("sitcom_pilot.assembler.concat_clips")
    @patch("sitcom_pilot.assembler.generate_srt")
    @patch("sitcom_pilot.assembler.burn_in_captions")
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
# E7.6: doctor
# ---------------------------------------------------------------------------


class TestDoctor:
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("subprocess.run")
    def test_doctor_all_ok(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(stdout="ffmpeg version 6.0")
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "All dependencies OK" in result.output

    @patch("shutil.which", return_value=None)
    def test_doctor_missing_ffmpeg(self, mock_which):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# E7.7: Legacy run command
# ---------------------------------------------------------------------------


class TestLegacyRun:
    def test_run_command_deprecated(self, tmp_path: Path):
        ep = _write_episode(tmp_path)
        result = runner.invoke(app, ["run", str(ep)])
        assert result.exit_code == 1
        assert "deprecated" in result.output.lower()


# ---------------------------------------------------------------------------
# No-args shows help
# ---------------------------------------------------------------------------


class TestHelp:
    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0 or result.exit_code == 2
        assert "Usage" in result.output
