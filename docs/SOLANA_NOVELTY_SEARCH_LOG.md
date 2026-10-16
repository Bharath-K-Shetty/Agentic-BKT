# Evidence-led novelty search: 9 October 2026

The requirement is a real blockchain AI/ML contribution. Novelty is a claim to
support with a specific distinction and evidence, not a promise that searching
will eventually produce a publishable result.

## Directions checked

| Direction | Evidence checked | Decision |
|---|---|---|
| Delayed outcome calibration | Delayed ACI, HAPS and financial delayed-label work; our held-out replay | Ordinary weighting overlaps prior work and our intervention misses its success gate. Keep the result. |
| Oracle trust/uncertainty prediction | ACon2, TOAD-ML, RED-ORACLE and RED-ARB original paper and corrected dataset documentation | Generic trust calibration is already studied. Corrected source definitions supersede tempting descriptive gaps. |
| Transaction execution risk with unknown signer history | ISSTA 2025 Solana failure study, Ethereum transaction classification, SolArchive raw schemas and actual Parquet rows | A narrower empirical candidate is being tested: transferable risk from non-signer accounts after controlling for signer and read-only context. |

[ACon2, USENIX Security 2023](https://www.usenix.org/conference/usenixsecurity23/presentation/park)
already studies adaptive conformal consensus for blockchain oracles.
[TOAD-ML, September 2026](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2026.1903202/full)
already studies multi-source oracle anomaly classification and trust scores.
Neither generic conformal oracle learning nor a trust score is a new idea here.

The original [RED corpus preprint](https://arxiv.org/abs/2610.00005) led to two
versioned deposits. Their first versions are restricted, but their latest versions
are open: [RED-ORACLE v1.1](https://zenodo.org/records/23020949) and
[RED-ARB v1.1](https://zenodo.org/records/23020971). We downloaded their README,
schema and correction documents; we did not train on these tapes. The corrections
identify currency/side mismatches, sequential requests and dependence, and
withdraw several original interpretations. Rediscovering those corrections is
not our novelty. These records also do not document actual fills or deployed
Solana oracle account state merely by providing Hermes prices/Jupiter quotes.

## Transaction-risk candidate

**Question:** Can previously observed failures involving declared, non-signer
writable accounts help screen an included transaction whose first signer has no
available failure history, beyond signer history and read-only/template context?

The [ISSTA 2025 author paper](https://zhiyuan-wan.github.io/assets/publications/zheng_issta_25_solana.pdf)
measures initiators, failing programs, error categories and time patterns. The
reviewed study does not evaluate our cold-signer, declared-account risk question.
Its [replication sample](https://github.com/ZXXYy/Solana_Failed_Tx), pinned at
`e69ce6637ef828a01d84d3ba70b6e22df92b98dd`, has 10,000 rows over approximately
24 seconds. Only failing rows supply the selected failing instruction; success
rows do not supply an equivalent full message. That sample is not a fair
pre-execution feature table. This is a suitability limitation, not a criticism
of its original descriptive purpose.

[Oliveira et al., 2021](https://www.researchgate.net/publication/351723407_Analyzing_Transaction_Confirmation_in_Ethereum_Using_Machine_Learning_Techniques)
already classify Ethereum execution outcomes using gas and related attributes;
their reported feature list includes actual gas used and inclusion-related
pending time. Our retrospective checkpoint features exclude corresponding
post-execution fields. Their existence rules out claiming transaction failure
classification itself as new.

Commercial/hackathon transaction stacks also advertise ML or LLM retry/fee
decisions. Their existence rules out a broad "first AI for Solana reliability"
claim. We have not independently verified their advertised effectiveness.

## Actual new source checks

[SolArchive](https://huggingface.co/datasets/solarchive/solarchive), pinned at
`6588cad2832e62be03972ac80d69c6af11d631c8`, releases BigQuery-derived Parquet
records under CC BY 4.0. Its README's complete-history wording is broader than
the pinned inventory we checked: the transaction inventory contains 476 dated
partitions, 85 in 2020, 356 in 2021 and 35 in 2025, plus a root index entry. No 2022–2024
or 2026 transaction dates occur in that inventory. Do not assume continuous
coverage from its README examples.

The first sampled 2025-11-01 row group contains 133,010 unique signatures,
97,303 distinct slots, 42,623 declared signers, 110,730 successes and 22,280
failures, spanning 00:00:01 to 23:59:59 UTC. Actual statuses are `Success` and
`Fail`, differing from the schema's example spelling `Failed`.

Selected columns are fetched by validated HTTP byte ranges from pinned HF URLs.
The index's original whole-file hash has not been verified because whole files
are not downloaded. Range hashes and local derived-file hashes are recorded;
do not equate them with verification of the original complete file.

The next two row groups have 15 identical repeated signatures within November 2,
zero cross-date overlaps and no timestamp/partition mismatches in this audit.
Identical selected-payload duplicates are counted once; conflicting duplicates
abort. No models had been fitted when this cleaning rule was added.

## What would qualify as progress

A positive cold-signer result after strong read-only/template controls, followed
by an unchanged later-week confirmation, would support a distinct empirical
contribution candidate. It would not prove a globally original algorithm.
Historical risk aggregation and boosted trees are established methods.

Actual submission times and unlanded attempts are absent. This is conditional
execution-risk screening, not a demonstrated reduction in total transaction
failures, fee savings, congestion, or a causal explanation. Histories use sampled
participation; shared accounts do not establish common ownership or blame.

The [pilot settings](../research/solana/ml/transaction_protocol.json) fix the
primary comparison before model results. Do not retune on the pilot test day.
Reserve November 8–10 for unchanged confirmation. A separate source, broader
periods, stronger identity baselines and genuine arrival-time observations may
still be required before a paper's contribution is defensible.

## Executed result and refinement

The first two primary experiments are complete. Cold-signer AP gains over the
structure/signer/read-only/template baseline are +0.0594 and +0.0265, with positive
paired-hour intervals. The post-result first-appearance and signer-bootstrap
checks also retain positive gains in these two periods. Thus the result is not
explained solely by repeated pending transactions from a single address.

A later November 22–24 extension uses alternate shards selected by a fixed
date/seed hash after inspecting only file counts. Its primary point gain is
+0.0179, but the hour-bootstrap interval crosses zero. This does not establish
stable gains across all periods. The identity-score diagnostic is also mixed:
its added writable-history gain is uncertain in the second period. Both limits
must remain in the paper's argument.

Additional primary sources reviewed on this pass include
[CMC's 2026 multisig anomaly study](https://www.techscience.com/cmc/v89n2/68773/html),
which explicitly frames its task as post-execution triage,
[the AIA platform review and TRON simulation](https://ojs.bonviewpress.com/index.php/AIA/article/view/6923),
and [BRIGHT](https://arxiv.org/abs/2205.13084), which already exploits relational
entity context for real-time fraud detection. These remove broad claims about
temporal evaluation, transaction failure prediction and relational transfer
being new. They do not evaluate the exact declared-account cold-signer benchmark
we tested, based on the reviewed task definitions. This is a limited literature
finding, not proof of absence everywhere.

The strongest current contribution candidate is the **cold-signer execution-risk
benchmark and its aggregate-versus-cold blind spot**, with writable context as a
tested, imperfect remedy. See [the generated evidence report](SOLANA_TRANSACTION_RISK_RESULTS.md)
for every primary and diagnostic result. A universally better algorithm and
publication readiness remain unproven.

## Reserved refined confirmation completed

After the three periods above, a narrower endpoint was specified before fetching
transaction outcomes for November 29–December 1: first signer appearances in
the sampled window, with the same delayed learned identity score supplied to
both models. Alternate shards were selected from file counts with a fixed
date/seed hash. Model, history, identity and bootstrap settings were unchanged.

The reserved test includes 17,904 first appearances. Its identity-controlled
AP gain is **+0.03161**, with paired-hour 95% interval **[+0.01682, +0.05012]**.
The fixed refined success condition passes. This supports the narrower empirical
contribution candidate without making the earlier uncertain comparisons disappear.
The corresponding global validation threshold transfers poorly to this test:
false alarms are high. Ranking evidence does not establish deployment readiness.

We can defend a specific tested research question and gap relative to the
reviewed sources. We cannot guarantee global originality or paper acceptance,
and established history encodings/boosting remain established methods. Broader
coverage, independently tested identity models, matched feedback batching and
independent/arrival-time observations remain the next publication evidence.
