import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.router.query_router import (
    build_multi_company_subqueries,
    detect_companies,
    detect_primary_company,
)


class QueryRoutingTests(unittest.TestCase):
    def test_detect_companies_returns_all_matches_in_order(self) -> None:
        self.assertEqual(
            detect_companies("Compare the legal risks mentioned by Apple and NVIDIA in their 10-K filings."),
            ["Apple Inc.", "NVIDIA CORP"],
        )

    def test_detect_primary_company_returns_first_match(self) -> None:
        self.assertEqual(
            detect_primary_company("Compare Apple with Alphabet in their 10-K filings."),
            "Apple Inc.",
        )

    def test_build_multi_company_subqueries_preserves_form_constraint(self) -> None:
        subqueries = build_multi_company_subqueries(
            "Compare the legal risks mentioned by Apple and NVIDIA in their 10-K filings.",
            ["Apple Inc.", "NVIDIA CORP"],
            form_filter="10-K",
        )

        self.assertEqual(len(subqueries), 2)
        self.assertEqual(
            subqueries[0]["subquery"],
            "What legal risks did Apple mention in its 10-K filings?",
        )
        self.assertEqual(
            subqueries[1]["subquery"],
            "What legal risks did NVIDIA mention in its 10-K filings?",
        )

    def test_build_multi_company_subqueries_without_form_keeps_broad_scope(self) -> None:
        subqueries = build_multi_company_subqueries(
            "Compare the cybersecurity risks described by Apple and Microsoft.",
            ["Apple Inc.", "MICROSOFT CORP"],
            form_filter=None,
        )

        self.assertEqual(
            subqueries[0]["subquery"],
            "What cybersecurity risks did Apple mention?",
        )
        self.assertEqual(
            subqueries[1]["subquery"],
            "What cybersecurity risks did Microsoft mention?",
        )


if __name__ == "__main__":
    unittest.main()
