from typing import Dict, Any, List, Tuple
from app.models.policy import Policy, Criterion
from app.models.evaluation import (
    CriterionStatus,
    Verdict,
    CriterionEvaluationResult,
    EvaluationReport,
)

class DeterministicRulesEngine:
    """
    Deterministic Policy Evaluation Engine
    Evaluates clinical facts against approved policy criteria.
    Guarantees:
    - Never uses external unapproved rules.
    - Preserves explicit status semantics (Met, Not met, Not documented, etc.).
    - Renders binary UI symbols (✅, ❌) with accurate sub-labels.
    - Detailed reasoning precedes the final verdict sentence.
    """

    @staticmethod
    def evaluate_criterion(criterion: Criterion, facts: Dict[str, Any]) -> CriterionEvaluationResult:
        # Check conditional prerequisite
        if criterion.conditional_on:
            cond_fact = facts.get(criterion.conditional_on)
            if not cond_fact or not cond_fact.get("value", False):
                return CriterionEvaluationResult(
                    rule_id=criterion.id,
                    criterion_name=criterion.name,
                    section=criterion.section,
                    requirement=criterion.requirement,
                    evidence_excerpt="Not applicable for this request",
                    source_page=None,
                    status=CriterionStatus.NOT_APPLICABLE,
                    ui_symbol="–",
                    ui_label="Not applicable",
                    comment="Condition not triggered by procedure scope"
                )

        fact = facts.get(criterion.fact_key)

        # 1. Not documented check
        if fact is None:
            return CriterionEvaluationResult(
                rule_id=criterion.id,
                criterion_name=criterion.name,
                section=criterion.section,
                requirement=criterion.requirement,
                evidence_excerpt="No matching documentation found in medical note",
                source_page=None,
                status=CriterionStatus.NOT_DOCUMENTED,
                ui_symbol="❌",
                ui_label="Not documented",
                comment="Required clinical evidence not found in note"
            )

        value = fact.get("value")
        excerpt = fact.get("excerpt", "")
        page = fact.get("source_page")
        is_unclear = fact.get("is_unclear", False)

        # 2. Unclear / conflicting check
        if is_unclear:
            return CriterionEvaluationResult(
                rule_id=criterion.id,
                criterion_name=criterion.name,
                section=criterion.section,
                requirement=criterion.requirement,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.UNCLEAR_CONFLICTING,
                ui_symbol="❌",
                ui_label="Unclear",
                comment="Conflicting or ambiguous clinical documentation"
            )

        # 3. Numeric threshold comparison
        if criterion.min_value is not None:
            if isinstance(value, (int, float)) and value >= criterion.min_value:
                return CriterionEvaluationResult(
                    rule_id=criterion.id,
                    criterion_name=criterion.name,
                    section=criterion.section,
                    requirement=criterion.requirement,
                    evidence_excerpt=excerpt,
                    source_page=page,
                    status=CriterionStatus.MET,
                    ui_symbol="✅",
                    ui_label="Satisfied",
                    comment=f"Duration of {value} weeks exceeds {criterion.min_value} weeks requirement"
                )
            else:
                return CriterionEvaluationResult(
                    rule_id=criterion.id,
                    criterion_name=criterion.name,
                    section=criterion.section,
                    requirement=criterion.requirement,
                    evidence_excerpt=excerpt,
                    source_page=page,
                    status=CriterionStatus.NOT_MET,
                    ui_symbol="❌",
                    ui_label="Not met",
                    comment=f"Value {value} does not meet required threshold of {criterion.min_value}"
                )

        # 4. Boolean satisfaction
        if value is True:
            return CriterionEvaluationResult(
                rule_id=criterion.id,
                criterion_name=criterion.name,
                section=criterion.section,
                requirement=criterion.requirement,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.MET,
                ui_symbol="✅",
                ui_label="Satisfied",
                comment="Meets criteria per documented findings"
            )
        else:
            return CriterionEvaluationResult(
                rule_id=criterion.id,
                criterion_name=criterion.name,
                section=criterion.section,
                requirement=criterion.requirement,
                evidence_excerpt=excerpt,
                source_page=page,
                status=CriterionStatus.NOT_MET,
                ui_symbol="❌",
                ui_label="Not met",
                comment="Documented evidence contradicts or fails requirement"
            )

    @classmethod
    def _categorize_criteria(
        cls,
        policy: Policy,
        facts: Dict[str, Any]
    ) -> Tuple[List[CriterionEvaluationResult], List[str], List[str], List[str], List[str]]:
        criteria_results: List[CriterionEvaluationResult] = []
        satisfied_ids: List[str] = []
        failed_ids: List[str] = []
        missing_ids: List[str] = []
        review_reasons: List[str] = []

        for crit in policy.criteria:
            res = cls.evaluate_criterion(crit, facts)
            criteria_results.append(res)

            if res.status == CriterionStatus.MET:
                satisfied_ids.append(res.rule_id)
            elif res.status == CriterionStatus.NOT_DOCUMENTED:
                missing_ids.append(res.rule_id)
                failed_ids.append(res.rule_id)
            elif res.status in (CriterionStatus.UNCLEAR_CONFLICTING, CriterionStatus.POLICY_AMBIGUITY):
                failed_ids.append(res.rule_id)
                review_reasons.append(f"Ambiguity/Conflict in {res.rule_id}: {res.comment}")
            elif res.status != CriterionStatus.NOT_APPLICABLE:
                failed_ids.append(res.rule_id)

        return criteria_results, satisfied_ids, failed_ids, missing_ids, review_reasons

    @staticmethod
    def _build_key_reasoning(
        criteria_results: List[CriterionEvaluationResult],
        satisfied_ids: List[str],
        failed_ids: List[str],
        missing_ids: List[str]
    ) -> List[str]:
        if not failed_ids:
            bullets = ["All required clinical criteria are satisfied"]
            for cr in criteria_results:
                if cr.status == CriterionStatus.MET:
                    bullets.append(f"{cr.criterion_name}: {cr.evidence_excerpt}")
            return bullets

        bullets = []
        if satisfied_ids:
            bullets.append(f"Satisfied conditions: {', '.join(satisfied_ids)}")
        if missing_ids:
            bullets.append(f"Missing documentation for: {', '.join(missing_ids)}")
        unmet_only = [i for i in failed_ids if i not in missing_ids]
        if unmet_only:
            bullets.append(f"Unmet clinical criteria: {', '.join(unmet_only)}")
        return bullets

    @staticmethod
    def _determine_verdict(
        procedure_type: str,
        satisfied_ids: List[str],
        failed_ids: List[str],
        missing_ids: List[str],
        review_reasons: List[str]
    ) -> Tuple[Verdict, str, bool, List[str]]:
        reasons = list(review_reasons)
        if not failed_ids:
            verdict = Verdict.APPROVED
            verdict_sentence = (
                f"Approval of a {procedure_type} requires all minimum clinical criteria to be met. "
                f"Conditions {', '.join(satisfied_ids)} are satisfied and meet that minimum. "
                f"Therefore the {procedure_type} request can be approved."
            )
            return verdict, verdict_sentence, False, reasons

        verdict = Verdict.NOT_APPROVED
        unmet_only = [i for i in failed_ids if i not in missing_ids]
        if missing_ids and not unmet_only:
            verdict_sentence = (
                f"Not all conditions required as the minimum for approval of a {procedure_type} have been satisfied. "
                f"The note does not contain the evidence required for {', '.join(missing_ids)}; "
                f"the request may be re-assessed if that documentation is provided. "
                f"Therefore the {procedure_type} request is not approved at this time."
            )
            reasons.append("Missing documentation requires human review or supplemental record intake.")
        else:
            verdict_sentence = (
                f"Not all conditions required as the minimum for approval of a {procedure_type} have been satisfied. "
                f"Not satisfied: {', '.join(failed_ids)}. "
                f"Therefore the {procedure_type} request is not approved."
            )
        return verdict, verdict_sentence, True, reasons

    @classmethod
    def evaluate_case(
        cls,
        case_id: str,
        patient_name: str,
        policy: Policy,
        facts: Dict[str, Any],
        evaluation_date: str = "2026-10-12"
    ) -> EvaluationReport:
        criteria_results, satisfied_ids, failed_ids, missing_ids, review_reasons = (
            cls._categorize_criteria(policy, facts)
        )
        key_reasoning = cls._build_key_reasoning(criteria_results, satisfied_ids, failed_ids, missing_ids)
        verdict, verdict_sentence, requires_review, final_review_reasons = (
            cls._determine_verdict(policy.procedure_type, satisfied_ids, failed_ids, missing_ids, review_reasons)
        )

        return EvaluationReport(
            case_id=case_id,
            patient_name=patient_name,
            procedure=policy.procedure_full_name,
            insurer=policy.insurer,
            policy_id=policy.id,
            policy_version=policy.version,
            evaluation_date=evaluation_date,
            criteria_results=criteria_results,
            key_reasoning=key_reasoning,
            verdict=verdict,
            verdict_sentence=verdict_sentence,
            requires_human_review=requires_review,
            review_reasons=final_review_reasons
        )
