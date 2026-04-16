---
name: paper-reading-investigator
description: Read an academic paper from an uploaded PDF, run OCR when needed, extract metadata and core claims, explain the work using the Feynman technique, assess reproducibility and limitations, and generate a formal investigation report. Use this skill when the user uploads or references a research paper PDF and wants a deep, structured understanding rather than a short summary.
---

# Paper Reading Investigator Skill

## Purpose

This skill reads an academic paper from a PDF and produces a rigorous investigation report.

The skill must:
- detect whether the PDF is text-based or scanned
- run OCR if the PDF is scanned or poorly extractable
- extract the paper structure and metadata
- identify authors and affiliations with conservative mapping
- extract dataset/model/metric/hardware entities
- index table and equation signals
- map figure/table citation mentions to local evidence contexts
- explain the work using the Feynman technique
- extend the explanation into implementation and reproduction guidance
- align major claims to supporting evidence sentences
- identify weaknesses, limitations, missing details, and risks
- generate a concise headline title
- produce a final formal report in a consistent format
- optionally generate a group-meeting briefing deck
- optionally compare multiple papers side by side

## Inputs

Expected inputs:
- one PDF file path, or
- one uploaded PDF selected by the user

Optional user preferences:
- target audience level: beginner / technical / expert
- focus area: theory / implementation / reproduction / critique
- output style: concise / standard / detailed

If the user does not specify preferences, default to:
- audience: technical but broadly understandable
- focus: balanced
- output style: detailed

## Required workflow

Follow these steps in order.

### Step 1: Validate the input
1. Confirm that the file exists and is a PDF.
2. Create a working directory for outputs.
3. Preserve the original file unchanged.

### Step 2: Determine the extraction strategy
1. Inspect the PDF to determine whether it is:
   - born-digital text PDF
   - scanned/image PDF
   - mixed PDF
   - badly extractable PDF
2. Prefer direct structured extraction for born-digital PDFs.
3. Run OCR for scanned or badly extractable PDFs.
4. If extraction quality is low, explicitly say so in the final report.

### Step 3: OCR and text extraction
Preferred pipeline:
1. Try structured extraction first.
2. If text is missing, corrupted, sparse, or clearly image-based:
   - run OCR
   - generate a searchable OCR PDF or extracted text
3. Save:
   - raw extracted text
   - cleaned text
   - sectioned text
   - extracted metadata
4. Preserve page references whenever possible.

### Step 4: Recover the paper structure
Identify and recover:
- title
- authors
- affiliations
- corresponding author information if present
- abstract
- keywords if present
- introduction
- related work
- method / approach
- experiments
- results
- discussion
- limitations
- conclusion
- references
- appendix or supplementary notes if present

If the section titles differ, map them into the closest standard paper sections.

### Step 5: Extract factual metadata
Extract the following fields as faithfully as possible:
- paper title
- author list
- affiliations / institutions
- corresponding author name
- corresponding author email if present
- venue / journal / arXiv / publisher if visible
- publication year if visible
- DOI if visible
- GitHub / project page / code link if visible
- dataset names
- benchmark names
- model names
- hardware details if visible
- main equations, algorithms, or pipelines
- key tables and figures
- extracted equation snippets with tags where possible

Do not invent metadata that is not explicitly present.
If a field is uncertain, mark it as "Not clearly stated in the paper."

### Step 6: Build a faithful technical understanding
Produce a technical understanding of:
- the research question
- the motivation
- the central hypothesis
- the proposed method
- the experimental setup
- the key results
- the claimed contributions

For every major claim:
1. state the claim
2. point to the supporting evidence from the paper
3. note whether the support is strong, partial, or weak

### Step 7: Apply the Feynman learning method
Use the Feynman technique explicitly.

For each core concept:
1. Explain it in plain English as if teaching a smart beginner.
2. Remove jargon where possible.
3. Rebuild the explanation step by step.
4. Add one intuitive analogy where useful.
5. State what remains unclear or underspecified.
6. Explain why the concept matters in the context of the paper.

The Feynman section must include:
- "Explain it simply"
- "What problem it solves"
- "How it works step by step"
- "Where confusion usually appears"
- "What I still cannot verify from the paper"

