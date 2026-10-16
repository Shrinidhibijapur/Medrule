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
