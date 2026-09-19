"""
Save, load, and apply manual masks.

Naming conventions:
  {stem}_segmentation.tif  — imported intensity/segmentation mask
  {stem}_mask_polygon.tif  — manual / auto mask from Instruments
  {stem}_mask_ROI.tif      — phasor ellipse ROI
  {stem} segmentation.tif  — legacy name with a space (still recognised on import)

See README.md (Masking) for import/export workflow.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from utils.shared_data import SharedData

MASK_KIND_POLYGON = "polygon"
MASK_KIND_ROI = "ROI"


def _normalize_mask_kind(kind: str) -> str:
    """Map UI kind strings to canonical mask kind."""
    key = (kind or "").strip()
    if key.upper() == MASK_KIND_ROI:
        return MASK_KIND_ROI
    if key.lower() == MASK_KIND_POLYGON:
        return MASK_KIND_POLYGON
    return key


def file_stem(filename: str) -> str:
    """Table/dict key to base name without extension."""
    return Path(filename).stem


def default_mask_filename(stem: str, kind: str) -> str:
    """Suggested save-as name for a mask (user may change in the save dialog)."""
    kind = _normalize_mask_kind(kind)
    suffix = "_mask_ROI.tif" if kind == MASK_KIND_ROI else "_mask_polygon.tif"
    return f"{stem}{suffix}"


def ensure_tif_path(path: str | Path) -> Path:
    """Ensure saved mask paths use a .tif extension."""
    path = Path(path)
    if path.suffix.lower() not in (".tif", ".tiff"):
        path = path.with_suffix(".tif")
    return path


def mask_path_for(stem: str, kind: str, folder: str | Path) -> Path:
    """Build output path: {stem}_mask_ROI.tif or {stem}_mask_polygon.tif."""
    return Path(folder) / default_mask_filename(stem, kind)


def mask_basename_candidates(stem: str) -> list[str]:
    """Recognised mask filenames for a sample stem (new names first, then legacy)."""
    return [
        f"{stem}_segmentation.tif",
        f"{stem}_mask_ROI.tif",
        f"{stem}_mask_polygon.tif",
        f"{stem} segmentation.tif",  # legacy; space in name
    ]


def resolve_mask_path(masks_dir: str | Path, file_name: str) -> Path | None:
    """Find first existing mask file for a sample in a folder."""
    stem = file_stem(file_name)
    folder = Path(masks_dir)
    for name in mask_basename_candidates(stem):
        path = folder / name
        if path.is_file():
            return path
    return None


def resolve_mask_from_files(file_name: str, mask_files: list[Path | str]) -> Path | None:
    """
    Match a raw sample to one of several user-selected mask TIFF paths.
    Tries standard names first, then stem prefix; single-file import uses lone TIFF.
    """
    stem = file_stem(file_name)
    paths = [Path(p) for p in mask_files if Path(p).is_file()]
    if not paths:
        return None

    by_name = {p.name: p for p in paths}
    for name in mask_basename_candidates(stem):
        if name in by_name:
            return by_name[name]

    stem_lower = stem.lower()
    for path in paths:
        file_stem_lower = path.stem.lower()
        if file_stem_lower == stem_lower:
            return path
        if file_stem_lower.startswith(stem_lower + "_") or file_stem_lower.startswith(stem_lower + " "):
            return path

    if len(paths) == 1:
        return paths[0]
    return None


def load_mask_array(path: str | Path) -> np.ndarray:
    return np.array(Image.open(path), dtype=np.float32)


def save_mask_tif(path: str | Path, mask: np.ndarray) -> None:
    arr = np.asarray(mask, dtype=np.uint16)
    Image.fromarray(arr).save(path)


def _align_mask_shape(mask_arr: np.ndarray, spatial: tuple) -> np.ndarray:
    """Resize mask to match sample (time, y, x) spatial dims if needed."""
    mask_arr = np.asarray(mask_arr)
    if mask_arr.shape == spatial:
        return mask_arr.astype(np.float32)
    from PIL import Image

    img = Image.fromarray(mask_arr.astype(np.uint16))
    img = img.resize((spatial[1], spatial[0]), Image.NEAREST)
    return np.array(img, dtype=np.float32)


def apply_mask_to_sample(main_window, filename: str, mask_arr: np.ndarray, preserve_mask_tool=False) -> None:
    """
    Store mask on raw_data_dict, build masked_data for analysis, refresh plots.
    preserve_mask_tool: keep polygon/brush/etc. active across plot redraws.
    """
    shared = SharedData()
    if filename not in shared.raw_data_dict:
        return

    data = shared.raw_data_dict[filename]["data"]
    spatial = data.shape[1:]
    mask_arr = _align_mask_shape(mask_arr, spatial)

    masked_data = np.where(mask_arr == 0, np.zeros_like(data), data)
    shared.raw_data_dict[filename]["mask_arr"] = mask_arr
    shared.raw_data_dict[filename]["masked_data"] = masked_data

    if filename in shared.results_dict:
        shared.results_dict[filename]["mask"] = mask_arr

    editor = main_window.mask_editor
    active_tool = editor._tool if preserve_mask_tool else None

    main_window.plotImages.plot_img(preserve_mask_tool=preserve_mask_tool)
    if shared.results_dict and filename in shared.results_dict:
        main_window.plotImages.plot_tau_map(preserve_mask_tool=preserve_mask_tool)
        main_window.canvas_tau.draw()
        if not preserve_mask_tool:
            main_window.phasor_componets.plot_phasor_coordinates()

    if active_tool:
        editor.activate_tool(active_tool)
