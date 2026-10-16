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

