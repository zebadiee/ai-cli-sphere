# Electrical Installation Condition Report (EICR)

**Report Number:** {{report_id}}  
**Date of Inspection:** {{date_of_inspection}}

---

## Section A: Details of the Person Ordering the Report

**Client Name:** {{client_name}}  
**Client Address:** {{client_address}}  
**Purpose of Report:** {{purpose_of_report}}

---

## Section B: Reason for Producing this Report

**Reason:** {{reason}}  
{{#if other_reason}}**Other Reason:** {{other_reason}}{{/if}}

---

## Section C: Details of the Installation

**Occupier:** {{occupier}}  
**Installation Address:** {{installation_address}}  
**Type of Installation:** {{type_of_installation}}  
**Estimated Age:** {{estimated_age}}

---

## Section D: Extent and Limitations of the Inspection

**Extent of Inspection:** {{extent_of_inspection}}  
**Percentage Inspected:** {{percentage_inspected}}%

**Limitations:**
{{#each limitations}}
- {{this}}
{{/each}}

---

## Section E: Summary of the Condition of the Installation

**General Condition:**  
{{general_condition}}

**Overall Assessment:** {{overall_assessment}}

*Note: An UNSATISFACTORY assessment indicates that dangerous (C1) and/or potentially dangerous (C2) conditions have been identified.*

---

## Section F: Recommendations

{{#each recommendations}}
**{{code}}** - {{description}} (Ref: {{reference}})
{{/each}}

---

## Section G: Declaration

I/We certify that the installation has been inspected and tested and that the results are recorded in this report.

**Inspector Name:** {{inspector_name}}  
**Position:** {{inspector_position}}  
**Date:** {{date_of_inspection}}  
**Signature:** {{signature}}

**Next Inspection Recommended:** {{next_inspection_date}}

---

## Section H: Schedule of Items Inspected

See attached Inspection Schedule

---

## Section I: Supply Characteristics and Earthing Arrangements

**Supply Type:** {{supply_type}}  
**Voltage:** {{voltage}}V  
**Frequency:** {{frequency}}Hz  
**Prospective Fault Current:** {{prospective_fault_current}}kA  
**External Loop Impedance:** {{external_loop_impedance}}Ω

**Earthing Arrangements:** {{earthing_arrangements}}

---

## Section J: Particulars of the Installation

**Means of Earthing:** {{means_of_earthing}}  
**Main Protective Conductors:** {{main_protective_conductors}}  
**Main Switch Rating:** {{main_switch_rating}}A  
**RCD Details:** {{rcd_details}}

---

## Section K: Observations and Recommendations

{{#each observations}}
**Item {{item}}**: {{description}}  
**Classification:** {{classification}}

{{#if evidence_refs}}
**Evidence:**
{{#each evidence_refs}}
- {{id}} (NICE: {{nice_ref}}) - {{description}} - Captured: {{captured_at}}
{{/each}}
{{/if}}

---
{{/each}}

---

## Schedules

### Schedule of Circuit Details

See attached Circuit Details Schedule

### Schedule of Test Results

See attached Test Results Schedule

### Condition Report Inspection Schedule

See attached Inspection Schedule

---

**End of Report**

---

*This is a human-readable template. Critical fields (C1/C2/C3/FI codes, SATISFACTORY/UNSATISFACTORY) require explicit human assertion.*
