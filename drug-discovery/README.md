# Drug-Discovery Extension — Natural-Product Pipeline for MASLD

Status: **design + smoke-tested** (2026-09-29). Extends MASLD-LLM from
"model that reads omics" toward "model-guided compound nomination", with
AlphaFold/Chai structures as the structural layer.

## 1 · Where structures plug in (and where they don't)

The MASLD-LLM + KG stack already nominates **targets**. Structures cannot
nominate targets; they act at two later stages only:

| Stage | Question | Tool for the job |
|---|---|---|
| Target nomination | "Which driver/suppressor in *this* patient's module?" | MASLD-LLM + masld_kg_v5 (already built) |
| Target tractability check | "Is the nominated protein structured/druggable?" | AlphaFold DB structures (local .pdb) |
| Compound nomination | "Which natural products bind it?" | NP library docking / Chai-1 co-folding |
| Personalisation | "Given patient A's profile, which target × compound wins?" | LLM reasoning over KG + affinity data |

**Chai-1 vs AlphaFold — division of labour:**
- **AlphaFold DB** (free, no compute): monomer structures for every human
  protein — 5 seed targets already downloaded. Use for tractability checks and
  as rigid receptors.
- **Chai-1** (chai-discovery/chai-lab, open-source weights): *complexes* —
  protein–ligand co-folding with predicted poses + confidence, no docking grid
  needed. The right tool for NP–target pairs at scale.
- AutoDock Vina (free) stays as the classical-docking fallback for
  reproducibility.

## 2 · What we already have (audited this session)

- **masld_kg_v5**: 21,191 drug nodes, 8,452 genes; 35k `targets`, 26k
  `interacts_with`, 3.2k fibrosis-module edges, driver/suppressor +
  personalization annotations — target nomination already lives in the KG.
- **BindingDB natural-product extract** (`Natural .xlsx`): 1,744 ligand–target
  rows with Ki/IC50 — but only ~4 unique NPs (quercetin, kaempferol,
  carvacrol derivative). A **seed**, not a library.
- **FerrDb ferroptosis inhibitors** (246 molecules with PubChem CIDs) — a ready
  246-compound NP-adjacent screening set.
- **PubChem properties** (10,650 compounds: SMILES, MW, XLogP, TPSA...) —
  physicochemical filters ready.
- **Trial outcomes** (resmetirom/semaglutide/lanifibranor/pioglitazone) —
  positive-control anchors for validation.

## 3 · The natural-product library (the missing piece)

The personalization KG tracks 5 seed targets (THRβ = resmetirom's target,
PPARα, GSK3β, LPA1, NCOA3). To screen NPs at meaningful scale:

| Library | Size | Access | Notes |
|---|---|---|---|
| **COCONUT** | ~400k NPs | free API/SMILES (verified reachable) | primary candidate |
| ZINC natural products subset | ~120k | free | good QED/Lipinski metadata |
| NPASS / SuperNatural-II | ~360k | free | alternative coverage |
| BindingDB full NP subset | ~90k | free | affinity-labelled (best training data) |

Minimum viable screen: **COCONUT filtered to MASLD-relevant chemical space**
(MW 250–600, LogP <= 5) -> ~50–150k candidates -> Chai-1 co-folding or Vina
docking against personalization targets -> rank.

## 4 · Pipeline (5 stages)

```
[1] TARGET NOMINATION (done)
    MASLD-LLM scoring + KG driver/suppressor + personalization_status
        |
[2] STRUCTURE LAYER (seeded)
    AlphaFold DB monomers (5 targets on disk; batch = 1 script)
    -> tractability: pLDDT in pocket, pocket volume
        |
[3] NP LIBRARY PREP (needs COCONUT pull, ~2-6 GB)
    COCONUT SMILES -> RDKit filters (Lipinski-ish, NP-likeness) -> 3D conformers
        |
[4] SCREENING (Colab Pro+, the GPU part)
    Option A: Chai-1 co-folding top ~10k NP x target pairs
    Option B: AutoDock Vina docking, receptor = AF structure
              (start with 5k compounds, not 50k)
        |
[5] LLM INTEGRATION + VALIDATION
    Affinity data -> KG edges -> MB-95xx patient-profile -> compound tasks
    Positive controls: resmetirom<->THRbeta, pioglitazone<->PPARa must rank high
    Wet-lab hand-off: top-20 ranked NPs with poses + SMILES
```

## 5 · Compute reality

| Run | Where | Cost |
|---|---|---|
| AlphaFold DB batch (any target list) | laptop | free, ~1 min/target |
| COCONUT download + RDKit filtering | laptop (2-6 GB) | free |
| Vina docking 5k cmpd x 5 targets | Colab Pro/Pro+ | ~2-4 weeks CU |
| Chai-1 co-folding 10k pairs | Colab Pro+ A100 | ~10-20 CU |
| Wet-lab validation | lab | out of computational scope |

## 6 · Honest caveats

- **Docking scores are weak evidence.** Rankings, not truth. The paper framing
  must stay "computational nomination + positive-control validation"; claiming
  therapeutic efficacy would be indefensible.
- **Chai-1 confidence is calibrated for pose recovery**, not absolute affinity;
  combine with BindingDB Ki/IC50 wherever available.
- **Personalised-medicine claims need more than a KG.** The personalization
  annotations are target-level, not patient-level trials — frame as
  "patient-stratified target nomination", not "personalised drugs".
- NP libraries have high assay-interference rates (PAINS, aggregators) —
  filter before believing any ranking.

## 7 · Seed structures on disk (2026-09-29)

| File | Protein | Role |
|---|---|---|
| AF-P10828-F1-model_v6.pdb | Thyroid hormone receptor beta (THRβ) | resmetirom's target — positive control |
| AF-P37231-F1-model_v6.pdb | PPARα | pioglitazone/fibrate axis |
| AF-P49841-F1-model_v6.pdb | GSK3β | metabolic/fibrotic kinase |
| AF-Q9NPH0-F1-model_v6.pdb | LPA1 (LYPLA1) | lysophosphatidic-acid signalling |
| AF-O15164-F1-model_v6.pdb | NCOA3 (SRC-3) | transcription co-activator, KG-nominated |
