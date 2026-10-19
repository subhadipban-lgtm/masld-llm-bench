# Quarantined: MB-86xx archives scored against the mislabeled freeze-8 corpus

`scripts/build_mb86xx.py` read the GSE267032 TPM header with `header[1:]`.
That matrix's header lists only the 35 sample names (no gene-ID column), so
the slice dropped `Blood_patient_1` and paired every remaining label with the
preceding sample's column. All 20 items in the freeze-8 corpus therefore
carried the wrong patient's expression against the given grade.

These archives were produced by evaluating models on the corrupted prompts.
They are retained for audit only and MUST NOT be scored or cited. Re-evaluate
on the freeze-16 corpus (21 patients) before using MB-86xx results.

Detected 2026-10-19 while cross-checking sample counts against the independent
blood-cohort search report.
