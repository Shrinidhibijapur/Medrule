export type ViewMode = 
  | 'login'
  | 'dashboard'
  | 'new_review'
  | 'extracted_doc'
  | 'extracted_info'
  | 'criteria_evaluation'
  | 'detailed_analysis'
  | 'authorization_decision'
  | 'cases_history'
  | 'policy_library'
  | 'terminology'
  | 'settings'
  | 'ask_medrule';

export type CriterionStatus = 
  | 'MET'
  | 'NOT_MET'
  | 'NOT_DOCUMENTED'
  | 'UNCLEAR_CONFLICTING'
  | 'POLICY_AMBIGUITY'
  | 'NOT_APPLICABLE';

export type PolicyLifecycleStatus = 
  | 'DRAFT'
  | 'PROCESSING'
  | 'NEEDS_REVIEW'
  | 'APPROVED_FOR_USE'
  | 'ARCHIVED'
  | 'FAILED';

export type CaseVerdict = 'APPROVED' | 'NOT_APPROVED' | 'CANNOT_BE_DETERMINED';

export interface CriterionResult {
  rule_id: string;
  criterion_name: string;
  section: string;
  requirement: string;
  evidence_excerpt: string;
  source_page?: number;
  status: CriterionStatus;
  ui_symbol: string;
  ui_label: string;
  comment: string;
  policy_citation?: string;
  logic_group?: string;
  plain_english_rationale?: string;
  is_exclusion?: boolean;
  fact_key?: string;
  fact_confidence?: number;
  reviewer_overridden?: boolean;
  reviewer_override_by?: string;
  reviewer_override_reason?: string;
}

export interface ReviewCase {
  id: string;
  patient_name: string;
  patient_age: number;
  gender: string;
  dob: string;
  facility: string;
  date_of_visit: string;
  procedure: string;
  insurance_plan: string;
  policy_version: string;
  status: 'Approved' | 'Not Approved' | 'In Review';
  evaluation_date: string;
  chief_complaint: string;
  history_of_illness: string;
  clinical_findings: string[];
  impression: string;
  recommendation: string;
  criteria_results: CriterionResult[];
  key_reasoning: string[];
}

export interface PolicySection {
  id: string;
  section_number: string;
  heading: string;
  page_number: number;
  content: string;
  character_count: number;
  table_detected: boolean;
}

export interface ExtractionQualityReport {
  total_pages: number;
  scanned_pages_count: number;
  low_confidence_pages: number[];
  overall_quality: 'HIGH' | 'MEDIUM' | 'LOW_NEEDS_OCR';
  notes: string[];
}

export interface PolicyRecord {
  id: string;
  policy_id?: string;
  insurer: string;
  policy_name: string;
  plan?: string;
  version: string;
  procedure_type: string;
  procedure_full_name: string;
  cpt_codes: string[];
  effective_date: string;
  expiry_date?: string;
  upload_date?: string;
  sha256_checksum?: string;
  original_filename?: string;
  storage_path?: string;
  total_pages: number;
  lifecycle_status: PolicyLifecycleStatus;
  sections: PolicySection[];
  extraction_report?: ExtractionQualityReport;
}

export interface PolicySearchResult {
  policy_id: string;
  policy_name: string;
  version: string;
  insurer: string;
  section_id: string;
  section_number: string;
  heading: string;
  page_number: number;
  matched_snippet: string;
  lifecycle_status: PolicyLifecycleStatus;
}

export type CriterionType = 
  | 'CRITERION'
  | 'LOGIC_GROUP'
  | 'NUMERIC_THRESHOLD'
  | 'DURATION'
  | 'EXCLUSION'
  | 'NOTE_EXPLANATORY';

export type LogicOperator = 'AND' | 'OR' | 'MINIMUM_COUNT' | 'CONDITIONAL';

export type VerificationStatus = 'DRAFT' | 'REVIEWED' | 'APPROVED_VERIFIED' | 'REJECTED';

export interface ReviewerSignoff {
  primary_reviewer: string;
  primary_reviewer_role: string;
  secondary_reviewer: string;
  secondary_reviewer_role: string;
  signed_off_at: string;
  policy_checksum: string;
  source_criteria_count: number;
  encoded_criteria_count: number;
  side_by_side_verified: boolean;
  plain_english_verified: boolean;
  notes?: string;
}

