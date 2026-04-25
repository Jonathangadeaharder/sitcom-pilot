import sys

collect_ignore = []
if "mutmut" in sys.modules:
    collect_ignore = ["test_cli.py", "test_e2e.py", "test_episode_01.py"]
