#!/usr/bin/env python3
# scripts/enrich_sample_entity_fields.py
"""
Widen thin sample entity tables so ERD/HTML diagrams show plausible column counts.

Touches ``src/maxitor/samples/**/entities/*.py``: for each ``*Entity`` class, counts
scalartype ``AnnAssign`` rows (anything without ``AssociationOne`` / ``AssociationMany``
/ ``Rel(``). When that count excluding ``id`` / ``lifecycle`` is below ``N``, inserts
typed ``Field(...)`` definitions before the first relation field or after the last
scalar field.
"""

from __future__ import annotations

import argparse
import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENT_ROOT = ROOT / "src" / "maxitor" / "samples"
DESIRED_SCALAR_EXTRAS = 6


@dataclass(frozen=True)
class _Stmt:
    name: str
    lineno: int
    end_lineno: int
    relationish: bool


def _relationish_ann(stmt: ast.AnnAssign, src_lines: list[str]) -> bool:
    """Heuristic matching interchange relation slots encoded as ``Annotated[..., Rel()]``."""
    if not isinstance(stmt.target, ast.Name):
        return True
    if stmt.annotation is None:
        return False
    start_idx = stmt.lineno - 1
    end_idx = (stmt.end_lineno or stmt.lineno) - 1
    block = "\n".join(src_lines[start_idx : end_idx + 1])
    return any(tok in block for tok in ("AssociationOne", "AssociationMany", "Rel("))


def _field_lines_for_domain(domain_key: str) -> list[str]:
    """Domain-flavoured English column templates (order stable)."""
    common_tail = (
        ("record_version", 'int = Field(description="Optimistic concurrency stamp", ge=0)'),
        ("correlation_nonce", 'str = Field(description="Opaque id echoed along adjoining workflows")'),
    )
    packs: dict[str, list[tuple[str, str]]] = {
        "analytics": [("ingress_batch_key", 'str = Field(description="Loader partition key echoed into lake prefixes")'), ("source_anchor_slug", 'str = Field(description="Upstream subsystem / connector anchor moniker")'), ("event_estimate", 'int = Field(description="Approximate attributable telemetry rows", ge=0)'), ("payload_byte_hint", 'int = Field(description="Compressed payload footprint hint bytes", ge=0)'), ("freshness_horizon_sec", 'int = Field(description="Skew allowance for unordered facts seconds", ge=0)'), ("privacy_tier_label", 'str = Field(description="Data-class label surfaced to rollup consumers")'), *list(common_tail)],
        "assurance_portfolio": [("scenario_ref", 'str = Field(description="Scenario / release train reference tag")'), ("expectation_grade", 'str = Field(description="Tolerance band moniker for auditors")'), ("evidence_locker_id", 'str = Field(description="Immutable evidence bundle locator")'), ("audit_locale", 'str = Field(description="Regulatory framing geography code")'), ("automation_vendor", 'str = Field(description="Runner / harness vendor label")'), ("flaky_budget_pct", 'float = Field(description="Accepted flake-rate envelope percent", ge=0, le=100)'), *list(common_tail)],
        "billing": [("legal_entity_ref", 'str = Field(description="Debtor / posting-company anchor")'), ("currency_iso", 'str = Field(description="Declared ISO-4217 money unit")'), ("posting_timezone", 'str = Field(description="Business-calendar timezone identifier")'), ("narrative_token", 'str = Field(description="Support / ops conversational lookup slug")'), ("reversibility_until_unix", 'int = Field(description="Cutoff epoch seconds for corrective moves", ge=0)'), ("source_journal_code", 'str = Field(description="ERP / PSP journal mnemonic")'), *list(common_tail)],
        "catalog": [("commercial_region_code", 'str = Field(description="Merchandising / pricing region discriminator")'), ("channel_partner_tag", 'str = Field(description="Acquisition partner or marketplace moniker")'), ("compliance_locale", 'str = Field(description="Regulatory storefront locale code")'), ("attribution_strategy", 'str = Field(description="Attribution-model key used for funnel credit")'), ("hash_stale_after_sec", 'int = Field(description="Seconds until cached facets must invalidate", ge=0)'), ("copy_variant_revision", 'int = Field(description="Narrative / SEO copy ordinal", ge=0)'), *list(common_tail)],
        "clinical_supply": [("sterility_claim_code", 'str = Field(description="Sterile-environment handling claim discriminator")'), ("lot_trace_handle", 'str = Field(description="Serialized trace corridor locator")'), ("temperature_ceiling_k", 'float = Field(description="Max allowed ambient storage kelvin snapshot")'), ("recall_watch_state", 'str = Field(description="Recall / embargo disposition label")'), ("quarantine_fence_id", 'str = Field(description="Facility quarantine corridor moniker")'), ("regulatory_territory", 'str = Field(description="Governing geography for distribution assertions")'), *list(common_tail)],
        "identity": [("subject_handle", 'str = Field(description="Pseudonymous subject moniker for federation")'), ("risk_band", 'str = Field(description="Assurance tier surfaced to policy engines")'), ("last_seen_ip_hash", 'str = Field(description="Salted client-network fingerprint heuristic")'), ("mfa_saturation_pct", 'float = Field(description="MFA-factor coverage heuristic percent", ge=0, le=100)'), ("recovery_budget_left", 'int = Field(description="Remaining recovery-token attempts envelope", ge=0)'), ("linkage_audit_seq", 'int = Field(description="Monotonic merge audit ticker", ge=0)'), *list(common_tail)],
        "inventory": [("facility_tz", 'str = Field(description="Warehouse operational timezone identifier")'), ("capacity_cu_m", 'float = Field(description="Usable volumetric envelope cubic metres")'), ("hazmat_classification", 'str = Field(description="Material-handling tier label")'), ("cycle_count_due_unix", 'int = Field(description="Next physical audit milestone epoch seconds", ge=0)'), ("dock_door_anchor", 'str = Field(description="Primary receiving / staging door label")'), ("velocity_bucket", 'str = Field(description="ABC / throughput velocity class")'), *list(common_tail)],
        "messaging": [("traceparent_seed", 'str = Field(description="Propagation root echoed to downstream carriers")'), ("dedupe_partition", 'str = Field(description="Logical inbox partition for idempotent consumers")'), ("backpressure_budget", 'int = Field(description="Outstanding backlog units tolerated per lane", ge=0)'), ("deadline_budget_ms", 'int = Field(description="End-to-end SLA budget millis", ge=0)'), ("content_class", 'str = Field(description="Envelope / codec family moniker")'), ("retry_policy_slug", 'str = Field(description="Backoff / retry escalation preset identifier")'), *list(common_tail)],
        "store": [("storefront_channel", 'str = Field(description="POS / kiosk / ecommerce channel moniker")'), ("compliance_rating", 'str = Field(description="Fraud / AML posture snapshot")'), ("fulfillment_priority", 'int = Field(description="Relative orchestration priority ordinal", ge=0)'), ("tax_jurisdiction_stub", 'str = Field(description="Derived routing hint for taxation engines")'), ("shipment_carrier_hint", 'str = Field(description="Preferred carrier mnemonic for planners")'), ("lineage_batch_token", 'str = Field(description="Correlation handle shared across mesh bridges")'), *list(common_tail)],
        "support": [("ticket_human_ref", 'str = Field(description="Customer-visible ticket mnemonic")'), ("severity_score", 'int = Field(description="Normalized severity ordinal", ge=0)'), ("first_response_deadline_unix", 'int = Field(description="SLA first-touch deadline epoch seconds", ge=0)'), ("routing_queue", 'str = Field(description="Primary queue owning responder pool")'), ("language_locale", 'str = Field(description="Preferred conversational language tag")'), ("deflection_attempts", 'int = Field(description="Self-serve resolutions before escalation", ge=0)'), *list(common_tail)],
    }
    fallback = packs["store"]
    return [f"    {n}: {rhs}" for n, rhs in packs.get(domain_key, fallback)]