### Step 8: Extend to implementation and reproduction
Create a practical reproduction section.

Include:
- prerequisites
- dependencies
- expected hardware
- expected software environment
- data requirements
- training or inference workflow
- evaluation procedure
- likely implementation steps
- hidden assumptions
- unclear hyperparameters
- missing ablations or missing setup details
- reproducibility risk rating: Low / Medium / High

If the paper lacks enough detail for exact reproduction, say so directly and explain what is missing.

### Step 9: Critique the paper
Assess:
- strengths
- limitations
- possible failure modes
- methodological blind spots
- dataset bias or evaluation bias
- missing baselines
- weak comparisons
- overclaiming risk
- external validity
- engineering practicality
- novelty versus incremental contribution

Be fair and evidence-based.
Do not criticize without grounding the critique in the paper.

### Step 10: Generate a headline title
Create a short title that captures the paper's essence and your assessment.

Rules:
- 8 to 18 words
- clear, sharp, high signal
- must reflect the actual contribution
- may include a cautious evaluative phrase if warranted

### Step 11: Produce the final report
Write the final answer as a formal investigation report using the report template in `templates/paper_investigation_report.md`.

### Step 12: Optional advanced outputs
When requested, also generate:
- a claim-evidence alignment matrix (`claim_evidence_alignment.json`)
- a group meeting brief (`meeting_brief.md`)
- a multi-paper comparison report (`comparison_report.md`)

## Metadata extraction rules for authors and affiliations

- Prefer the title block, author block, footnotes, and first-page affiliation lines.
- If multiple affiliations exist, preserve author-to-affiliation mapping where possible.
- If the corresponding author is marked with symbols such as `*`, `+`, or an email footnote, report it.
- If there is only an email and no explicit corresponding-author label, report the email but do not claim corresponding authorship unless clearly indicated.
- If affiliation mapping is ambiguous, say: "Affiliation mapping is partially ambiguous in the source PDF."

## Feynman analysis policy

For each of the top 3 to 7 core concepts:
1. Name the concept.
2. Explain it in simple language without assuming specialist background.
3. Restate it using one analogy.
4. Reconstruct the formal meaning using the paper's terminology.
5. Identify the gap between the simple explanation and the formal mechanism.
6. State what the paper proves, what it suggests, and what it does not prove.
7. State one practical implication for implementation or reproduction.

## Output requirements

The final output must be a polished report with the following top-level sections:

1. Headline Assessment
2. Paper Identity
3. Executive Summary
4. Core Concepts Explained with the Feynman Method
5. Method and Experimental Logic
6. Reproduction Plan
7. Defects, Limitations, and Risks
8. Author and Affiliation Information
9. Final Verdict
10. Confidence and Extraction Notes

## Quality bar

Before finalizing, verify:
- names and affiliations are extracted from the paper, not guessed
- the explanation is simpler than the original wording
- the reproduction plan is actionable
- every critique is tied to the paper content
- uncertainty is made explicit
- no unsupported claims are introduced

## Operational rules

- Prefer faithfulness over fluency.
- Prefer direct evidence over speculation.
- If OCR output is noisy, acknowledge extraction risk.
- If the corresponding author is not explicitly identifiable, do not infer one.
- If the affiliations are ambiguous, report them conservatively.
- If tables or equations are critical and extraction is partial, mention that the report may miss fine-grained numerical detail.

## Suggested command usage

Typical script flow:
1. `python scripts/detect_pdf_type.py <pdf_path>`
2. `python scripts/run_ocr.py <pdf_path> <output_dir>` if needed
3. `python scripts/extract_paper.py <input_pdf_or_ocr_pdf> <output_dir>`
4. `python scripts/analyze_paper.py <output_dir> --enable-llm-alignment` (optional)
5. `python scripts/build_report.py <output_dir> --with-appendix`
6. `python scripts/build_meeting_brief.py <output_dir>` (optional)
7. `python scripts/compare_papers.py <paper_output_dir_a> <paper_output_dir_b> --output-dir <compare_dir>` (optional)

## Success condition

This skill succeeds only if it returns:
- a faithful metadata block
- a genuinely simplified explanation
- a realistic reproduction plan
- a grounded critique
- a final formal report
