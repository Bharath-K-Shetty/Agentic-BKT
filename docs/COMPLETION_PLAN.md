# HOMIE completion and research readiness

Reviewed 8 October 2026. Scope: the DeFi decision-learning prototype and its
public-data knowledge-tracing experiments. This is not a smart-contract auditing
tool. The current work is a functioning prototype with exploratory results;
it is not ready to submit as a paper demonstrating a new method or learning benefit.

Implementation update: simulator v2 now adds five diagnostics and a second distinct
practice item per skill. Adaptive order responds to diagnostic and practice
answers; the fixed arm receives the same items in fixed order. Legacy v1 sessions
retain their original sequence. Session-level exports now include zero-answer
assignments and bank-specific completion counts. The defect below records the
original review finding; content validation and the learner study remain pending.

## Evidence at this review

- After the v2 repair, full automated suite: **74 passed**, with four dependency
  deprecation warnings. Live HTTP smoke covered all 20 tasks; frontend JavaScript
  syntax passed. The original pre-repair review had 70 passing tests, showing why
  test count alone does not establish study validity.
- Local database: two quiz sessions and five quiz answers; one nonconsenting
  simulator session and zero simulator answers. There is no completed learner
  study supporting a HOMIE learning-effect claim.
- The latest EdNet item-control experiment gives AUC 0.6811 for item/skill/history
  and 0.6815 after adding timing/revisions. The paired learner-bootstrap interval
  for the difference includes zero. Behavioral-feature benefit is unestablished.
- Public English-learning data supports evaluation of prediction methods, not
  evidence that HOMIE teaches DeFi or prevents financial losses.
- The existing manuscript describes the earlier conversational Solana agent,
  including execution and live risk-analysis claims. It does not report the
  current study and must not be submitted in that form.

## First priority: repair the study before recruiting

**The v1 simulator's adaptive and fixed conditions produced identical
practice orders.** There was one practice scenario per skill. After answering it,
that skill has no remaining practice scenario; every available skill still has
the same initial BKT probability. Both policies therefore break ties by skill ID.
An exhaustive temporary-database check of all 32 binary practice-answer patterns
produced the same order in both arms for every pattern. This finding applies to
the simulator, not the separate quiz bank.

Readiness checklist before any adaptive-versus-fixed learner study:

1. **Implemented in v2:** a diagnostic phase and multiple distinct practice
   opportunities per skill. Adaptation changes order, with equal item exposure
   between arms. Transfer answers never choose practice; elapsed time is observed,
   not held constant.
2. **Verified in v2:** different diagnostic histories change adaptive order,
   fixed order stays fixed, and the arms can receive different orders. Tests also
   check practice-dependent reprioritization and legacy bank-version handling.
3. Obtain educator/domain-expert review of content and scoring. Expand the transfer
   bank beyond one item per skill and check that it measures decisions on unfamiliar
   cases rather than recall of coached answers.
4. **Export implemented:** session-level assignment and completion records include
   consented sessions with no answers. Still plan how dropout and repeat participation
   are identified without retaining unnecessary personal information.
5. Freeze the study protocol, primary transfer outcome, allocation procedure,
   exclusions and analysis before collection. Choose sample size based on the
   intended inference and recruitment capacity. A small convenience pilot supports
   feasibility findings, not a strong effectiveness claim.

Live coaching currently uses configured BKT. Behavior-augmented DKT runs offline;
the EdNet checkpoint is not a validated five-skill DeFi coaching model.

## Publication work still needed

Use [RESEARCH_DECISION.md](RESEARCH_DECISION.md) for the measured results and
literature overlap. Pick one main paper question before adding more features.

- For a public-data prediction paper: complete corrected ASSISTments replication;
  add an established item-aware neural comparator with comparable information;
  select settings on validation data; and freeze a fresh test evaluation because
  the current cohort has already informed exploratory choices. Report calibration,
  uncertainty and a separately specified item-novelty evaluation if claiming
  generalization to unseen questions. Preserve each dataset's native field meanings.
- For a HOMIE educational-system paper: complete the intervention repair and
  reviewed learner study above. Public-data prediction results cannot replace it.
- Write the contribution as a bounded, evidence-supported claim. Neither an app,
  DKT integration, nor a higher AUC alone establishes novelty. Negative telemetry
  results are useful evidence but do not automatically make a publishable paper.
- Rewrite the manuscript around the chosen question, actual methods and results;
  replace the old architecture figure; reconcile all claims with implemented and
  evaluated behavior; include limitations, dataset attribution and reproducibility.

## Practical two-to-four-week sequence

| Window | Deliverable and completion check |
|---|---|
| First 2–3 days | Freeze scope; repair and test the simulator treatment; start expert content review and recruitment feasibility checks. |
| Rest of week 1 | Finalize reviewed bank, session-level export and study protocol; package a repeatable demo. Start the external-data comparison only if it serves the chosen paper question. |
| Week 2 | Run the feasible pilot and/or frozen cross-dataset experiment; preserve failures and dropouts; produce analysis tables and confidence intervals. |
| Weeks 3–4, if available | Finish collection and analysis, rewrite the manuscript, verify figures and claims, and rehearse the final-year demonstration. |

If only two weeks remain, prioritize a reliable final-year deliverable and an
honest pilot report. Do not promise a completed effectiveness paper on that schedule.

## Submission packaging

Many learning modules, tests and research documents are currently untracked, among
other staged and unstaged work. Deliberately version the intended deliverable,
record dependencies and run the documented demo/experiment commands from a clean
checkout. Keep raw datasets and participant records out of the submission repository;
include permitted download instructions and aggregate results instead. Preserve
the distinction between the earlier wallet experiments and current learning study.

**Immediate next step after the v2 repair:** obtain expert content review, refine
the transfer bank, and freeze a feasible learner-study protocol. More model
complexity should wait until the research question and evaluation can support it.
