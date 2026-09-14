# Phase 2 submission plan (CS23E02, due 26 to 28 September 2026)

Written 13 September. Three deliverables, and the arena is the new material in
all three.

| deliverable | due | what |
|---|---|---|
| PPT, 4 slides, and a live demo | demo slot 21 to 28 Sept | Title; Objective; Overall architecture; Module design with snapshots and results. Bring soft copies of the base papers. |
| Full paper, Springer format | 26 Sept, MS Teams | The phase-1 IEEE paper rewritten: updated results, architecture and module diagrams, intermediate snapshots to final output, result analysis in tables and charts. |
| Report (Word, Springer format) and code | 28 Sept, MS Teams | Title, Abstract, Introduction and problem statement, Literature survey with critical analysis and the gap, Methodology with architecture and module diagrams, Result analysis, Performance metrics with diagram, Charts and tables with observations, Conclusion, References. |

Marks: implementation 50, paper 50.

## What changes from phase 1

The phase-1 paper (`docs/NashForge_IEEE.docx`, 4,088 words, 15 August) quotes
results that the project has since withdrawn or superseded: the +370 BB/100
edges were measured against a 4,000-iteration solver, and `NEXT.md` records the
three claims the panel upgrade overturned. Every number in the phase-2 paper
comes from the native panel of 11 September (`results/comparison/phase4_native.json`)
and later. Sections that survive as written: the introduction, the related work,
the engine and abstraction description. Sections rewritten: architecture (the
C++ core is new), results, discussion, comparison, conclusion.

## The arena, as the paper's contribution

Phase 1 measured three learning families against each other and against fixed
baselines. Phase 2 adds what none of those can give: **rated play against
other developers' bots on a public ladder**, with every hand recorded. That is
the strongest possible "analysis of results" section, because it produced a
diagnosis and a fix inside one day:

1. **Deployment** (`chipzen/`): the bridge from a live protocol to the solver's
   abstraction, the depth ladder, the companion for off-tree nodes. Module
   diagram: arena protocol, bridge, ladder, solver lookup, logger.
2. **Results**: matches, wins, chips by opponent and by stack depth
   (`scripts/chipzen_review.py`), the Glicko rating, and the season standings.
3. **Analysis**: 46 matches on 13 September: +121,000 chips below 70 big blinds
   and −43,000 above, eleven companion shoves losing −61,000, nine of eleven
   showdowns lost to the one opponent that re-raises. The gap: a one-raise
   betting abstraction against opponents who re-raise. That is the literature
   survey's gap, found in our own data.
4. **The fix and its measurement**: the raise-cap-2 solver as the main solver at
   depth, texture-aware buckets, the 200-sample estimator (+5.9 ± 1.9 BB/100,
   measured), and the opponent profile. The season's second half, played on the
   new set, against the first half on the old one, is the before-and-after
   table. The season ends 20 September, six days before the paper is due.

Performance metrics for the rubric: BB/100 with standard errors (internal),
mbb/hand against Slumbot, chips and win rate in the arena, decision latency,
lookup miss rate, training throughput (ms/iteration, the 32.5x port).

## Revised 13 September, 22:15: everything by Thursday 18 September

The brief (`docs/course/assignment-brief.pdf`) gives 21 to 28 September, but
the demo slot and submission are Thursday the 18th. Four working days, and the
season's first two evening rounds (Tuesday and Wednesday, from 23:30 IST) fall
inside them, which is enough for the arena section: today's 62 matches on the
old solver set, and two rated rounds on the new one, give the before-and-after.

| day | work | done by end of day |
|---|---|---|
| Mon 14 | Figures and diagrams from the repository: architecture with the C++ core and the arena path; `chipzen/` module diagram; charts (panel, bucket sweep, speed history, arena chips by depth and by opponent, the 200-sample head-to-head). `scripts/make_springer.py` built from `make_docx.py`. Paper text drafted: abstract, introduction, survey with the gap, methodology, results as of today. | LNCS draft with every section, figures placed, today's results in |
| Tue 15 | Text finished and read through. `scripts/make_slides.py`: the four slides. Exhibition matches on the new solver set in the morning; the bot on it for the first round at 23:30. | Paper v1, slides v1 |
| Wed 16 | Tuesday's round into the results (the before-and-after table, standings). Demo rehearsed: bot in the lobby, `chipzen-progress.sh --watch`, a live house-bot match, the review. Code packaged: the public repository at a tagged commit, plus the arena logs as a zip. | Paper v2, slides v2, demo script |
| Thu 18 | Wednesday's round folded in first thing. Submit; demo. | |

The report and the paper are one document: the LNCS paper carries the rubric's
section names (Problem Statement inside the Introduction, Literature Survey
with the gap, Methodology with both diagrams, Result Analysis with metrics,
Charts and Tables with observations, Conclusion, References).

## Order of work (original, superseded by the table above)

1. 14 to 20 Sept: play the season; keep `results/chipzen/` complete; collect the
   review tables after each round.
2. 21 Sept: figures. Architecture diagram updated with the native core and the
   arena path; module diagram for `chipzen/`; charts: chips by depth, per-opponent
   record, before-and-after the fix, the 200-sample head-to-head.
3. 22 to 24 Sept: the paper text, Springer style (`scripts/make_springer.py`,
   from `scripts/make_docx.py`: numbered sections, "Fig. 1." and "Table 1."
   captions, abstract and keywords, references). The report is the same document
   with the rubric's section names.
4. 25 Sept: the four slides and a rehearsed demo: the bot in the lobby,
   `tools/chipzen-progress.sh --watch`, a house-bot match live, the review.
5. 26 Sept: paper in; 28 Sept: report and code in.

## Decided 13 September

- **Format: Springer LNCS.** Title, authors and affiliation, abstract, keywords,
  numbered sections, "Fig. 1." and "Table 1." captions, Springer-style
  references.
- **Base papers**, in `docs/base-papers/` (local only, not in git):
  1. Lanctot, Waugh, Zinkevich, Bowling, *Monte Carlo sampling for regret
     minimization in extensive games*, NIPS 2009. The solver is their
     external-sampling MCCFR; the contribution is what happens when it is put
     under a coarse abstraction and measured.
  2. Johanson, Burch, Valenzano, Bowling, *Evaluating state-space abstractions
     in extensive-form games*, AAMAS 2013. The abstraction findings (six buckets
     at every budget, the estimator-noise result, the board texture) sit on it.
  3. Ganzfried and Sandholm, *Action translation in extensive-form games with
     large action spaces*, IJCAI 2013. The arena bridge is their pseudo-harmonic
     mapping, and the deployment section is what it looks like against live
     opponents.
  Libratus (Brown and Sandholm 2018) is the context paper for the introduction,
  not a base paper: nothing here is built on it.
- `python-pptx` 1.0.2 is installed in the venv; the slides build from the
  repository.
