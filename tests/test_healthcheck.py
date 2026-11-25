"""
test_healthcheck.py – Unit tests for pre-flight healthcheck and sanity validator.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import unittest
from healthcheck import (
    check_python_version,
    check_directory_structure,
    check_module_imports,
    run_math_sanity_check,
    run_full_healthcheck,
)


class TestHealthcheck(unittest.TestCase):

    def test_python_version(self):
        self.assertTrue(check_python_version())

    def test_directory_structure(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        res = check_directory_structure(root)
        self.assertIn("src", res)
        self.assertIn("tests", res)
        self.assertTrue(all(res.values()))

    def test_module_imports(self):
        res = check_module_imports()
        for mod, status in res.items():
            self.assertIs(status, True, f"Failed importing {mod}: {status}")

    def test_math_sanity(self):
        self.assertTrue(run_math_sanity_check())

    def test_full_healthcheck(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        summary = run_full_healthcheck(root)
        self.assertEqual(summary["status"], "HEALTHY")
        self.assertTrue(summary["python_version_ok"])
        self.assertTrue(summary["directories_ok"])
        self.assertTrue(summary["imports_ok"])
        self.assertTrue(summary["math_sanity_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
