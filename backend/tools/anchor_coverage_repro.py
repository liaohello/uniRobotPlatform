"""Reproduce the M1.5g coverage defect and show the M1.5h correction on one fixture.

Run twice against the same isolated fixture archive, once with the frozen baseline sources on
PYTHONPATH and once with the corrected sources; the printed verdicts are the evidence.
Nothing here touches the real recording root: the fixture lives under a temp directory.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "src"))
sys.path.insert(0, sys.argv[2])

from test_episodes import _episode  # noqa: E402
from unirobot.episodes import EpisodeArchive, load_history_source  # noqa: E402
from unirobot.frames import FrameLinkReader  # noqa: E402

import test_frames  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="m1h-repro-"))
root = tmp / "runs"
directory = _episode(root, test_frames.RUN, test_frames.EPISODE)
test_frames._write_frames(directory, anchor_extra_lines="unparseable")
source, resolved = load_history_source(test_frames._source_file(tmp, root))
body = FrameLinkReader(EpisodeArchive(source, resolved)).frames(
    test_frames.EPISODE, run_id=test_frames.RUN, include_time_quality=True)
census = body["time_quality"]
coverage, schedule = census["coverage"], census["playback_eligibility"]["recorded_interval_schedule"]
print(json.dumps({
    "sources": sys.argv[1],
    "label": sys.argv[3],
    "anchor_file_lines": coverage["anchor_lines"],
    "whole_anchor_file_scanned": coverage.get("whole_anchor_file_scanned"),
    "reached_end_of_file": coverage.get("reached_end_of_file", "field_not_in_this_build"),
    "every_line_decided": coverage.get("line_accounting", {}).get("every_line_of_the_anchor_file_is_decided",
                                                                  "field_not_in_this_build"),
    "covers_whole_episode": coverage["covers_whole_episode"],
    "any_base_eligible_for_whole_episode": schedule["any_base_eligible_for_whole_episode"],
    "per_base_blocking": {field: item["blocking_reasons"] for field, item in schedule["eligible_by_base"].items()},
    "append_order_display_eligible": census["playback_eligibility"]["append_order_display"]["eligible"],
}, ensure_ascii=False, indent=1))
