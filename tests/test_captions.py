from __future__ import annotations

from showrunner.captions import generate_srt, split_text_for_subtitles, timecode
from showrunner.loader import BeatData


class TestTimecode:
    def test_zero_seconds(self):
        assert timecode(0.0) == "00:00:00,000"

    def test_seconds_only(self):
        assert timecode(3.5) == "00:00:03,500"

    def test_minutes(self):
        assert timecode(125.0) == "00:02:05,000"

    def test_hours(self):
        assert timecode(3661.0) == "01:01:01,000"

    def test_milliseconds_at_high_precision(self):
        assert timecode(1.234) == "00:00:01,234"

    def test_rounds_to_nearest_frame_at_24fps(self):
        result = timecode(1.0 / 24.0, fps=24.0)
        assert result == "00:00:00,041" or result == "00:00:00,042"


class TestSplitTextForSubtitles:
    def test_short_text_returns_single(self):
        assert split_text_for_subtitles("Hello world") == ["Hello world"]

    def test_splits_long_text_at_word_boundary(self):
        text = (
            "This is a very long sentence that should be split "
            "into multiple subtitle entries for readability"
        )
        chunks = split_text_for_subtitles(text, max_chars=42)
        assert len(chunks) >= 2
        assert all(len(c) <= 42 for c in chunks)

    def test_splits_keeps_words_intact(self):
        text = "Hello world how are you doing today"
        chunks = split_text_for_subtitles(text, max_chars=15)
        for chunk in chunks:
            assert not chunk.startswith(" ")
            assert not chunk.endswith(" ")
            assert chunk.strip() == chunk

    def test_single_word_longer_than_max(self):
        text = "Supercalifragilisticexpialidocious"
        chunks = split_text_for_subtitles(text, max_chars=10)
        assert len(chunks) > 1

    def test_custom_max_chars(self):
        text = "A B C D E F G H I J K L"
        chunks = split_text_for_subtitles(text, max_chars=5)
        assert all(len(c) <= 5 for c in chunks)

    def test_empty_text(self):
        assert split_text_for_subtitles("") == [""]

    def test_newlines_replaced_with_spaces(self):
        result = split_text_for_subtitles("Hello\nworld\nfoo")
        assert len(result) == 1
        assert result[0] == "Hello world foo"


class TestGenerateSrt:
    def test_single_beat(self):
        beats = [
            BeatData(
                beat_id="1", kind="speech", speaker="Maya",
                text="Hello world", duration_sec=3.0,
            ),
        ]
        result = generate_srt(beats)
        assert result == (
            "1\n00:00:00,000 --> 00:00:03,000\nMaya: Hello world\n"
        )

    def test_multiple_beats_sequential_numbering(self):
        beats = [
            BeatData(beat_id="1", kind="speech", speaker="Maya", text="First", duration_sec=3.0),
            BeatData(beat_id="2", kind="speech", speaker="Derek", text="Second", duration_sec=2.0),
        ]
        result = generate_srt(beats)
        lines = result.strip().split("\n\n")
        assert len(lines) == 2
        assert lines[0].startswith("1\n")
        assert lines[1].startswith("2\n")
        assert "Maya: First" in result
        assert "Derek: Second" in result

    def test_timing_sequential(self):
        beats = [
            BeatData(beat_id="1", kind="speech", text="First", duration_sec=3.0),
            BeatData(beat_id="2", kind="speech", text="Second", duration_sec=2.0),
        ]
        result = generate_srt(beats)
        assert "00:00:00,000 --> 00:00:03,000" in result
        assert "00:00:03,000 --> 00:00:05,000" in result

    def test_long_text_split_across_entries(self):
        text = (
            "This is a very long line of dialogue that should be split "
            "into multiple subtitle entries for the viewer to read comfortably"
        )
        beats = [
            BeatData(
                beat_id="1", kind="speech", speaker="Maya",
                text=text, duration_sec=6.0,
            ),
        ]
        result = generate_srt(beats, max_chars=42)
        entries = result.strip().split("\n\n")
        assert len(entries) >= 2
        assert "Maya: " in entries[0]
        assert "Maya: " not in entries[1]

    def test_split_entries_have_proper_timing(self):
        text = "This is a very long dialogue that will need to be split into two entries"
        beats = [
            BeatData(beat_id="1", kind="speech", speaker="Maya", text=text, duration_sec=6.0),
        ]
        result = generate_srt(beats, max_chars=42)
        entries = result.strip().split("\n\n")
        assert len(entries) == 2
        first_start, first_end = entries[0].split("\n")[1].split(" --> ")
        second_start, second_end = entries[1].split("\n")[1].split(" --> ")
        assert first_start == "00:00:00,000"
        assert second_start == first_end
        assert second_end == "00:00:06,000"

    def test_silent_beats_skipped(self):
        beats = [
            BeatData(beat_id="1", kind="speech", speaker="Maya", text="Hello", duration_sec=2.0),
            BeatData(beat_id="2", kind="silent", duration_sec=3.0),
            BeatData(beat_id="3", kind="speech", speaker="Derek", text="Hi", duration_sec=2.0),
        ]
        result = generate_srt(beats)
        entries = result.strip().split("\n\n")
        assert len(entries) == 2
        assert "Maya: Hello" in result
        assert "Derek: Hi" in result

    def test_empty_beats(self):
        result = generate_srt([])
        assert result == ""

    def test_fps_parameter_affects_timing(self):
        beats = [
            BeatData(beat_id="1", kind="speech", text="Hello", duration_sec=2.0),
        ]
        result_24 = generate_srt(beats, fps=24.0)
        result_30 = generate_srt(beats, fps=30.0)
        assert "00:00:00,000 --> 00:00:02,000" in result_24
        assert "00:00:00,000 --> 00:00:02,000" in result_30

    def test_text_with_newlines_sanitized(self):
        beats = [
            BeatData(
                beat_id="1", kind="speech", speaker="Maya",
                text="Line one\nLine two\r\nLine three", duration_sec=3.0,
            ),
        ]
        result = generate_srt(beats)
        assert "\nLine" not in result.split("Maya: ")[1].split("\n\n")[0]
        assert "Line one" in result
        assert "Line three" in result

    def test_missing_speaker_omits_prefix(self):
        beats = [
            BeatData(beat_id="1", kind="speech", text="Hello", duration_sec=2.0),
        ]
        result = generate_srt(beats)
        assert result.startswith("1\n")
        assert "Hello" in result
        assert ": Hello" not in result
