from __future__ import annotations

import re

from app.data.question_bank import CURATED_QUESTION_BANK
from app.services.demo_service import store_demo_response
from app.services.question_bank_service import build_question_bank


def extract_companies(question: str) -> list[str]:
    matches = re.findall(r"\b(Apple|NVIDIA|Alphabet)\b", str(question or ""))
    ordered: list[str] = []
    for item in matches:
        if item not in ordered:
            ordered.append(item)
    return ordered


def infer_topic(question: str) -> str:
    lowered = str(question or "").lower()
    topic_patterns = [
        ("legal proceedings", "legal proceedings and litigation exposure"),
        ("litigation", "litigation and dispute exposure"),
        ("regulatory", "regulatory compliance and enforcement exposure"),
        ("cybersecurity", "cybersecurity, privacy and data protection risk"),
        ("supply chain", "supplier concentration and supply-chain execution risk"),
        ("intellectual property", "intellectual property and infringement risk"),
        ("global operations", "global operations, trade and geopolitical exposure"),
        ("product defects", "product quality, warranty and defect-related risk"),
        ("economic", "macroeconomic and demand-side risk"),
        ("future profitability", "factors that could pressure future profitability"),
        ("liquidity and capital resources", "liquidity and capital resources"),
        ("revenue trends", "revenue drivers and trend commentary"),
        ("governance", "governance risk and oversight topics"),
        ("executive compensation", "executive compensation topics"),
        ("board governance", "board governance topics"),
        ("proxy statement", "proxy statement governance topics"),
        ("quarterly report", "quarterly-report regulatory topics"),
        ("risks", "key risks discussed in the filings"),
    ]

    for pattern, topic in topic_patterns:
        if pattern in lowered:
            return topic

    return "material risks and disclosures in the filings"


def build_demo_answer(question: str) -> str:
    companies = extract_companies(question)
    topic = infer_topic(question)
    lowered = str(question or "").lower()

    if "compare" in lowered and companies:
        company_text = ", ".join(companies[:-1]) + f" and {companies[-1]}" if len(companies) > 1 else companies[0]
        return (
            f"A comparison of {company_text} indicates that the filings describe overlapping exposure in {topic}, "
            "but with different emphasis by issuer. The common themes are legal and regulatory uncertainty, "
            "operational execution risk, and market conditions. The main differences are the way each company "
            "frames exposure around its product mix, supply chain, intellectual property posture and global footprint."
        )

    company_text = companies[0] if companies else "The company"
    return (
        f"{company_text}'s filings describe {topic} as an area that could materially affect operations, reputation "
        "and financial results. The disclosures point to a combination of compliance obligations, execution risk, "
        "external market pressure and the possibility that adverse developments could increase costs or reduce "
        "future performance."
    )


def main() -> None:
    seeded = 0
    for question in build_question_bank() or CURATED_QUESTION_BANK:
        store_demo_response(question, build_demo_answer(question))
        seeded += 1

    print(f"Seeded demo cache entries: {seeded}")


if __name__ == "__main__":
    main()
