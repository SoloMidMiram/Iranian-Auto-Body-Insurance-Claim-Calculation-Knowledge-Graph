"""Run the curated body-calculation mutation gate and verify its report."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "MUTATION_REPORT.md"


@dataclass(frozen=True)
class Mutation:
    mutation_id: str
    path: str
    original: str
    replacement: str
    risk: str


MUTATIONS = (
    Mutation("M01", "src/iran_auto_claim/plans.py", 'return value * operands["ratio"]', 'return value + operands["ratio"]', "ratio changes from multiplication to addition"),
    Mutation("M02", "src/iran_auto_claim/plans.py", 'return value - operands["franchise"]', 'return value + operands["franchise"]', "franchise is added instead of deducted"),
    Mutation("M03", "src/iran_auto_claim/plans.py", 'return value + operands["rescue"]', 'return value - operands["rescue"]', "rescue is deducted instead of added"),
    Mutation("M04", "src/iran_auto_claim/plans.py", 'return value - operands["salvage"]', 'return value + operands["salvage"]', "salvage is added instead of deducted"),
    Mutation("M05", "src/iran_auto_claim/plans.py", 'return min(value, operands["insured"])', 'return max(value, operands["insured"])', "insured-sum cap becomes a floor"),
    Mutation("M06", "src/iran_auto_claim/plans.py", "return max(Decimal(0), value)", "return min(Decimal(0), value)", "non-negative floor is inverted"),
    Mutation("M07", "src/iran_auto_claim/plans.py", "duplicates or unknown or missing or unexpected or len(normalized) != len(expected_ids)", "duplicates or unknown or unexpected", "missing active operator is accepted"),
    Mutation("M08", "src/iran_auto_claim/operators.py", "return min(actual_cost, RESCUE_CAP_RATIO * cap_base)", "return max(actual_cost, RESCUE_CAP_RATIO * cap_base)", "rescue cap becomes a floor"),
    Mutation("M09", "src/iran_auto_claim/operators.py", "return combined > threshold, combined, threshold", "return combined >= threshold, combined, threshold", "strict total-loss boundary becomes inclusive"),
    Mutation("M10", "src/iran_auto_claim/operators.py", "if insured_sum >= market_value:\n        return Decimal(1)", "if insured_sum >= market_value:\n        return Decimal(0)", "fully insured claim receives a zero ratio"),
    Mutation(
        "M11",
        "src/iran_auto_claim/engine.py",
        "def _enforce_guard_plan(res: CalcResult) -> None:\n    missing = [\n        guard_id for guard_id in res.required_guards if guard_id not in res.guards_executed\n    ]\n    if not missing:\n        return",
        "def _enforce_guard_plan(res: CalcResult) -> None:\n    missing = [\n        guard_id for guard_id in res.required_guards if guard_id not in res.guards_executed\n    ]\n    if missing:\n        return",
        "a bypassed required guard is accepted",
    ),
    Mutation("M12", "src/iran_auto_claim/admission.py", "if _snapshot_hash(grant.claim_snapshot) != grant.claim_hash:", "if False:", "the immutable claim snapshot no longer has to match its issued hash"),
    Mutation("M13", "src/iran_auto_claim/admission.py", "if self.decision not in AUTHORIZED_DECISIONS:", "if False:", "a REFUSE or INSUFFICIENT_INFORMATION decision reaches the calculator"),
    Mutation("M14", "src/iran_auto_claim/engine.py", "if not case.risk_intensified:\n        return", "if case.risk_intensified:\n        return", "risk intensification is settled at full amount instead of blocked on U15"),
    Mutation(
        "M15",
        "src/iran_auto_claim/admission.py",
        """if not (\n            (\n                grant.issuance_seal is _REVIEW_ISSUANCE_SEAL\n                and self.issuer == ISSUER_REVIEW\n            )\n            or (\n                grant.issuance_seal is _INTERNAL_TEST_ISSUANCE_SEAL\n                and self.issuer == ISSUER_INTERNAL_TEST\n            )\n        ) or not (\n            grant.decision == self.decision\n            and grant.issuer == self.issuer\n            and grant.issued_at == self.issued_at\n        ):""",
        "if False:",
        "an internal or metadata-mismatched capability can masquerade as review-issued",
    ),
    Mutation(
        "M16",
        "src/iran_auto_claim/admission.py",
        "_grant: _AuthorizationGrant | None = field(default=None, init=False, repr=False, compare=False)",
        "_grant: _AuthorizationGrant | None = field(default=None, init=True, repr=False, compare=False)",
        "dataclasses.replace can transplant a modified private grant onto another claim",
    ),
    Mutation(
        "M17",
        "src/iran_auto_claim/engine.py",
        "insurer_payable = min(actual, corresponding, limit)",
        "insurer_payable = min(corresponding, limit)",
        "Article 8 explicit zero is replaced by the corresponding-damage cap",
    ),
    Mutation(
        "M18",
        "src/iran_auto_claim/engine.py",
        "return bool(checks) and all(checks)",
        "return bool(checks) and any(checks)",
        "one exclusion clause can replace the required causal conjunction",
    ),
    Mutation(
        "M19",
        "src/iran_auto_claim/operators.py",
        "effective_depreciation = capped - after_depreciation",
        "effective_depreciation = scheduled_depreciation",
        "depreciate-then-cap deducts scheduled depreciation a second time",
    ),
    Mutation(
        "M20",
        "src/iran_auto_claim/engine.py",
        "selected_base = bases.get(str(calculation_base).upper()) if calculation_base else None",
        "selected_base = next(iter(bases.values())) if calculation_base else None",
        "percentage franchise ignores its named calculation base",
    ),
    Mutation(
        "M21",
        "src/iran_auto_claim/engine.py",
        "missing = [item for item in authorized if item not in res.blocking_uncertainties]\n    if not missing:\n        return",
        "missing = [item for item in authorized if item not in res.blocking_uncertainties]\n    if missing:\n        return",
        "a review-live uncertainty disappears from the deterministic result",
    ),
    Mutation(
        "M22",
        "src/iran_auto_claim/engine.py",
        '"AFTER_SALVAGE": after_salvage,\n            "SETTLEMENT_BASE": base,\n            "GROSS_ELIGIBLE": base,',
        '"AFTER_SALVAGE": after_salvage,\n            "SETTLEMENT_BASE": after_salvage,\n            "GROSS_ELIGIBLE": base,',
        "total-loss settlement base is silently aliased to the post-salvage base",
    ),
    Mutation(
        "M23",
        "src/iran_auto_claim/dates.py",
        "maximum = 30 if is_leap else 29",
        "maximum = 30",
        "a non-leap Shamsi year accepts Esfand 30",
    ),
    Mutation(
        "M24",
        "src/iran_auto_claim/engine.py",
        "_validate_theft_clock_start_event(case, clock)\n        derived_days = _dated_theft_clock_days(clock)",
        "derived_days = _dated_theft_clock_days(clock)",
        "the theft clock can use a date that disagrees with its selected event",
    ),
    Mutation(
        "M25",
        "src/iran_auto_claim/operators.py",
        "if not requires_replacement:\n        rate = Decimal(0)",
        "if False:\n        rate = Decimal(0)",
        "repair-only work receives replacement-part depreciation",
    ),
    Mutation(
        "M26",
        "src/iran_auto_claim/review.py",
        'damage["rescue_for_total_loss_test_irr"] = irr(rescue_actual)',
        'damage["rescue_for_total_loss_test_irr"] = 0',
        "Review drops evidenced rescue from the total-loss classification numerator",
    ),
    Mutation(
        "M27",
        "src/iran_auto_claim/engine.py",
        'and rescue_source == "UNRESOLVED_MISSING_RESCUE"',
        "and False",
        "omitted material rescue is treated as zero and allowed to authorize payment",
    ),
    Mutation(
        "M28",
        "src/iran_auto_claim/engine.py",
        "and override is not None\n        and not unresolved_rescue_gate",
        "and override is not None\n        and True",
        "a classification override bypasses the unresolved-rescue payment gate",
    ),
    Mutation(
        "M29",
        "src/iran_auto_claim/engine.py",
        "or (override is not None and declared in RESCUE_THRESHOLD_BRANCHES)",
        "or False",
        "an override-selected threshold branch skips the missing-rescue evidence gate",
    ),
    Mutation(
        "M31",
        "src/iran_auto_claim/engine.py",
        "if not case.title_transferred:\n            raise guards.GuardViolation(",
        "if False:\n            raise guards.GuardViolation(",
        "an incomplete title transfer can use the insurer-title no-salvage route",
    ),
)

THRESHOLD = 90.0


def _run_probe(root: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "mutation_probe.py")],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _copy_repository(target: Path) -> None:
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(
            ".git",
            ".qwen",
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            "COMMIT_STAGING_DRAFT.txt",
            ".venv",
        ),
    )


def _apply_mutation(root: Path, mutation: Mutation) -> None:
    target = root / mutation.path
    source = target.read_text(encoding="utf-8")
    count = source.count(mutation.original)
    if count != 1:
        raise RuntimeError(
            f"{mutation.mutation_id}: expected one mutation target in {mutation.path}, found {count}"
        )
    target.write_text(source.replace(mutation.original, mutation.replacement), encoding="utf-8")


def _render(results: list[tuple[Mutation, bool]]) -> str:
    killed = sum(1 for _, was_killed in results if was_killed)
    total = len(results)
    score = 100.0 * killed / total
    rows = [
        "# Body Calculation Mutation Report",
        "",
        "This is a reproducible, curated high-risk mutation set for the deterministic",
        "body calculation boundary. It is not a claim of exhaustive mutation coverage.",
        "",
        (
            "- Target modules: `plans.py`, `operators.py`, the guard-plan gate in "
            "`engine.py`, Review operand construction in `review.py`, canonical "
            "calendar validation in `dates.py`, and the authorization boundary "
            "in `admission.py`"
        ),
        f"- Required score: **{THRESHOLD:.0f}%**",
        f"- Result: **{killed}/{total} killed ({score:.1f}%)**",
        "- Command: `python scripts/run_mutation_gate.py --check-report`",
        "",
        "| Mutant | Result | Safety property |",
        "|---|---|---|",
    ]
    rows.extend(
        f"| {mutation.mutation_id} | {'KILLED' if was_killed else 'SURVIVED'} | {mutation.risk} |"
        for mutation, was_killed in results
    )
    rows.extend(
        [
            "",
            "A surviving mutant or a score below the threshold fails the gate. The checked-in",
            "report must exactly match a fresh run.",
            "",
        ]
    )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--check-report", action="store_true")
    args = parser.parse_args(argv)

    baseline = _run_probe(ROOT)
    if baseline.returncode != 0:
        print("baseline mutation probe failed", file=sys.stderr)
        print(baseline.stdout, file=sys.stderr)
        print(baseline.stderr, file=sys.stderr)
        return 2

    results: list[tuple[Mutation, bool]] = []
    with tempfile.TemporaryDirectory(prefix="body-model-mutations-") as temporary:
        temporary_root = Path(temporary)
        for mutation in MUTATIONS:
            mutant_root = temporary_root / mutation.mutation_id
            _copy_repository(mutant_root)
            _apply_mutation(mutant_root, mutation)
            results.append((mutation, _run_probe(mutant_root).returncode != 0))

    rendered = _render(results)
    killed = sum(1 for _, was_killed in results if was_killed)
    score = 100.0 * killed / len(results)
    if args.write_report:
        REPORT.write_text(rendered, encoding="utf-8")
        print(f"wrote {REPORT.relative_to(ROOT)}")
    elif args.check_report:
        if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != rendered:
            print("mutation report is stale; rerun with --write-report", file=sys.stderr)
            return 1
        print("mutation report is current")
    else:
        print(rendered, end="")
    if score < THRESHOLD:
        print(f"mutation score {score:.1f}% is below {THRESHOLD:.1f}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
