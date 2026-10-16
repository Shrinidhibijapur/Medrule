import { ReviewCase } from '../types';

export const mockJohnDoeCase: ReviewCase = {
  id: 'CASE-2026-001',
  patient_name: 'John Doe',
  patient_age: 42,
  gender: 'M',
  dob: '01/15/1980',
  facility: 'Riverside Medical Center',
  date_of_visit: '10/05/2026',
  procedure: 'CT Scan of Head with Contrast',
  insurance_plan: 'United Healthcare',
  policy_version: '2026',
  status: 'Approved',
  evaluation_date: 'Oct 12, 2026',
  chief_complaint: 'Persistent headaches and dizziness',
  history_of_illness: '42 year old male presents with recurrent severe headaches and dizziness persisting for 3 months with associated visual disturbances.',
  clinical_findings: [
    '1. Neurological examination abnormal: mild ataxia, asymmetric reflexes.',
    '2. Conservative treatment attempted over 8 weeks (no improvement).',
    '3. Patient has history of hypertension.'
  ],
  impression: 'Rule out intracranial pathology or mass lesion.',
  recommendation: 'CT scan of head with contrast clinically indicated.',
  criteria_results: [
    {
      rule_id: '1',
      criterion_name: 'Clinical Indication',
      section: 'Section 4.2.1',
      requirement: 'Patient must have neurological symptoms or signs',
      evidence_excerpt: 'Headaches, dizziness, visual disturbances',
      source_page: 1,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Meets criteria for neurological symptoms'
    },
    {
      rule_id: '2',
      criterion_name: 'Duration of Symptoms',
      section: 'Section 4.2.2',
      requirement: 'Symptoms must persist for >= 6 weeks',
      evidence_excerpt: 'Present for 3 months',
      source_page: 1,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Exceeds 6 weeks requirement'
    },
    {
      rule_id: '3',
      criterion_name: 'Previous Treatment',
      section: 'Section 4.2.3',
      requirement: 'Conservative treatment attempted',
      evidence_excerpt: 'Conservative treatment (no improvement)',
      source_page: 1,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Documented trial of treatment'
    },
    {
      rule_id: '4',
      criterion_name: 'Documented Findings',
      section: 'Section 4.2.4',
      requirement: 'Abnormal neurological examination',
      evidence_excerpt: 'Neurological examination abnormal',
      source_page: 2,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Meets requirement'
    },
    {
      rule_id: '5',
      criterion_name: 'Rule out Serious Condition',
      section: 'Section 4.2.5',
      requirement: 'Must be to rule out intracranial pathology or mass',
      evidence_excerpt: 'Rule out intracranial pathology',
      source_page: 2,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Valid indication'
    },
    {
      rule_id: '6',
      criterion_name: 'Contrast Justification',
      section: 'Section 4.2.6',
      requirement: 'If contrast requested, must be clinically indicated',
      evidence_excerpt: 'Further evaluation needed',
      source_page: 2,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Clinically indicated'
    }
  ],
  key_reasoning: [
    'All required clinical criteria are satisfied',
    'Documented neurological symptoms',
    'Symptoms persist for more than 6 weeks',
    'Conservative treatment already attempted',
    'Abnormal neurological examination',
    'Valid clinical indication to rule out intracranial pathology'
  ]
};

