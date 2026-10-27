# Paper 1 — Leakage-Aware CTI NER Evaluation

This directory contains the first research-paper draft derived from verified ACTIT experiment artifacts.

## Files

- `main.tex`: complete English IEEE conference-style manuscript.
- `references.bib`: BibTeX references.
- `ARABIC_SUMMARY.md`: Arabic explanation of the paper and its results.
- `EVIDENCE_MAP.md`: traceability map from manuscript claims to project artifacts.
- `SUBMISSION_CHECKLIST.md`: items that must be completed before submission.
- `AUTHOR_METADATA.md`: confirmed Arabic names and provisional English transliterations.

## Build

With a TeX distribution that includes `IEEEtran`:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Alternatively, upload `main.tex` and `references.bib` to Overleaf and select pdfLaTeX.

## Status

The manuscript is a professional evidence-based draft, not a submission-ready final. The three student names, university, and supervisor acknowledgment have been added. The English transliterations, email addresses, corresponding-author designation, target venue, and public artifact URL must still be confirmed. The manuscript explicitly avoids a state-of-the-art claim and discloses the single-seed and artifact-retention limitations.

The intended final location is `documentation/final/paper_1_leakage_aware_ner/`. It could not be written during this run because the existing `documentation/working` and `documentation/final` directories are owned by another account and are not writable by `alaaldeen`.
