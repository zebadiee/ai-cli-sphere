import { z } from 'zod';

/**
 * ECIR Validation Schema
 * 
 * Client-side validation matching ecir_schema.json
 * Enforces authority boundaries - no auto-assignment of critical fields
 */

// Classification codes - HUMAN ASSERTION REQUIRED
export const ClassificationCodeSchema = z.enum(['C1', 'C2', 'C3', 'FI']);

// Overall assessment - HUMAN ASSERTION REQUIRED
export const OverallAssessmentSchema = z.enum(['SATISFACTORY', 'UNSATISFACTORY']);

// Section A: Person ordering report
export const SectionASchema = z.object({
  client_name: z.string().min(1, 'Client name is required'),
  client_address: z.string().min(1, 'Client address is required'),
  purpose_of_report: z.string().min(1, 'Purpose is required'),
});

// Section B: Reason for report
export const SectionBSchema = z.object({
  reason: z.enum([
    'change_of_occupancy',
    'change_of_use',
    'periodic_inspection',
    'previous_inspection_recommendations',
    'other'
  ]),
  other_reason: z.string().optional(),
});

// Section C: Installation details
export const SectionCSchema = z.object({
  occupier: z.string().min(1, 'Occupier is required'),
  installation_address: z.string().min(1, 'Installation address is required'),
  type_of_installation: z.string().min(1, 'Installation type is required'),
  estimated_age: z.string().optional(),
});

// Section D: Extent and limitations
export const SectionDSchema = z.object({
  extent_of_inspection: z.string().min(1, 'Extent of inspection is required'),
  limitations: z.array(z.string()).default([]),
  percentage_inspected: z.number().min(0).max(100).optional(),
});

// Section E: Summary - CRITICAL: Overall assessment must be human-selected
export const SectionESchema = z.object({
  general_condition: z.string().min(1, 'General condition description required'),
  overall_assessment: OverallAssessmentSchema,
});

// Section F: Recommendations
export const RecommendationSchema = z.object({
  code: ClassificationCodeSchema, // HUMAN ASSERTION REQUIRED
  description: z.string().min(1, 'Description is required'),
  reference: z.string().optional(),
});

export const SectionFSchema = z.object({
  recommendations: z.array(RecommendationSchema).default([]),
});

// Section G: Declaration
export const SectionGSchema = z.object({
  inspector_name: z.string().min(1, 'Inspector name is required'),
  inspector_position: z.string().min(1, 'Position is required'),
  date_of_inspection: z.string().min(1, 'Date of inspection is required'),
  signature: z.string().min(1, 'Signature is required'),
  next_inspection_date: z.string().optional(),
});

// Section I: Supply characteristics
export const SectionISchema = z.object({
  supply_type: z.string().optional(),
  supply_parameters: z.object({
    voltage: z.number().optional(),
    frequency: z.number().optional(),
    prospective_fault_current: z.number().optional(),
    external_loop_impedance: z.number().optional(),
  }).optional(),
  earthing_arrangements: z.string().optional(),
});

// Section J: Installation particulars
export const SectionJSchema = z.object({
  means_of_earthing: z.string().optional(),
  main_protective_conductors: z.string().optional(),
  main_switch_rating: z.number().optional(),
  rcd_details: z.string().optional(),
});

// Evidence reference - REFERENCED not EMBEDDED
export const EvidenceRefSchema = z.object({
  id: z.string(),
  nice_ref: z.string(),
  description: z.string(),
  captured_at: z.string(),
});

// Section K: Observations - HUMAN WRITTEN ONLY
export const ObservationSchema = z.object({
  item: z.string().min(1, 'Item reference is required'),
  description: z.string().min(1, 'Observation description is required (human-written)'),
  classification: ClassificationCodeSchema, // HUMAN ASSERTION REQUIRED
  evidence_refs: z.array(EvidenceRefSchema).optional(),
});

export const SectionKSchema = z.object({
  observations: z.array(ObservationSchema).default([]),
});

// Circuit Details
export const CircuitDetailSchema = z.object({
  circuit_designation: z.string(),
  circuit_type: z.string(),
  live_conductors: z.string(),
  cpc_conductors: z.string(),
  overcurrent_device: z.string(),
  residual_current_device: z.string(),
});

// Test Results
export const TestResultSchema = z.object({
  circuit_designation: z.string(),
  continuity: z.number().optional(),
  insulation_resistance: z.number().optional(),
  polarity: z.string().optional(),
  earth_fault_loop_impedance: z.number().optional(),
  rcd_test: z.string().optional(),
});

// Inspection Schedule Item
export const InspectionScheduleItemSchema = z.object({
  checked: z.boolean().default(false),
  na: z.boolean().default(false),
  lim: z.boolean().default(false),
  notes: z.string().optional(),
});

// Complete EICR Schema
export const ECIRSchema = z.object({
  report_id: z.string().regex(/^EICR-\d{4}-\d{3}$/, 'Invalid report ID format'),
  version: z.string().default('1.0'),
  created_at: z.string().optional(),
  sections: z.object({
    section_a: SectionASchema,
    section_b: SectionBSchema,
    section_c: SectionCSchema,
    section_d: SectionDSchema,
    section_e: SectionESchema,
    section_f: SectionFSchema.optional(),
    section_g: SectionGSchema,
    section_h: z.object({}).optional(),
    section_i: SectionISchema.optional(),
    section_j: SectionJSchema.optional(),
    section_k: SectionKSchema.optional(),
  }),
  schedules: z.object({
    circuit_details: z.array(CircuitDetailSchema).optional(),
    test_results: z.array(TestResultSchema).optional(),
    inspection_schedule: z.record(InspectionScheduleItemSchema).optional(),
  }).optional(),
});

export type ECIRData = z.infer<typeof ECIRSchema>;
export type SectionAData = z.infer<typeof SectionASchema>;
export type SectionBData = z.infer<typeof SectionBSchema>;
export type SectionCData = z.infer<typeof SectionCSchema>;
export type SectionDData = z.infer<typeof SectionDSchema>;
export type SectionEData = z.infer<typeof SectionESchema>;
export type SectionFData = z.infer<typeof SectionFSchema>;
export type SectionGData = z.infer<typeof SectionGSchema>;
export type SectionIData = z.infer<typeof SectionISchema>;
export type SectionJData = z.infer<typeof SectionJSchema>;
export type SectionKData = z.infer<typeof SectionKSchema>;
export type ObservationData = z.infer<typeof ObservationSchema>;
export type RecommendationData = z.infer<typeof RecommendationSchema>;
export type CircuitDetailData = z.infer<typeof CircuitDetailSchema>;
export type TestResultData = z.infer<typeof TestResultSchema>;
