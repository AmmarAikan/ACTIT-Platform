# ACTIT Paper 2 — Evidence-Constrained CTI

Professional IEEE-style editable manuscript about observable/indicator separation, bounded relationship extraction, secure multi-source collection, and the ACTIT production quality case study.

## Files

- `main.tex`: complete editable English paper with four TikZ diagrams.
- `references.bib`: bibliography.
- `ARABIC_SUMMARY.md`: Arabic summary.
- `EVIDENCE_MAP.md`: traceability from claims to project artifacts.
- `EDIT_POINTS_AR.md`: short manual-edit checklist.
- `AUTHOR_METADATA.md`: authors and supervisor metadata.

## Build

Upload `main.tex` and `references.bib` to Overleaf, or run:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The manuscript is venue-neutral. It is scientifically complete as a first draft, but author transliterations, emails, target venue, and permanent artifact URL require final verification. Completing the planned human evaluation would materially strengthen publication readiness.