def _domain_key_from_path(path: Path) -> str:
    return path.relative_to(ENT_ROOT).parts[0]


def _gather_class_stmt_meta(cls: ast.ClassDef, lines: list[str]) -> list[_Stmt]:
    out: list[_Stmt] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        rel = _relationish_ann(stmt, lines)
        end_ln = getattr(stmt, "end_lineno", None) or stmt.lineno
        out.append(_Stmt(stmt.target.id, stmt.lineno, end_ln, rel))
    return out


def process_file(path: Path, *, dry_run: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False

    lines = text.splitlines()
    domain_key = _domain_key_from_path(path)
    pack_templates = _field_lines_for_domain(domain_key)

    # (insert_idx0, newline block)
    insertions: list[tuple[int, list[str]]] = []

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Entity"):
            continue
        meta = _gather_class_stmt_meta(node, lines)
        if not meta:
            continue
        extras = len([m for m in meta if (not m.relationish and m.name not in {"id", "lifecycle"})])
        if extras >= DESIRED_SCALAR_EXTRAS:
            continue

        need = DESIRED_SCALAR_EXTRAS - extras
        used = {m.name for m in meta}
        additions: list[str] = []
        for template in pack_templates:
            if need <= 0:
                break
            m_line = re.match(r"^\s+(\w+):", template)
            if not m_line:
                continue
            cand = m_line.group(1)
            if cand in used:
                continue
            additions.append(template)
            used.add(cand)
            need -= 1
        if not additions:
            continue

        first_rel = next((m for m in meta if m.relationish), None)
        last_scalar = meta[-1]
        if first_rel is not None:
            insert_before_idx0 = first_rel.lineno - 1
            block = additions
            if insert_before_idx0 > 0 and lines[insert_before_idx0 - 1].strip() and block:
                block = ["", *block]
            insertions.append((insert_before_idx0, block))
        else:
            after_idx0 = last_scalar.end_lineno
            block = additions
            if after_idx0 < len(lines) and lines[after_idx0 - 1].strip():
                block = ["", *block]
            insertions.append((after_idx0, block))

    if not insertions:
        return False

    insertions.sort(key=lambda t: -t[0])
    for idx0, blk in insertions:
        lines[idx0:idx0] = blk

    new_text = "\n".join(lines)
    ends_nl = text.endswith("\n")
    if ends_nl:
        new_text += "\n"
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Do not modify files.")
    ap.add_argument("paths", nargs="*", type=Path, help="Explicit entity paths (defaults to samples).")
    args = ap.parse_args()

    todo: Sequence[Path] = sorted(ENT_ROOT.glob("*/entities/*.py")) if not args.paths else args.paths
    n = 0
    for p in todo:
        rp = Path(p).expanduser().resolve(strict=False)
        if rp.name.startswith("__"):
            continue
        if process_file(rp, dry_run=args.dry_run):
            print(f"{rp.relative_to(ROOT)}{' (dry-run)' if args.dry_run else ''}")
            n += 1
    print(f"files touched={n}")


if __name__ == "__main__":
    main()
