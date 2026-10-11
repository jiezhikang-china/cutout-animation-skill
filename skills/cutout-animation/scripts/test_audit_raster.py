"""Exercise invariant failures using generated fixtures, without project artwork."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from audit_raster import compare, main
import subprocess
import sys
import json


class PixelAudits(unittest.TestCase):
    def setUp(self):
        self.base = Image.new("RGBA", (7, 5), (201, 151, 121, 255))
        self.allowed = np.zeros((5, 7), bool)
        self.allowed[1:4, 1:6] = True
        self.fixed = np.zeros((5, 7), bool)
        self.fixed[2, 2] = True

    def check_variant(self, x, y, pixel):
        result = self.base.copy()
        result.putpixel((x, y), pixel)
        return compare("replacement", self.base, result,
                       self.allowed, self.fixed)

    def test_allowed_colour_replacement(self):
        metrics, failures = self.check_variant(4, 2, (10, 20, 30, 255))
        self.assertEqual(sum(metrics.values()), 0)
        self.assertFalse(failures.any())

    def test_outside_change_fails(self):
        metrics, failures = self.check_variant(0, 0, (10, 20, 30, 255))
        self.assertEqual(metrics["outside_changed_pixels"], 1)
        self.assertTrue(failures[0, 0])

    def test_protected_pixel_inside_allowed_fails(self):
        metrics, _ = self.check_variant(2, 2, (10, 20, 30, 255))
        self.assertEqual(metrics["protected_changed_pixels"], 1)

    def test_alpha_inside_allowed_fails(self):
        metrics, _ = self.check_variant(4, 2, (201, 151, 121, 127))
        self.assertEqual(metrics["alpha_changed_pixels"], 1)

    def test_zero_pose_with_original_semitransparency(self):
        base = self.base.copy()
        base.putpixel((3, 2), (80, 40, 20, 100))
        body = base.copy()
        arm = Image.new("RGBA", base.size)
        for x in (3, 4):
            for y in (1, 2, 3):
                arm.putpixel((x, y), base.getpixel((x, y)))
                body.putpixel((x, y), (0, 0, 0, 0))
        body.alpha_composite(arm)
        metrics, failures = compare("assembly", base, body)
        self.assertEqual(sum(metrics.values()), 0)
        self.assertFalse(failures.any())

    def test_double_arm_semitransparency_fails(self):
        base = Image.new("RGBA", (3, 3), (80, 40, 20, 100))
        double = base.copy()
        double.alpha_composite(base)
        metrics, _ = compare("assembly", base, double)
        self.assertEqual(metrics["alpha_changed_pixels"], 9)

    def test_transparent_rgb_is_ignored_only_in_assembly(self):
        a = Image.new("RGBA", (2, 2), (90, 70, 30, 0))
        b = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
        self.assertFalse(compare("assembly", a, b)[1].any())
        self.assertEqual(compare("exact", a, b)[0]["rgba_changed_pixels"], 4)

    def test_cli_unicode_failure_report_and_input_error(self):
        with tempfile.TemporaryDirectory(prefix="像素检查-") as directory:
            root = Path(directory)
            self.base.save(root / "原图.png")
            changed = self.base.copy()
            changed.putpixel((0, 0), (0, 0, 0, 255))
            changed.save(root / "差分.png")
            Image.fromarray(self.allowed.astype("uint8") * 255).save(root / "遮罩.png")
            cmd = [sys.executable, str(Path(__file__).with_name("audit_raster.py")),
                   "replacement", "--base", str(root / "原图.png"),
                   "--candidate", str(root / "差分.png"),
                   "--mask", str(root / "遮罩.png"),
                   "--report", str(root / "诊断/报告.json")]
            result = subprocess.run(cmd, capture_output=True)
            self.assertEqual(result.returncode, 2)
            report = json.loads((root / "诊断/报告.json").read_text(encoding="utf8"))
            self.assertFalse(report["passed"])
            with Image.open(report["failure_map"]) as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 0, 90, 255))
            Image.new("RGBA", (1, 1)).save(root / "差分.png")
            result = subprocess.run(cmd, capture_output=True)
            self.assertEqual(result.returncode, 1)
            report = json.loads((root / "诊断/报告.json").read_text(encoding="utf8"))
            self.assertIn("input_error", report)


if __name__ == "__main__":
    unittest.main()