export const mockJaneSmithUnmetCase: ReviewCase = {
  id: 'CASE-2026-002',
  patient_name: 'Jane Smith',
  patient_age: 38,
  gender: 'F',
  dob: '05/20/1988',
  facility: 'Westside Clinic',
  date_of_visit: '10/08/2026',
  procedure: 'CT Scan of Head with Contrast',
  insurance_plan: 'United Healthcare',
  policy_version: '2026.1',
  status: 'Not Approved',
  evaluation_date: 'Oct 14, 2026',
  chief_complaint: 'Mild tension-type headache for 2 weeks',
  history_of_illness: 'Patient reports intermittent bilateral band-like headache for 2 weeks without red flags, neurological deficits, or nausea.',
  clinical_findings: [
    '1. Neurological examination completely normal without asymmetry.',
    '2. Symptoms present for 2 weeks only.',
    '3. No trial of conservative medications attempted.'
  ],
  impression: 'Episodic tension headache without atypical or focal features.',
  recommendation: 'Recommend conservative analgesia and outpatient tracking.',
  criteria_results: [
    {
      rule_id: '1',
      criterion_name: 'Clinical Indication',
      section: 'Section 4.2.1',
      requirement: 'Patient must have neurological symptoms or signs',
      evidence_excerpt: 'Normal neurological exam; typical tension headache',
      source_page: 1,
      status: 'NOT_MET',
      ui_symbol: '❌',
      ui_label: 'Not met',
      comment: 'Lacks documented focal neurological signs or atypical features'
    },
    {
      rule_id: '2',
      criterion_name: 'Duration of Symptoms',
      section: 'Section 4.2.2',
      requirement: 'Symptoms must persist for >= 6 weeks',
      evidence_excerpt: 'Documented 2 weeks duration',
      source_page: 2,
      status: 'NOT_MET',
      ui_symbol: '❌',
      ui_label: 'Not met',
      comment: 'Duration of 2 weeks does not meet required threshold of >= 6 weeks'
    },
    {
      rule_id: '3',
      criterion_name: 'Previous Treatment',
      section: 'Section 4.2.3',
      requirement: 'Conservative treatment attempted',
      evidence_excerpt: 'No conservative medications attempted prior to imaging request',
      source_page: 2,
      status: 'NOT_MET',
      ui_symbol: '❌',
      ui_label: 'Not met',
      comment: 'No trial of conservative management documented'
    },
    {
      rule_id: '4',
      criterion_name: 'Documented Findings',
      section: 'Section 4.2.4',
      requirement: 'Abnormal neurological examination',
      evidence_excerpt: 'Neurological exam documented as entirely benign and normal',
      source_page: 3,
      status: 'NOT_MET',
      ui_symbol: '❌',
      ui_label: 'Not met',
      comment: 'Fails requirement for documented abnormal findings'
    },
    {
      rule_id: '5',
      criterion_name: 'Rule out Serious Condition',
      section: 'Section 4.2.5',
      requirement: 'Must be to rule out intracranial pathology or mass',
      evidence_excerpt: 'Request submitted for patient reassurance, not suspicion of neoplasm',
      source_page: 3,
      status: 'NOT_MET',
      ui_symbol: '❌',
      ui_label: 'Not met',
      comment: 'Lacks clinical justification to rule out mass lesion'
    },
    {
      rule_id: '6',
      criterion_name: 'Contrast Justification',
      section: 'Section 4.2.6',
      requirement: 'If contrast requested, must be clinically indicated',
      evidence_excerpt: 'Contrast not requested or justified',
      source_page: 4,
      status: 'NOT_APPLICABLE',
      ui_symbol: '–',
      ui_label: 'Not applicable',
      comment: 'Conditional on IV contrast request; not applicable'
    }
  ],
  key_reasoning: [
    'Symptoms duration (2 weeks) does not meet mandatory 6-week policy threshold [Section 4.2.2]',
    'Neurological examination is normal without asymmetric signs [Section 4.2.4]',
    'No trial of conservative medical therapy attempted [Section 4.2.3]'
  ]
};

