#!/usr/bin/env python3
"""Deterministic RGBA audits. No segmentation, rendering or artistic judgement."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgba(path, size=None):
    with Image.open(path) as image:
        image = image.convert("RGBA")
        if size is not None and image.size != size:
            raise ValueError("Image dimensions differ: " + str(path))
        return image.copy()


def mask(path, size):
    with Image.open(path) as image:
        if image.size != size:
            raise ValueError("Mask dimensions differ: " + str(path))
        if image.mode not in ("1", "L"):
            raise ValueError("Mask must be grayscale (1 or L), not an RGBA cutout")
        return np.asarray(image.convert("L")) > 0


def compare(mode, base, candidate, allowed=None, protected=None):
    a, b = np.asarray(base), np.asarray(candidate)
    if a.shape != b.shape:
        raise ValueError("Image dimensions differ")
    changed = np.any(a != b, axis=2)
    alpha = a[:, :, 3] != b[:, :, 3]
    if mode == "replacement":
        outside = changed & ~allowed
        fixed = changed & protected
        metrics = {
            "outside_changed_pixels": int(outside.sum()),
            "protected_changed_pixels": int(fixed.sum()),
            "alpha_changed_pixels": int(alpha.sum()),
        }
        failed = outside | fixed | alpha
    elif mode == "assembly":
        visible = (a[:, :, 3] > 0) | (b[:, :, 3] > 0)
        rgb = np.any(a[:, :, :3] != b[:, :, :3], axis=2) & visible
        metrics = {"visible_rgb_changed_pixels": int(rgb.sum()),
                   "alpha_changed_pixels": int(alpha.sum())}
        failed = rgb | alpha
    else:
        metrics = {"rgba_changed_pixels": int(changed.sum())}
        failed = changed
    return metrics, failed


def run(args):
    base = rgba(args.base)
    inputs = {"base": {"path": str(args.base), "sha256": sha(args.base)}}
    if args.mode == "assembly":
        candidate = Image.new("RGBA", base.size)
        inputs["layers"] = []
        for path in args.layers:
            candidate.alpha_composite(rgba(path, base.size))
            inputs["layers"].append({"path": str(path), "sha256": sha(path)})
        allowed = protected = None
    else:
        candidate = rgba(args.candidate, base.size)
        inputs["candidate"] = {"path": str(args.candidate),
                               "sha256": sha(args.candidate)}
        allowed = protected = None
        if args.mode == "replacement":
            allowed = mask(args.mask, base.size)
            protected = (mask(args.protected, base.size) if args.protected
                         else np.zeros((base.height, base.width), dtype=bool))
            for key in ("mask", "protected"):
                path = getattr(args, key)
                if path:
                    inputs[key] = {"path": str(path), "sha256": sha(path)}
    metrics, failed = compare(args.mode, base, candidate, allowed, protected)
    report = {"mode": args.mode, "size": list(base.size), "inputs": inputs,
              "metrics": metrics, "passed": not bool(failed.any()),
              "scope": "pixel-invariants-only"}
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if failed.any():
        diff_path = report_path.with_name(report_path.stem + "-failures.png")
        diff = np.zeros((base.height, base.width, 4), dtype=np.uint8)
        diff[failed] = [255, 0, 90, 255]
        Image.fromarray(diff).save(diff_path)
        with Image.open(diff_path) as check:
            check.load()
        report["failure_map"] = str(diff_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "metrics": metrics,
                      "report": str(report_path)}, ensure_ascii=False))
    return 0 if report["passed"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for name in ("replacement", "assembly", "exact"):
        sub = modes.add_parser(name)
        sub.add_argument("--base", required=True, type=Path)
        sub.add_argument("--report", required=True, type=Path)
        if name == "assembly":
            sub.add_argument("--layers", required=True, nargs="+", type=Path)
        else:
            sub.add_argument("--candidate", required=True, type=Path)
        if name == "replacement":
            sub.add_argument("--mask", required=True, type=Path)
            sub.add_argument("--protected", type=Path)
    args = parser.parse_args()
    try:
        return run(args)
    except (OSError, ValueError) as error:
        report_path = args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(
            {"passed": False, "input_error": str(error)}, ensure_ascii=False,
            indent=2), encoding="utf-8")
        print("Input error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
