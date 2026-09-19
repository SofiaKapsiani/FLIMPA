"""Mask file naming and resolution."""

from pathlib import Path

import numpy as np
import pytest

from utils.mask_io import (
    MASK_KIND_POLYGON,
    default_mask_filename,
    ensure_tif_path,
    file_stem,
    mask_path_for,
    resolve_mask_from_files,
    resolve_mask_path,
    save_mask_tif,
)


def test_file_stem():
    assert file_stem("sample_01.tif") == "sample_01"
    assert file_stem("sample_01") == "sample_01"


def test_mask_path_for():
    p = mask_path_for("cell_a", "ROI", "/tmp")
    assert p.name == "cell_a_mask_ROI.tif"
    p2 = mask_path_for("cell_a", MASK_KIND_POLYGON, "/tmp")
    assert p2.name == "cell_a_mask_polygon.tif"


def test_default_mask_filename():
    assert default_mask_filename("cell_a", "ROI") == "cell_a_mask_ROI.tif"
    assert default_mask_filename("cell_a", MASK_KIND_POLYGON) == "cell_a_mask_polygon.tif"


def test_ensure_tif_path():
    assert ensure_tif_path("my_mask").name == "my_mask.tif"
    assert ensure_tif_path("my_mask.png").name == "my_mask.tif"
    assert ensure_tif_path("already.tif").name == "already.tif"


def test_resolve_mask_path_priority(tmp_path):
    stem = "sample"
    segmentation = tmp_path / f"{stem}_segmentation.tif"
    segmentation.write_bytes(b"")
    assert resolve_mask_path(tmp_path, stem) == segmentation

    segmentation.unlink()
    roi = tmp_path / f"{stem}_mask_ROI.tif"
    roi.write_bytes(b"")
    assert resolve_mask_path(tmp_path, stem) == roi


def test_resolve_mask_path_legacy_space_name(tmp_path):
    stem = "sample"
    legacy = tmp_path / f"{stem} segmentation.tif"
    legacy.write_bytes(b"")
    assert resolve_mask_path(tmp_path, stem) == legacy


def test_resolve_mask_path_polygon(tmp_path):
    stem = "sample"
    polygon = tmp_path / f"{stem}_mask_polygon.tif"
    polygon.write_bytes(b"")
    extra = tmp_path / f"{stem}_mask_extra.tif"
    extra.write_bytes(b"")
    assert resolve_mask_path(tmp_path, stem) == polygon


def test_resolve_mask_from_files_exact_name(tmp_path):
    stem = "sample"
    roi = tmp_path / f"{stem}_mask_ROI.tif"
    roi.write_bytes(b"")
    other = tmp_path / "other_mask_polygon.tif"
    other.write_bytes(b"")
    assert resolve_mask_from_files(stem, [roi, other]) == roi


def test_resolve_mask_from_files_stem_prefix(tmp_path):
    stem = "treated40uM_3"
    custom = tmp_path / f"{stem}_mask_polygon_1.tif"
    custom.write_bytes(b"")
    assert resolve_mask_from_files(stem, [custom]) == custom


def test_resolve_mask_from_files_single_fallback(tmp_path):
    only = tmp_path / "any_name.tif"
    only.write_bytes(b"")
    assert resolve_mask_from_files("sample", [only]) == only


def test_resolve_mask_from_files_no_match(tmp_path):
    a = tmp_path / "a.tif"
    b = tmp_path / "b.tif"
    a.write_bytes(b"")
    b.write_bytes(b"")
    assert resolve_mask_from_files("sample", [a, b]) is None
    mask = np.array([[0, 1], [2, 0]], dtype=np.uint16)
    path = tmp_path / "a_mask_polygon.tif"
    save_mask_tif(path, mask)
    from PIL import Image

    loaded = np.array(Image.open(path))
    assert loaded.shape == mask.shape
    assert loaded[0, 1] == 1
