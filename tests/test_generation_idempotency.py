"""
Regression tests: dataset generation is deterministic and idempotent, and it does not
rewrite historical manifests, catalogs, metadata or results when content is unchanged.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from src.imuca.synthetic_suite import (SyntheticSuiteGenerator, write_if_changed, write_json_if_changed,
                                       write_text_if_changed)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _snapshot(*roots):
    out = {}
    for r in roots:
        if os.path.isfile(r):
            out[r] = (os.stat(r).st_mtime_ns, _sha(r))
            continue
        for d, _, files in os.walk(r):
            for f in files:
                p = os.path.join(d, f)
                out[p] = (os.stat(p).st_mtime_ns, _sha(p))
    return out


def _sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _small_config(**changes):
    with open(os.path.join(ROOT, "config", "synthetic_suite_config.json"), "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["scenarios"] = [s for s in cfg["scenarios"] if s["scenario_id"] in ("VOLT_REPEATABILITY", "TEMP_INTEGRITY")]
    cfg.pop("fault_benchmark")
    cfg.update(changes)
    return cfg


def test_repeated_export_changes_nothing(tmp_path):
    g = SyntheticSuiteGenerator(_small_config())
    first = g.export(str(tmp_path))
    before = _snapshot(str(tmp_path))
    second = g.export(str(tmp_path))
    after = _snapshot(str(tmp_path))
    assert before == after, "second export modified files"
    assert set(second["file_status"].values()) == {"unchanged"}
    assert set(second["auxiliary_file_status"].values()) == {"unchanged"}
    assert second["manifest_written_utc"] == first["manifest_written_utc"]
    with open(tmp_path / "metadata" / "suite_manifest.json", encoding="utf-8") as f:
        stored = json.load(f)
    assert "file_status" not in stored and "auxiliary_file_status" not in stored


def test_legacy_line_endings_and_fields_do_not_trigger_rewrites(tmp_path):
    g = SyntheticSuiteGenerator(_small_config())
    g.export(str(tmp_path))
    meta_dir = tmp_path / "metadata"
    # Simulate historical files written in Windows text mode (CRLF) with the legacy file_status field
    man = json.loads((meta_dir / "suite_manifest.json").read_text(encoding="utf-8"))
    man["file_status"] = {s: "written" for s in ("VOLT_REPEATABILITY", "TEMP_INTEGRITY")}
    (meta_dir / "suite_manifest.json").write_bytes(json.dumps(man, indent=2).replace("\n", "\r\n").encode("utf-8"))
    for p in meta_dir.glob("*.metadata.json"):
        p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    before = _snapshot(str(tmp_path))
    g.export(str(tmp_path))
    assert _snapshot(str(tmp_path)) == before


def test_substantive_change_rewrites_but_keeps_data_provenance(tmp_path):
    g = SyntheticSuiteGenerator(_small_config())
    first = g.export(str(tmp_path))
    meta_path = tmp_path / "metadata" / "VOLT_REPEATABILITY.metadata.json"
    gen_ts = json.loads(meta_path.read_text(encoding="utf-8"))["generation_timestamp_utc"]
    csv_before = _snapshot(str(tmp_path / "voltage"))
    cfg = _small_config(disclaimer="Changed disclaimer text for the regression test.")
    second = SyntheticSuiteGenerator(cfg).export(str(tmp_path))
    assert second["auxiliary_file_status"]["suite_manifest.json"] == "updated"
    assert second["manifest_written_utc"] != first["manifest_written_utc"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["disclaimer"].startswith("Changed")
    assert meta["generation_timestamp_utc"] == gen_ts          # data unchanged -> original provenance kept
    assert _snapshot(str(tmp_path / "voltage")) == csv_before  # raw CSV untouched


def test_write_helpers_are_content_aware(tmp_path):
    p = tmp_path / "a.txt"
    assert write_text_if_changed(str(p), "x\ny\n") == "written"
    p.write_bytes(b"x\r\ny\r\n")
    assert write_text_if_changed(str(p), "x\ny\n") == "unchanged"
    assert write_text_if_changed(str(p), "x\nz\n") == "updated"
    j = tmp_path / "a.json"
    assert write_json_if_changed(str(j), {"b": 1, "a": [1, 2]}) == "written"
    assert write_json_if_changed(str(j), {"a": [1, 2], "b": 1}) == "unchanged"
    b = tmp_path / "a.bin"
    assert write_if_changed(str(b), b"1") == "written" and write_if_changed(str(b), b"1") == "unchanged"


@pytest.mark.parametrize("args", [[], ["--config", "config/synthetic_suite_v3_config.json", "--output-root", "data/synthetic_v3",
                                       "--catalog", "docs/DATASET_CATALOG_V3.md"]])
def test_default_generator_preserves_historical_files(args):
    """Running the generator on the real repository rewrites nothing in data/, docs/ or results/."""
    roots = [os.path.join(ROOT, p) for p in ("data/synthetic", "data/synthetic_v3", "docs", "results")]
    before = _snapshot(*roots)
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "generate_synthetic_suite.py"), *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, proc.stderr
    assert "catalog: unchanged" in proc.stdout
    assert _snapshot(*roots) == before
