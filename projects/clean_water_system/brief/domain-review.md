# Domain review — Clean-water system

**Review date:** 2026-07-30  
**Reviewer:** AI source-and-process review; independent drinking-water
professional review remains recommended before public sign-off.

## Claims checked

1. Utilities often use coagulation, flocculation, sedimentation, filtration,
   and disinfection as a series of treatment steps.
2. Coagulation destabilizes fine-particle charge and flocculation uses gentle
   mixing to grow larger floc.
3. Sedimentation separates heavier floc; filtration removes remaining particles
   and contributes to germ reduction.
4. Disinfection inactivates susceptible pathogens but does not make every
   possible contaminant interchangeable.
5. Utilities select treatment according to source-water conditions and safety
   requirements.
6. Turbidity instruments and SCADA data support monitoring, but data quality and
   verification matter.

## Evidence

- CDC, *How Water Treatment Works*, conventional sequence, stage purposes,
  utility variation, and community delivery:
  https://www.cdc.gov/drinking-water/about/how-water-treatment-works.html
- US EPA, *Generating High-Quality Turbidity Data in Drinking Water Treatment
  Plants*, turbidimeter/SCADA monitoring and data-quality practice:
  https://www.epa.gov/sdwa/generating-high-quality-turbidity-data-drinking-water-treatment-plants-support-system
- US EPA, *Drinking Water Treatment Plant Residuals Management Technical
  Report*, conventional filtration and source-dependent process variation:
  https://www.epa.gov/sites/default/files/2015-11/documents/dw-treatment-residuals-mgmt-tech-report-sept-2011.pdf

## Deterministic checks

- The stage dataset contains eight unique, consecutively numbered records.
- Conventional plant processes remain ordered: coagulation, flocculation,
  sedimentation, filtration, disinfection.
- Every stage and monitoring state has a stable semantic identifier.
- The response sequence contains sense, verify, respond, and confirm.

## Assumptions and simplifications

- Intake screening and source protection are contextual additions around the
  conventional plant sequence.
- Storage, pumps, and the pipe network are schematic rather than hydraulic.
- “Turbidity changes” is a generic disturbance, not an alarm threshold.
- Dissolved-chemical treatment is acknowledged but deliberately not modeled.
- No operating values or plant-specific recommendations are supplied.

## Unresolved review items

- Obtain independent water-treatment/public-health review.
- The full-tape proof is not the final 1920×1080 website master.
