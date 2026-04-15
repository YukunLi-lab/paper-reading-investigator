# Methodology Notes

## Recommended Extraction Architecture

1. Detect whether the PDF is born-digital or scanned.
2. If scanned, run OCR first.
3. Extract text and structure.
4. Analyze the paper with a Feynman-style workflow.
5. Produce a formal investigation report.
6. End with one headline-style title.

## OCR Strategy Recommendation

Recommended rule:
- First choice: use a structured PDF parser.
- Fallback: use OCR only when needed.

Rationale:
- Born-digital papers usually extract cleaner with direct parsing.
- Scanned papers need OCR for recoverable text.
- Tables, equations, captions, and affiliation blocks are sensitive to OCR noise.

## Practical Tooling Default

- Primary structured extraction path: Marker or parser pipeline.
- OCR fallback path: OCRmyPDF.
- Post-processing: clean OCR text and map sections to canonical paper structure.

## Version 1 Scope

- Input: one PDF.
- Support: born-digital + scanned PDFs.
- OCR: fallback only.
- Output: markdown investigation report.

Not in scope for v1:
- multi-paper comparison
- automatic web crawling of author pages
- automatic repository harvesting
- automatic diagram generation

## Final Engineering Advice

A. Keep OCR as fallback, not default.
B. Keep author/corresponding-author/affiliation extraction conservative.
C. Keep Feynman explanation and reproducibility assessment in a fixed output structure.
