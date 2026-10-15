# MASLD-LLM · The aging–ferroptosis axis integration
*(added 2026-10-15; source papers in Drive `wim MASLD modified/MASLD-Aging Ferroptosis axis/`)*

## The papers (what they establish)

1. **Du K, Wang L, Jun JH, … Diehl AM. "Aging promotes metabolic
   dysfunction-associated steatotic liver disease by inducing ferroptotic
   stress." Nature Aging 4:949–968 (2024).** DOI 10.1038/s43587-024-00652-w.
   - Aging hepatocytes accumulate ferroptotic stress; old mice on CDA-HFD
     develop worse steatohepatitis/fibrosis, fully reverted by Ferrostatin-1
     (Fer1) — ferroptosis is causal, not correlative.
   - "Ferrosenescence": ferroptotic stress drives senescence markers
     (p21/CDKN1A, p16/CDKN2A, β-gal, γH2AX); Fer1 reverts them.
   - **Human validation: GSE213623 (Duke MASLD cohort, N=368)** — 69 controls
     + 299 biopsy-proven MASLD staged F0F1 (97) / F2 (107) / F3F4 (95).
   - **AHGS** (aging hepatocyte gene signature): 496 DEGs (old vs young mouse
     hepatocytes, FC>3); in Duke livers it tracks BMI, age (in MASLD), AST,
     FIB-4, albumin (inverse), and fibrosis stage progressively.
   - **Ferroptosis marker score: 9 FerrDb V2 genes** — FTH1, GPX4, CHAC1,
     HSPB1, NFE2L2, PTGS2, SLC40A1, TF, TFRC. Directions in human fibrosis
     progression: **ACSL4 ↑, SLC7A11 ↑, PTGS2 ↑, FSP1/AIFM2 ↑ (adaptive);
     GPX4 ↓, GCH1 ↓ (defenses exhausted)**. Plus a 128-gene iron-response
     signature (IAS).
   - Companion datasets: GSE262457 (old-vs-young CDA-HFD bulk RNA-seq),
     GSE262939 (snRNA-seq), GSE174748 (human snRNA-seq), GSE33814 (Japanese),
     GSE135251 (European), GSE167523, GSE132042, E-MTAB-2502, GSE50244.
2. **Jun JH, … "Hepatocyte hedgehog signaling controls ferroptosis to
   alleviate aging-related organ dysfunction."** Hh(+) hepatocytes resist
   ferroptosis; Smo loss → vulnerability. Accessions GSE213183 (mouse scRNA),
   GSE330266 (human MASLD scRNA).
3. **Jun JH, … Diehl AM. "The senescence-associated secretome of
   Hedgehog-deficient hepatocytes drives MASLD progression." J Clin Invest
   (2024/25).** Smo-deficient hepatocytes become senescent; their SASP
   secretome (sera + conditioned medium) perpetuates progression. New data:
   GSE273523 (Smo-KO vs control CDA-HFD bulk RNA-seq).
4. **Ying K, Tyshkovskiy A, … Gladyshev DE. "Autonomous AI agents discover
   aging interventions from millions of molecular profiles."** LLM agents
   mining GEO for geroprotectors — the AI-for-aging lineage our benchmark
   recipe (LongevityBench) belongs to; cite as positioning, not data.
5. *(Cellular senescence in human liver aging/cancer review — PDF is
   image-only; needs OCR before use.)*

## Why this matters for the program

The axis lands on all three open fronts at once:
- **C3 (novel tasks)**: mechanism-grounded task families no generalist
  benchmark has (ferroptosis-marker direction with stage, Fer1 reversion,
  SASP membership).
- **Track D (geometry stability)**: GSE213623 adds ~299 staged human livers
  to the train pool (466 → ~765) — the direct fix for the ±0.15 module
  instability, with a published signature (AHGS) to anchor interpretation.
- **C4 (regime split)**: mechanistic modules (FSS/AHGS) make the geometric
  layer interpretable, not just performant.

## Integration plan (concrete)

### 1. Immediate data acquisition (public)
- [x] GSE267032 (WBC blood-proxy; done 2026-10-15)
- [ ] **GSE213623** — Duke N=368 staged cohort (highest priority)
- [ ] GSE262457, GSE273523 — mouse perturbation panels (age × Fer1; Smo-KO)
- [ ] GSE135251 (European staged validation), GSE330266 (human scRNA)

### 2. Mechanistic module layer (extends MB-40xx)
Add engineered, literature-anchored modules alongside the co-expression
modules (fitted train-side, frozen-test only embedded):
- **FSS** — ferroptosis stress score from the 9 FerrDb genes, signed per the
  Nature Aging directions (ACSL4/SLC7A11/PTGS2/FSP1 vs GPX4/GCH1).
- **AGING** — senescence panel: CDKN1A, CDKN2A, GLB1, MKI67 (inverse), core
  SASP (IL6, CCL2, CXCL8/CXCL1-3, SERPINE1).
- **IRON** — iron handling: TF, TFRC, FTH1, FTL, SLC40A1, HAMP.
New task ids: MB-9601/9602/9605 on the module layer (registry/profile
update), same split discipline as MB-40xx.

### 3. New task families
- **MB-96xx (axis reasoning, existing corpora — no new data needed)**:
  - 9601: given a gene panel, is the ferroptosis-stress profile consistent
    with advanced fibrosis? (yes/no)
  - 9602: senescence-burden multiclass from module activities
  - 9605: FSS regression vs fibrosis stage
- **MB-97xx (perturbation transfer, mouse panels)**: "old CDA-HFD ± Fer1" —
  direction-of-change and reversion tasks (does the model know Fer1 reverts
  aging/ferroptosis transcripts?). Grounds the F5-4 drug-perturbation family
  in a published causal result; same builder pattern as MB-70xx.
- **MB-98xx (Duke cohort C3 family)**: fibrosis staging + AHGS-enrichment
  tasks on GSE213623; train-side (test freeze untouched).
- **Knowledge corpora**: FerrDb V2 / MSigDB ferroptosis + senescence +
  SASP gene sets → MB-61xx-style membership tasks.

### 4. Drug-arm tie-in
Ferroptosis inhibitors are a druggable class: screen the NP library for
anti-ferroptotic natural products (quercetin is a known ferroptosis
inhibitor — one of our four seed NPs). Re-scopes the Vina/COCONUT arm from
"generic docking" to "axis-targeted nomination".

### 5. Narrative (paper)
New sub-claim under C3: **mechanistic-axis grounding** — "the benchmark
tests whether models encode the aging–ferroptosis axis, not just
correlative staging." Cite Du et al. (Nat Aging 2024), Jun et al. (JCI),
Ying et al. (AI agents) for lineage. Honest framing stays: mechanistic
scores are literature-anchored hypotheses to TEST, not assumed truths.

## Guardrails
- Test side (EPoS) stays frozen; GSE213623 is train/validation only.
- Module/score definitions fixed BEFORE any eval (freeze discipline).
- Species split enforced (mouse perturbation corpora never mixed into human
  clinical tasks).
