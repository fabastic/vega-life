"""A status file being read by the UI at the wrong moment must never end a life (vega-6 died of exactly this)."""
import json
import os
import threading
import time

import pytest

from vegalife.trainer import write_json


def test_write_succeeds_after_a_reader_lets_go(tmp_path):
    path = tmp_path / "live.json"
    path.write_text("{}", encoding="utf-8")
    holder = open(path, "rb")                       # like the server reading it; on Windows this blocks a replace
    threading.Timer(0.2, holder.close).start()
    assert write_json(path, {"status": "running", "age": 1})
    assert json.loads(path.read_text(encoding="utf-8"))["age"] == 1


@pytest.mark.skipif(os.name != "nt", reason="only Windows refuses to replace an open file")
def test_a_file_held_open_for_long_does_not_raise(tmp_path):
    path = tmp_path / "live.json"
    path.write_text("{}", encoding="utf-8")
    with open(path, "rb"):
        t0 = time.time()
        ok = write_json(path, {"status": "running"})  # gives up quietly instead of crashing the trainer
        assert time.time() - t0 < 5
    assert ok in (True, False)
