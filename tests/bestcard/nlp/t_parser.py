from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from bestcard.nlp.parser import ALLOWED_CATEGORIES, ScenarioParseError, parse_scenario


@dataclass
class ParserCase:
    name: str
    message: str
    amount: float | None = None
    category: str | None = None
    is_foreign: bool | None = None
    currency: str = "USD"
    include_annual_fee_proration: bool = False
    monthly_spend_estimate: float | None = None
    expected_category: str | None = None
    expected_is_foreign: bool | None = None


def _hard_checks(case: ParserCase, scenario) -> list[str]:
    issues: list[str] = []
    if scenario.amount <= 0:
        issues.append(f"amount must be > 0, got {scenario.amount}")
    if scenario.category not in ALLOWED_CATEGORIES:
        issues.append(f"category must be in {ALLOWED_CATEGORIES}, got {scenario.category}")
    if not isinstance(scenario.is_foreign, bool):
        issues.append(f"is_foreign must be bool, got {type(scenario.is_foreign).__name__}")
    if not scenario.currency or len(scenario.currency) < 3:
        issues.append(f"currency looks invalid, got {scenario.currency!r}")
    return issues


def _soft_checks(case: ParserCase, scenario) -> list[str]:
    warnings: list[str] = []
    if case.expected_category and scenario.category != case.expected_category:
        warnings.append(
            f"expected category={case.expected_category}, got {scenario.category}"
        )
    if case.expected_is_foreign is not None and scenario.is_foreign != case.expected_is_foreign:
        warnings.append(
            f"expected is_foreign={case.expected_is_foreign}, got {scenario.is_foreign}"
        )
    return warnings


def t_parser_generates_good_spend_scenario() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    cases = [
        ParserCase(
            name="zh_grocery",
            message="今晚去超市买菜花了230元，帮我选卡",
            expected_category="grocery",
            expected_is_foreign=False,
        ),
        ParserCase(
            name="en_travel_foreign",
            message="I will pay 450 EUR for an overseas hotel booking tomorrow.",
            expected_category="travel",
            expected_is_foreign=True,
            currency="EUR",
        ),
        ParserCase(
            name="override_fields",
            message="Dinner with friends tonight",
            amount=88,
            category="dining",
            is_foreign=False,
            expected_category="dining",
            expected_is_foreign=False,
        ),
    ]

    hard_failures = 0
    warning_count = 0

    for case in cases:
        print(f"--- Case: {case.name} ---")
        try:
            scenario = parse_scenario(
                message=case.message,
                amount=case.amount,
                category=case.category,
                is_foreign=case.is_foreign,
                currency=case.currency,
                include_annual_fee_proration=case.include_annual_fee_proration,
                monthly_spend_estimate=case.monthly_spend_estimate,
            )
        except ScenarioParseError as exc:
            hard_failures += 1
            print(f"FAIL: parser error: {exc}")
            continue
        except Exception as exc:
            hard_failures += 1
            print(f"FAIL: unexpected error: {exc}")
            continue

        print(f"Input: {case.message}")
        print(f"Scenario: {scenario.model_dump()}")

        errors = _hard_checks(case, scenario)
        warns = _soft_checks(case, scenario)

        if errors:
            hard_failures += 1
            print("FAIL:")
            for err in errors:
                print(f"- {err}")
        else:
            print("PASS: hard checks passed")

        if warns:
            warning_count += len(warns)
            print("WARN:")
            for warn in warns:
                print(f"- {warn}")
        print()

    print("=== Summary ===")
    print(f"Hard failures: {hard_failures}")
    print(f"Warnings: {warning_count}")

    if hard_failures > 0:
        raise RuntimeError("Parser quality check failed.")


if __name__ == "__main__":
    t_parser_generates_good_spend_scenario()
