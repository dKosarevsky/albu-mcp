# AlbumentationsX MCP Preview Report

- Baseline run: baseline
- Quality profile: classification
- Candidates: 2
- Best candidate: candidate-a

## Review Summary

- Recommended action: export_pipeline
- Best candidate: candidate-a (score 100.0, risk low).
- Feedback trail: 0 concrete record(s), 0 accepted.
- Decisions: 1 recorded, 1 accepted.
- Tuning sessions: 0 linked.
- Guidance: Best dataset candidate is candidate-a.; Best candidate is candidate-a with score 100.0.; The best candidate is marked export-ready.

## Contact Sheets

### Baseline

- ![contact sheet](<FIXTURE_ROOT>/images/baseline-contact.png)
- <FIXTURE_ROOT>/images/baseline-contact.png

### Candidates

| Rank | Candidate | Score | Risk | Export Ready | Next Tool | Feedback Tags | Contact Sheets |
| ---: | --- | ---: | --- | --- | --- | --- | --- |
| 1 | candidate-a | 100.0 | low | true | export_pipeline | none | ![contact sheet](<FIXTURE_ROOT>/images/candidate-a-contact.png)<br><FIXTURE_ROOT>/images/candidate-a-contact.png |
| 2 | candidate-b | 85.0 | medium | false | adjust_pipeline | too_noisy:high | ![contact sheet](<FIXTURE_ROOT>/images/candidate-b-contact.png)<br><FIXTURE_ROOT>/images/candidate-b-contact.png |

## Dataset Metrics

| Metric | Candidates | Min | Max | Mean |
| --- | ---: | ---: | ---: | ---: |
| brightness_mean | 2 | 78.0000 | 128.0000 | 103.0000 |
| clipping_fraction | 2 | 0.0200 | 0.1800 | 0.1000 |

## Finding Counts

| Severity | Code | Count |
| --- | --- | ---: |
| medium | candidate_high_clipping | 1 |

## Tuning Decisions

| Decision | Candidate | Accepted | Score | Risk | Notes |
| --- | --- | --- | ---: | --- | --- |
| decision-a | candidate-a | true | 100.0 | low | accepted snapshot fixture |

## Interactive Tuning Sessions

No interactive tuning sessions matched this report.

## Concrete Preview Feedback

No concrete preview feedback matched this report.
