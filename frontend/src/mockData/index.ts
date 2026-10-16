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

export const mockCasesList = [
  { patient_name: 'John Doe', procedure: 'CT Scan', insurance_plan: 'United Healthcare', status: 'Approved', date: 'Oct 12, 2026' },
  { patient_name: 'Jane Smith', procedure: 'MRI', insurance_plan: 'Aetna', status: 'Not Approved', date: 'Oct 11, 2026' },
  { patient_name: 'Robert Lee', procedure: 'CT Scan', insurance_plan: 'BCBS', status: 'Approved', date: 'Oct 10, 2026' },
  { patient_name: 'Emily Davis', procedure: 'MRI', insurance_plan: 'Cigna', status: 'In Review', date: 'Oct 09, 2026' },
  { patient_name: 'Michael Brown', procedure: 'CT Scan', insurance_plan: 'Humana', status: 'Approved', date: 'Oct 08, 2026' },
  { patient_name: 'Sarah Wilson', procedure: 'MRI', insurance_plan: 'United Healthcare', status: 'Not Approved', date: 'Oct 07, 2026' },
];
