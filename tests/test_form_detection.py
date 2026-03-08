import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.router.query_router import detect_sec_form


class DetectSecFormTests(unittest.TestCase):
    def test_no_explicit_form_returns_none(self) -> None:
        self.assertIsNone(detect_sec_form("What legal risks did Apple mention?"))

    def test_explicit_10k_detection(self) -> None:
        self.assertEqual(detect_sec_form("What did Apple disclose in its 10-K?"), "10-K")

    def test_proxy_statement_maps_to_def14a(self) -> None:
        self.assertEqual(
            detect_sec_form("What governance topics appear in Apple's proxy statement?"),
            "DEF 14A",
        )

    def test_annual_report_maps_to_10k(self) -> None:
        self.assertEqual(
            detect_sec_form("What risks are mentioned in Apple's annual report?"),
            "10-K",
        )

    def test_quarterly_report_maps_to_10q(self) -> None:
        self.assertEqual(
            detect_sec_form("What did Apple report in its quarterly report?"),
            "10-Q",
        )


if __name__ == "__main__":
    unittest.main()