export const mockRobertChenMissingDocCase: ReviewCase = {
  id: 'CASE-2026-003',
  patient_name: 'Robert Chen',
  patient_age: 55,
  gender: 'M',
  dob: '03/12/1971',
  facility: 'Metro General Neuroscience',
  date_of_visit: '10/11/2026',
  procedure: 'CT Scan of Head with Contrast',
  insurance_plan: 'United Healthcare',
  policy_version: '2026.1',
  status: 'In Review',
  evaluation_date: 'Oct 15, 2026',
  chief_complaint: 'Progressive unilateral headache and limb weakness',
  history_of_illness: '55 year old male with 9 weeks of progressive left-sided headache and mild pronator drift.',
  clinical_findings: [
    '1. Abnormal neurological exam: left pronator drift and hyperreflexia.',
    '2. Symptoms present for 9 weeks.',
    '3. Conservative therapy trial: NOT DOCUMENTED in submitted intake chart.'
  ],
  impression: 'Rule out structural intracranial lesion or space-occupying mass.',
  recommendation: 'Request supplemental clinic chart showing conservative therapy before final disposition.',
  criteria_results: [
    {
      rule_id: '1',
      criterion_name: 'Clinical Indication',
      section: 'Section 4.2.1',
      requirement: 'Patient must have neurological symptoms or signs',
      evidence_excerpt: 'Left-sided headaches and pronator drift',
      source_page: 1,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Focal neurological symptoms confirmed'
    },
    {
      rule_id: '2',
      criterion_name: 'Duration of Symptoms',
      section: 'Section 4.2.2',
      requirement: 'Symptoms must persist for >= 6 weeks',
      evidence_excerpt: 'Present for 9 weeks',
      source_page: 2,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Duration of 9 weeks exceeds 6-week threshold'
    },
    {
      rule_id: '3',
      criterion_name: 'Previous Treatment',
      section: 'Section 4.2.3',
      requirement: 'Conservative treatment attempted',
      evidence_excerpt: 'No documentation of prior conservative therapy in submitted records',
      source_page: 2,
      status: 'NOT_DOCUMENTED',
      ui_symbol: '❌',
      ui_label: 'Not documented',
      comment: 'Required trial of conservative treatment not documented in intake record'
    },
    {
      rule_id: '4',
      criterion_name: 'Documented Findings',
      section: 'Section 4.2.4',
      requirement: 'Abnormal neurological examination',
      evidence_excerpt: 'Documented pronator drift and asymmetric reflexes',
      source_page: 3,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Objective abnormal neurological findings documented'
    },
    {
      rule_id: '5',
      criterion_name: 'Rule out Serious Condition',
      section: 'Section 4.2.5',
      requirement: 'Must be to rule out intracranial pathology or mass',
      evidence_excerpt: 'Evaluation of suspected mass lesion',
      source_page: 3,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Documented requirement to evaluate mass lesion'
    },
    {
      rule_id: '6',
      criterion_name: 'Contrast Justification',
      section: 'Section 4.2.6',
      requirement: 'If contrast requested, must be clinically indicated',
      evidence_excerpt: 'Contrast justified for suspected intracranial mass',
      source_page: 4,
      status: 'MET',
      ui_symbol: '✅',
      ui_label: 'Satisfied',
      comment: 'Contrast enhancement justified'
    }
  ],
  key_reasoning: [
    'Missing documentation for conservative therapy trial [Section 4.2.3]',
    'Absence of documentation is distinct from clinical failure; request can be re-assessed upon clinical record submission',
    'Satisfied conditions: Clinical Indication, Duration >= 6 weeks, Abnormal Findings, Rule out pathology'
  ]
};

export const mockCasesList = [
  { patient_name: 'John Doe', procedure: 'CT Scan', insurance_plan: 'United Healthcare', status: 'Approved', date: 'Oct 12, 2026' },
  { patient_name: 'Jane Smith', procedure: 'CT Scan', insurance_plan: 'United Healthcare', status: 'Not Approved', date: 'Oct 14, 2026' },
  { patient_name: 'Robert Chen', procedure: 'CT Scan', insurance_plan: 'United Healthcare', status: 'In Review', date: 'Oct 15, 2026' },
  { patient_name: 'Emily Davis', procedure: 'MRI', insurance_plan: 'Cigna', status: 'In Review', date: 'Oct 09, 2026' },
  { patient_name: 'Michael Brown', procedure: 'CT Scan', insurance_plan: 'Humana', status: 'Approved', date: 'Oct 08, 2026' },
  { patient_name: 'Sarah Wilson', procedure: 'MRI', insurance_plan: 'United Healthcare', status: 'Not Approved', date: 'Oct 07, 2026' },
];