export interface CriterionRule {
  id: string;
  policy_id: string;
  policy_version: string;
  section_number: string;
  section_name: string;
  source_page: number;
  source_text: string;
  plain_english_description: string;
  criterion_type: CriterionType;
  is_mandatory: boolean;
  fact_key?: string;
  operator?: LogicOperator;
  min_count?: number;
  comparison_op?: string;
  threshold_value?: number;
  threshold_unit?: string;
  conditional_prerequisite?: string;
  is_exclusion?: boolean;
  children?: CriterionRule[];
  verification_status: VerificationStatus;
  reviewer_signoff?: ReviewerSignoff;
}

export interface PolicyRuleset {
  policy_id: string;
  policy_name: string;
  policy_version: string;
  policy_checksum: string;
  procedure_type: string;
  rules: CriterionRule[];
  verification_status: VerificationStatus;
  signoff?: ReviewerSignoff;
  last_updated?: string;
}

export type ClinicalFactStatus = 'EXPLICIT' | 'UNCLEAR' | 'CONFLICTING' | 'ABSENT';

export interface ReviewerFactOverride {
  is_overridden: boolean;
  overridden_by: string;
  overridden_at: string;
  original_value?: any;
  corrected_value: any;
  original_status: ClinicalFactStatus;
  corrected_status: ClinicalFactStatus;
  reason: string;
}

export interface ExtractedFact {
  fact_key: string;
  label: string;
  value?: any;
  status: ClinicalFactStatus;
  excerpt?: string;
  source_page?: number;
  confidence: number;
  is_flagged_for_review?: boolean;
  flag_reason?: string;
  reviewer_override?: ReviewerFactOverride;
}

export interface ClinicalNoteRecord {
  case_id: string;
  patient_name: string;
  patient_age?: number;
  gender?: string;
  dob?: string;
  facility?: string;
  date_of_visit?: string;
  procedure_requested: string;
  procedure_type?: string;
  insurance_plan: string;
  policy_id: string;
  policy_version?: string;
  chief_complaint?: string;
  history_of_present_illness?: string;
  clinical_findings?: string[];
  impression?: string;
  physician_recommendation?: string;
  original_filename: string;
  storage_path?: string;
  sha256_checksum: string;
  total_pages: number;
  scanned_pages_count: number;
  overall_quality: string;
  ocr_engine_status: string;
  facts: Record<string, ExtractedFact>;
  raw_pages_text?: Array<{
    page_number: number;
    text: string;
    char_count: number;
    is_scanned: boolean;
  }>;
  is_synthetic: boolean;
  governance_warning: string;
  audit_trail: Array<Record<string, any>>;
  latest_outcome?: string;
  latest_evaluation?: any;
  created_at: string;
  updated_at: string;
}

export interface FactCorrectionPayload {
  fact_key: string;
  corrected_value: any;
  corrected_status: ClinicalFactStatus;
  reviewer_name: string;
  reason: string;
}

export interface FactFlagPayload {
  fact_key: string;
  reviewer_name: string;
  reason: string;
}

export type Verdict = 'APPROVED' | 'NOT_APPROVED' | 'CANNOT_BE_DETERMINED';

export type DecisionOutcome = 
  | 'APPROVED' 
  | 'DENIED' 
  | 'ADDITIONAL_DOCUMENTATION_REQUIRED' 
  | 'CANNOT_BE_DETERMINED';

export interface CriterionEvaluationResult {
  rule_id: string;
  criterion_name: string;
  section: string;
  requirement: string;
  evidence_excerpt: string;
  source_page?: number;
  status: CriterionStatus;
  ui_symbol: string;
  ui_label: string;
  comment: string;
  policy_citation?: string;
  logic_group?: string;
  plain_english_rationale?: string;
  is_exclusion: boolean;
  fact_key?: string;
  fact_confidence?: number;
  reviewer_overridden?: boolean;
  reviewer_override_by?: string;
  reviewer_override_reason?: string;
}

export interface EvaluationReport {
  case_id: string;
  patient_name: string;
  procedure: string;
  insurer: string;
  policy_id: string;
  policy_version: string;
  evaluation_date: string;
  criteria_results: CriterionEvaluationResult[];
  key_reasoning: string[];
  verdict: Verdict;
  verdict_sentence: string;
  requires_human_review: boolean;
  review_reasons: string[];
  decision_outcome?: DecisionOutcome;
  policy_checksum?: string;
  verification_gate_verified: boolean;
  is_synthetic_demo: boolean;
  governance_notice: string;
}

export type UserRole = 'Reviewer MD' | 'Nurse Auditor' | 'Compliance Officer' | 'System Admin';

export interface UserProfile {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: string;
  permissions: string[];
}

export interface CSRFTokenResponse {
  csrf_token: string;
  header_name: string;
}


