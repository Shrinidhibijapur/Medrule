import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.models.criteria import (
    CriterionRule,
    CriterionType,
    LogicOperator,
    ComparisonOperator,
    VerificationStatus,
    ReviewerSignoff,
    PolicyRuleset,
    VerificationGateRequest,
)
from app.models.evaluation import (
    CriterionStatus,
    Verdict,
    DecisionOutcome,
    CriterionEvaluationResult,
    EvaluationReport,
)
from app.models.policy import Policy, PolicyLifecycleStatus

logger = logging.getLogger(__name__)

class PolicyVerificationGateError(Exception):
    """Raised when policy criteria or lifecycle status fails verification gate."""
    pass

class CriteriaService:
    """
    Phase 2: Authoritative Criteria Encoding, Verification Gate, and Deterministic Logic Engine.
    Guarantees:
    1. Zero LLM hallucination in logic evaluation; deterministic and auditable.
    2. Strict Policy Verification Gate: No case evaluated on unapproved/unverified criteria.
    3. Explicit Status Semantics: 'Not Documented' != 'Clinical Failure'.
    4. Exact source text, page citations, and plain-English round-trip descriptions.
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir / "rulesets"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_ruleset_file(self, policy_id: str) -> Path:
        safe_id = policy_id.replace("/", "_").replace("\\", "_")
        return self.storage_dir / f"{safe_id}_ruleset.json"

    def get_ruleset(self, policy_id: str) -> Optional[PolicyRuleset]:
        file_path = self._get_ruleset_file(policy_id)
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return PolicyRuleset(**data)

    def save_ruleset(self, ruleset: PolicyRuleset) -> PolicyRuleset:
        file_path = self._get_ruleset_file(ruleset.policy_id)
        ruleset.last_updated = datetime.now(timezone.utc).isoformat()
        dump_dict = ruleset.model_dump() if hasattr(ruleset, "model_dump") else ruleset.dict()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dump_dict, f, indent=2)
        return ruleset

    @staticmethod
    def generate_plain_english_description(rule: CriterionRule) -> str:
        """Generates an accurate, readable round-trip description of the rule."""
        if rule.criterion_type == CriterionType.LOGIC_GROUP:
            if rule.operator == LogicOperator.AND:
                return f"All of the following {len(rule.children)} requirements must be simultaneously satisfied."
            elif rule.operator == LogicOperator.OR:
                return f"At least one of the following {len(rule.children)} clinical pathways must be satisfied."
            elif rule.operator == LogicOperator.MINIMUM_COUNT:
                return f"At least {rule.min_count or 1} of the {len(rule.children)} criteria must be documented and met."
        elif rule.criterion_type == CriterionType.DURATION:
            return f"Clinical symptoms must persist for at least {rule.threshold_value} {rule.threshold_unit or 'weeks'} prior to authorization."
        elif rule.criterion_type == CriterionType.NUMERIC_THRESHOLD:
            op_sym = rule.comparison_op or ">="
            return f"Measured clinical parameter must be {op_sym} {rule.threshold_value} {rule.threshold_unit or ''}."
        elif rule.criterion_type == CriterionType.EXCLUSION:
            return f"Exclusion contraindication: If {rule.section_name.lower()} is present, coverage is denied unless formal medical director override is documented."
        elif rule.criterion_type == CriterionType.NOTE_EXPLANATORY:
            return f"Explanatory guidance note (non-binding clinical context): {rule.source_text[:120]}..."
        
        cond_text = f" [Applicable only when {rule.conditional_prerequisite} is present]" if rule.conditional_prerequisite else ""
        return f"Requirement: {rule.section_name}. {rule.source_text[:120]}...{cond_text}"

    def verify_ruleset_gate(
        self,
        policy: Policy,
        request: VerificationGateRequest
    ) -> PolicyRuleset:
        """
        Policy Verification Gate Execution (Master Plan §7 Phase 2):
        1. Compares encoded criteria count vs source policy count.
        2. Validates independent second reviewer sign-off.
        3. Validates policy SHA-256 checksum matching original PDF.
        4. Validates side-by-side & plain-English review assertions.
        """
        ruleset = self.get_ruleset(policy.id)
        if not ruleset:
            raise PolicyVerificationGateError(f"No criteria ruleset found for policy {policy.id}. Must encode criteria before gate verification.")

        # 1. Checksum verification
        if policy.sha256_checksum and ruleset.policy_checksum:
            if policy.sha256_checksum != ruleset.policy_checksum:
                raise PolicyVerificationGateError(
                    f"Policy verification gate failed: PDF checksum mismatch. "
                    f"Expected {policy.sha256_checksum[:16]}..., ruleset recorded {ruleset.policy_checksum[:16]}... "
                    "Ruleset must be tied to the exact source policy version."
                )

        # 2. Reviewer requirements (Mandatory secondary independent reviewer)
        if not request.primary_reviewer or not request.primary_reviewer.strip():
            raise PolicyVerificationGateError("Primary reviewer name is required for verification gate sign-off.")
        if not request.secondary_reviewer or not request.secondary_reviewer.strip():
            raise PolicyVerificationGateError("Independent secondary reviewer name is mandatory under clinical governance.")
        if request.primary_reviewer.strip().lower() == request.secondary_reviewer.strip().lower():
            raise PolicyVerificationGateError("Secondary reviewer must be an independent individual, distinct from primary reviewer.")

        # 3. Completeness count
        encoded_count = len([r for r in ruleset.rules if r.criterion_type != CriterionType.NOTE_EXPLANATORY])
        if request.source_criteria_count != encoded_count:
            raise PolicyVerificationGateError(
                f"Criteria count mismatch: Source policy has {request.source_criteria_count} criteria, but encoded ruleset contains {encoded_count}. "
                "All criteria must be accounted for with none added and none dropped."
            )

        # 4. Assertions
        if not request.side_by_side_verified:
            raise PolicyVerificationGateError("Side-by-side line-by-line verification against PDF must be confirmed.")
        if not request.plain_english_verified:
            raise PolicyVerificationGateError("Plain-English round-trip verification must be confirmed.")

        # Record sign-off and promote status
        signoff = ReviewerSignoff(
            primary_reviewer=request.primary_reviewer.strip(),
            primary_reviewer_role=request.primary_reviewer_role.strip(),
            secondary_reviewer=request.secondary_reviewer.strip(),
            secondary_reviewer_role=request.secondary_reviewer_role.strip(),
            signed_off_at=datetime.now(timezone.utc).isoformat(),
            policy_checksum=ruleset.policy_checksum,
            source_criteria_count=request.source_criteria_count,
            encoded_criteria_count=encoded_count,
            side_by_side_verified=True,
            plain_english_verified=True,
            notes=request.notes
        )

        ruleset.verification_status = VerificationStatus.APPROVED_VERIFIED
        ruleset.signoff = signoff
        for r in ruleset.rules:
            r.verification_status = VerificationStatus.APPROVED_VERIFIED
            r.reviewer_signoff = signoff

        return self.save_ruleset(ruleset)

    # --- Deterministic Evaluation Logic ---

    def evaluate_rule(
        self,
        rule: CriterionRule,
        facts: Dict[str, Any],
        policy: Policy
    ) -> Tuple[CriterionEvaluationResult, List[CriterionEvaluationResult]]:
        """
        Recursively evaluates a criterion rule or logic group against patient facts.
        Returns: (Primary Result, List of Child Results)
        """
        child_results: List[CriterionEvaluationResult] = []

        # 1. Explanatory Note (Non-binding)
        if rule.criterion_type == CriterionType.NOTE_EXPLANATORY:
            res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt="Explanatory guidance note",
                source_page=rule.source_page,
                status=CriterionStatus.NOT_APPLICABLE,
                ui_symbol="–",
                ui_label="Informational Note",
                comment="Guidance note; not a binding authorization gate",
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group="EXPLANATORY_NOTES",
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=False
            )
            return res, child_results

        # 2. Check Conditional Prerequisite
        if rule.conditional_prerequisite:
            cond_fact = facts.get(rule.conditional_prerequisite)
            # If prerequisite is not met or not requested, criterion is NOT_APPLICABLE
            if not cond_fact or not cond_fact.get("value", False):
                res = CriterionEvaluationResult(
                    rule_id=rule.id,
                    criterion_name=rule.section_name,
                    section=rule.section_number,
                    requirement=rule.source_text,
                    evidence_excerpt="Conditional prerequisite not triggered",
                    source_page=rule.source_page,
                    status=CriterionStatus.NOT_APPLICABLE,
                    ui_symbol="–",
                    ui_label="Not applicable",
                    comment=f"Prerequisite condition '{rule.conditional_prerequisite}' not applicable to this order",
                    policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                    logic_group=rule.operator.value if rule.operator else None,
                    plain_english_rationale=rule.plain_english_description,
                    is_exclusion=False
                )
                return res, child_results

        # 3. Logic Group Evaluation (AND, OR, MINIMUM_COUNT)
        if rule.criterion_type == CriterionType.LOGIC_GROUP and rule.children:
            for child in rule.children:
                c_res, c_sub = self.evaluate_rule(child, facts, policy)
                child_results.append(c_res)
                child_results.extend(c_sub)

            # Filter out non-applicable children for group calculation
            active_children = [c for c in child_results if c.status != CriterionStatus.NOT_APPLICABLE and not c.is_exclusion]
            met_count = sum(1 for c in active_children if c.status == CriterionStatus.MET)
            not_met_count = sum(1 for c in active_children if c.status == CriterionStatus.NOT_MET)
            missing_count = sum(1 for c in active_children if c.status == CriterionStatus.NOT_DOCUMENTED)
            unclear_count = sum(1 for c in active_children if c.status in (CriterionStatus.UNCLEAR_CONFLICTING, CriterionStatus.POLICY_AMBIGUITY))

            if rule.operator == LogicOperator.AND:
                if unclear_count > 0:
                    group_status = CriterionStatus.UNCLEAR_CONFLICTING
                    group_symbol = "❌"
                    group_label = "Unclear"
                    group_comment = f"Ambiguity or conflicting documentation present in {unclear_count} required conditions."
                elif not_met_count > 0:
                    group_status = CriterionStatus.NOT_MET
                    group_symbol = "❌"
                    group_label = "Not met"
                    group_comment = f"{not_met_count} of {len(active_children)} required conditions explicitly failed."
                elif missing_count > 0:
                    group_status = CriterionStatus.NOT_DOCUMENTED
                    group_symbol = "❌"
                    group_label = "Not documented"
                    group_comment = f"{missing_count} required conditions lack documentation in submitted records."
                else:
                    group_status = CriterionStatus.MET
                    group_symbol = "✅"
                    group_label = "Satisfied"
                    group_comment = f"All {len(active_children)} required criteria met."

            elif rule.operator == LogicOperator.OR:
                if met_count > 0:
                    group_status = CriterionStatus.MET
                    group_symbol = "✅"
                    group_label = "Satisfied"
                    group_comment = f"{met_count} of {len(active_children)} alternative pathways satisfied."
                elif unclear_count > 0:
                    group_status = CriterionStatus.UNCLEAR_CONFLICTING
                    group_symbol = "❌"
                    group_label = "Unclear"
                    group_comment = "Documentation for alternative pathways is ambiguous or conflicting."
                elif missing_count == len(active_children):
                    group_status = CriterionStatus.NOT_DOCUMENTED
                    group_symbol = "❌"
                    group_label = "Not documented"
                    group_comment = "No documentation found for any alternative pathway."
                else:
                    group_status = CriterionStatus.NOT_MET
                    group_symbol = "❌"
                    group_label = "Not met"
                    group_comment = "None of the acceptable clinical pathways were satisfied."

            elif rule.operator == LogicOperator.MINIMUM_COUNT:
                target_min = rule.min_count or 1
                if met_count >= target_min:
                    group_status = CriterionStatus.MET
                    group_symbol = "✅"
                    group_label = "Satisfied"
                    group_comment = f"Satisfied {met_count} conditions (minimum required: {target_min})."
                elif unclear_count > 0 and (met_count + unclear_count >= target_min):
                    group_status = CriterionStatus.UNCLEAR_CONFLICTING
                    group_symbol = "❌"
                    group_label = "Unclear"
                    group_comment = f"Potentially meets threshold ({met_count} confirmed), but {unclear_count} criteria are unclear."
                elif (met_count + missing_count) >= target_min:
                    group_status = CriterionStatus.NOT_DOCUMENTED
                    group_symbol = "❌"
                    group_label = "Not documented"
                    group_comment = f"Only {met_count} confirmed; requires documentation for remaining items to reach {target_min}."
                else:
                    group_status = CriterionStatus.NOT_MET
                    group_symbol = "❌"
                    group_label = "Not met"
                    group_comment = f"Failed to meet minimum threshold of {target_min} conditions ({met_count} met)."
            else:
                group_status = CriterionStatus.MET
                group_symbol = "✅"
                group_label = "Satisfied"
                group_comment = "Group conditions evaluated."

            group_res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt=f"{met_count}/{len(active_children)} active child conditions satisfied",
                source_page=rule.source_page,
                status=group_status,
                ui_symbol=group_symbol,
                ui_label=group_label,
                comment=group_comment,
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group=rule.operator.value if rule.operator else None,
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=False
            )
            return group_res, child_results

        # 4. Atomic Criterion / Threshold / Duration / Exclusion
        fact = facts.get(rule.fact_key) if rule.fact_key else None

        # A. Not documented check
        if fact is None:
            res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt="No matching clinical documentation found in submitted records",
                source_page=rule.source_page,
                status=CriterionStatus.NOT_DOCUMENTED,
                ui_symbol="❌",
                ui_label="Not documented",
                comment="Required clinical evidence not documented in medical record",
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group="MANDATORY_CRITERIA" if rule.is_mandatory else "OPTIONAL",
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=rule.is_exclusion
            )
            return res, child_results

        value = fact.get("value")
        excerpt = fact.get("excerpt", "")
        page = fact.get("source_page", rule.source_page)
        is_unclear = fact.get("is_unclear", False)

        # B. Unclear / Conflicting check
        if is_unclear:
            res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.UNCLEAR_CONFLICTING,
                ui_symbol="❌",
                ui_label="Unclear",
                comment="Ambiguous or conflicting clinical notes require manual clinician review",
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group="UNCLEAR_EVIDENCE",
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=rule.is_exclusion
            )
            return res, child_results

        # C. Exclusion Contraindication check
        if rule.is_exclusion:
            # If the exclusion fact is present/true, it triggers an immediate denial
            if value is True:
                res = CriterionEvaluationResult(
                    rule_id=rule.id,
                    criterion_name=rule.section_name,
                    section=rule.section_number,
                    requirement=rule.source_text,
                    evidence_excerpt=excerpt,
                    source_page=page,
                    status=CriterionStatus.NOT_MET,
                    ui_symbol="❌",
                    ui_label="Exclusion Present",
                    comment="Clinical contraindication/exclusion condition is present; request cannot be approved",
                    policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                    logic_group="CONTRAINDICATION",
                    plain_english_rationale=rule.plain_english_description,
                    is_exclusion=True
                )
            else:
                res = CriterionEvaluationResult(
                    rule_id=rule.id,
                    criterion_name=rule.section_name,
                    section=rule.section_number,
                    requirement=rule.source_text,
                    evidence_excerpt=excerpt or "No exclusion or contraindication present",
                    source_page=page,
                    status=CriterionStatus.MET,
                    ui_symbol="✅",
                    ui_label="Satisfied",
                    comment="Exclusion condition ruled out",
                    policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                    logic_group="CONTRAINDICATION",
                    plain_english_rationale=rule.plain_english_description,
                    is_exclusion=True
                )
            return res, child_results

        # D. Numeric Threshold / Duration Comparison
        if rule.criterion_type in (CriterionType.NUMERIC_THRESHOLD, CriterionType.DURATION) or rule.threshold_value is not None:
            thresh = rule.threshold_value
            op = rule.comparison_op or ">="
            unit = rule.threshold_unit or ""
            is_valid_num = isinstance(value, (int, float))

            passed = False
            if is_valid_num:
                if op == ">=":
                    passed = value >= thresh
                elif op == "<=":
                    passed = value <= thresh
                elif op == ">":
                    passed = value > thresh
                elif op == "<":
                    passed = value < thresh
                elif op == "==":
                    passed = value == thresh
                elif op == "BETWEEN" and rule.threshold_max is not None:
                    passed = (thresh <= value <= rule.threshold_max)

            if passed:
                res = CriterionEvaluationResult(
                    rule_id=rule.id,
                    criterion_name=rule.section_name,
                    section=rule.section_number,
                    requirement=rule.source_text,
                    evidence_excerpt=excerpt,
                    source_page=page,
                    status=CriterionStatus.MET,
                    ui_symbol="✅",
                    ui_label="Satisfied",
                    comment=f"Value {value} {unit} satisfies requirement ({op} {thresh} {unit})",
                    policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                    logic_group="DURATION_AND_THRESHOLDS",
                    plain_english_rationale=rule.plain_english_description,
                    is_exclusion=False
                )
            else:
                res = CriterionEvaluationResult(
                    rule_id=rule.id,
                    criterion_name=rule.section_name,
                    section=rule.section_number,
                    requirement=rule.source_text,
                    evidence_excerpt=excerpt,
                    source_page=page,
                    status=CriterionStatus.NOT_MET,
                    ui_symbol="❌",
                    ui_label="Not met",
                    comment=f"Value {value} {unit} fails required threshold ({op} {thresh} {unit})",
                    policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                    logic_group="DURATION_AND_THRESHOLDS",
                    plain_english_rationale=rule.plain_english_description,
                    is_exclusion=False
                )
            return res, child_results

        # E. Boolean Clinical Satisfaction
        if value is True:
            res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.MET,
                ui_symbol="✅",
                ui_label="Satisfied",
                comment="Clinical requirement documented and confirmed",
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group="CLINICAL_CRITERIA",
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=False
            )
        else:
            res = CriterionEvaluationResult(
                rule_id=rule.id,
                criterion_name=rule.section_name,
                section=rule.section_number,
                requirement=rule.source_text,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.NOT_MET,
                ui_symbol="❌",
                ui_label="Not met",
                comment="Clinical documentation explicitly contradicts or fails requirement",
                policy_citation=f"{policy.policy_name} v{policy.version}, {rule.section_number}, Page {rule.source_page}",
                logic_group="CLINICAL_CRITERIA",
                plain_english_rationale=rule.plain_english_description,
                is_exclusion=False
            )
        return res, child_results

    def evaluate_policy_case(
        self,
        policy: Policy,
        case_id: str,
        patient_name: str,
        facts: Dict[str, Any],
        evaluation_date: Optional[str] = None
    ) -> EvaluationReport:
        """
        Master Plan Deterministic Evaluation Engine:
        1. Enforces Policy Verification Gate:
           - Policy MUST be APPROVED_FOR_USE.
           - Ruleset MUST be APPROVED_VERIFIED by two reviewers.
        2. Evaluates all criteria, nested groups, thresholds, durations, and exclusions.
        3. Separates 'Not Documented' from 'Clinical Failure'.
        4. Key reasoning strictly precedes final verdict.
        """
        eval_date = evaluation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Verification Gate Enforcement
        if policy.lifecycle_status != PolicyLifecycleStatus.APPROVED_FOR_USE:
            raise PolicyVerificationGateError(
                f"Policy Gate Blocked: Policy '{policy.id}' is currently in state '{policy.lifecycle_status}'. "
                "Policies must be 'APPROVED_FOR_USE' before clinical evaluation."
            )

        ruleset = self.get_ruleset(policy.id)
        if not ruleset or ruleset.verification_status != VerificationStatus.APPROVED_VERIFIED:
            raise PolicyVerificationGateError(
                f"Policy Verification Gate Blocked: Criteria ruleset for '{policy.id}' is not 'APPROVED_VERIFIED'. "
                "Two-reviewer verification gate sign-off is mandatory before authorization assessment."
            )

        all_results: List[CriterionEvaluationResult] = []
        for rule in ruleset.rules:
            primary_res, sub_results = self.evaluate_rule(rule, facts, policy)
            all_results.append(primary_res)
            all_results.extend(sub_results)

        # Analyze outcomes across active criteria
        evaluable = [r for r in all_results if r.status != CriterionStatus.NOT_APPLICABLE and not r.is_exclusion]
        exclusions = [r for r in all_results if r.is_exclusion]

        exclusion_triggered = any(ex.status == CriterionStatus.NOT_MET for ex in exclusions)
        met_rules = [r for r in evaluable if r.status == CriterionStatus.MET]
        not_met_rules = [r for r in evaluable if r.status == CriterionStatus.NOT_MET]
        not_doc_rules = [r for r in evaluable if r.status == CriterionStatus.NOT_DOCUMENTED]
        unclear_rules = [r for r in evaluable if r.status in (CriterionStatus.UNCLEAR_CONFLICTING, CriterionStatus.POLICY_AMBIGUITY)]

        # Construct key reasoning strictly before verdict
        key_reasoning: List[str] = []
        review_reasons: List[str] = []

        if exclusion_triggered:
            triggered_excl = [ex for ex in exclusions if ex.status == CriterionStatus.NOT_MET]
            key_reasoning.append(f"Contraindication/Exclusion triggered: {', '.join(e.criterion_name for e in triggered_excl)}")
            decision_outcome = DecisionOutcome.DENIED
            verdict = Verdict.NOT_APPROVED
            verdict_sentence = (
                f"Clinical authorization for {policy.procedure_full_name} cannot be approved. "
                f"A documented contraindication ({', '.join(e.criterion_name for e in triggered_excl)}) was identified."
            )
            requires_human_review = True
            review_reasons.append("Clinical contraindication requires peer-to-peer or medical director review.")

        elif unclear_rules:
            key_reasoning.append(f"Ambiguous or conflicting clinical documentation in {len(unclear_rules)} criteria: {', '.join(u.rule_id for u in unclear_rules)}")
            if met_rules:
                key_reasoning.append(f"Satisfied conditions: {', '.join(m.rule_id for m in met_rules)}")
            decision_outcome = DecisionOutcome.CANNOT_BE_DETERMINED
            verdict = Verdict.CANNOT_BE_DETERMINED
            verdict_sentence = (
                f"Authorization for {policy.procedure_full_name} cannot be determined automatically due to ambiguous or conflicting medical records. "
                f"Clinician review is required for: {', '.join(u.rule_id for u in unclear_rules)}."
            )
            requires_human_review = True
            review_reasons.append("Documentation ambiguity or clinical discrepancy requires human adjudication.")

        elif not_met_rules:
            key_reasoning.append(f"Documented clinical evidence explicitly fails {len(not_met_rules)} mandatory requirements: {', '.join(n.rule_id for n in not_met_rules)}")
            if met_rules:
                key_reasoning.append(f"Satisfied conditions: {', '.join(m.rule_id for m in met_rules)}")
            decision_outcome = DecisionOutcome.DENIED
            verdict = Verdict.NOT_APPROVED
            verdict_sentence = (
                f"Not all mandatory clinical conditions required for {policy.procedure_full_name} have been satisfied. "
                f"Unmet criteria: {', '.join(n.rule_id for n in not_met_rules)}. Therefore the request is not approved."
            )
            requires_human_review = True
            review_reasons.append("Clinical criteria failure; eligible for appeal or peer-to-peer discussion.")

        elif not_doc_rules:
            # Missing documentation is NOT treated as a clinical failure!
            key_reasoning.append(f"Missing clinical documentation for {len(not_doc_rules)} requirements: {', '.join(d.rule_id for d in not_doc_rules)}")
            key_reasoning.append("Absence of documentation is distinct from clinical failure; request may be reassessed upon record submission.")
            if met_rules:
                key_reasoning.append(f"Satisfied conditions: {', '.join(m.rule_id for m in met_rules)}")
            decision_outcome = DecisionOutcome.ADDITIONAL_DOCUMENTATION_REQUIRED
            verdict = Verdict.NOT_APPROVED
            verdict_sentence = (
                f"The clinical note does not contain documentation for: {', '.join(d.rule_id for d in not_doc_rules)}. "
                f"This does not represent a clinical denial; authorization may be re-assessed once the missing records are submitted."
            )
            requires_human_review = True
            review_reasons.append("Supplemental clinical documentation required from ordering provider.")

        else:
            # All active criteria MET!
            key_reasoning.append("All required clinical criteria, thresholds, and duration mandates are fully satisfied.")
            for m in met_rules:
                key_reasoning.append(f"{m.criterion_name} [{m.section}]: {m.evidence_excerpt}")
            decision_outcome = DecisionOutcome.APPROVED
            verdict = Verdict.APPROVED
            verdict_sentence = (
                f"Approval of {policy.procedure_full_name} requires all mandatory criteria to be met. "
                f"Conditions ({', '.join(m.rule_id for m in met_rules)}) are documented and satisfied. "
                f"Therefore the request is APPROVED."
            )
            requires_human_review = False

        return EvaluationReport(
            case_id=case_id,
            patient_name=patient_name,
            procedure=policy.procedure_full_name,
            insurer=policy.insurer,
            policy_id=policy.id,
            policy_version=policy.version,
            evaluation_date=eval_date,
            criteria_results=all_results,
            key_reasoning=key_reasoning,
            verdict=verdict,
            verdict_sentence=verdict_sentence,
            requires_human_review=requires_human_review,
            review_reasons=review_reasons,
            decision_outcome=decision_outcome,
            policy_checksum=policy.sha256_checksum,
            verification_gate_verified=True
        )
