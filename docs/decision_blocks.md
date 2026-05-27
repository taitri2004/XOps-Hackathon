# Evidence Pack §6.5 — Decision Block templates (your personal angle)

Fill in numbers WHILE you build, not Thursday night. Vague answers score 0.
Minimum 2 blocks required; aim for 2 strong blocks over 6 weak ones.

---

## DECISION 1 — Vector store: S3 Vectors over OpenSearch Serverless

DECISION: Use **S3 Vectors** as Bedrock KB vector store backend for StudyBot RAG pipeline.

ALTERNATIVES CONSIDERED:
- **OpenSearch Serverless (2 OCU minimum)** — eliminated: 2 OCU × $0.288/hr × 48h = **$27.65** fixed cost in ap-southeast-1, regardless of query volume. That is 28% of our $100 cap consumed before a single user query.
- **Aurora pgvector** — eliminated: db.t3.medium minimum + storage + 2-3h to set up pgvector extension and tune HNSW params. Lambda needs RDS Proxy → another ~$0.86/48h. Not worth it for ≤500MB of slide content.

MEASUREMENT (fill in after measuring on YOUR stack):
- S3 Vectors cost over 48h on YOUR stack = $______ (from Cost Explorer filtered by Team=G<N>)
- Query latency p50 = ______ ms / p99 = ______ ms (measured by Lambda Duration metric)
- Ingestion time for ______ documents (______ MB total) = ______ minutes
- precision@5 on ______ probe questions = ______ / 5 correct (manual judgment; record each Q+A+expected_source in spreadsheet)

EVIDENCE:
- Cost Explorer screenshot: `docs/evidence/cost_day2.png` showing S3 Vectors line item
- Probe question spreadsheet: `docs/evidence/probe_questions.csv` (5 questions × answer × source_chunk × correct_y/n)
- CloudWatch Lambda Duration graph: `docs/evidence/lambda_latency.png`

TRADE-OFF ACCEPTED:
- S3 Vectors is newer than OpenSearch — less community knowledge, harder to debug if ingestion fails. We accepted this because cost savings of ~$27 justified the risk for a 48h hackathon. Production at >10K docs would warrant re-evaluating.

---

## DECISION 2 — AI model: Claude 3.5 Haiku over Sonnet for default generation

DECISION: Use **Claude 3.5 Haiku** (`anthropic.claude-3-5-haiku-20241022-v1:0`) as the default model in `retrieve_and_generate` calls.

ALTERNATIVES CONSIDERED:
- **Claude 3.5 Sonnet** — eliminated: $3 input / $15 output per 1M tokens = **12x the cost** of Haiku ($0.25 / $1.25). On our test of ______ queries, output quality was indistinguishable in a blind 5-pair comparison (link spreadsheet).
- **Llama 3.1 70B (Bedrock)** — eliminated: $0.30 / $0.30 per 1M, similar cost to Haiku but ______ % accuracy on probe questions vs Haiku ______ % (measure on YOUR stack).

MEASUREMENT (fill in):
- Cost per query on YOUR stack: Haiku = $______ (input tokens × $0.25/M + output × $1.25/M)
- Blind preference: out of 5 paired responses (Haiku vs Sonnet), prefer Haiku: ____ / 5, prefer Sonnet: ____ / 5, no preference: ____ / 5
- Latency p50: Haiku = ______ ms vs Sonnet = ______ ms (CloudWatch Lambda Duration when each is used)

EVIDENCE:
- Blind comparison spreadsheet: `docs/evidence/model_blind_test.csv` (question, haiku_response, sonnet_response, preferred, reason)
- Cost Explorer screenshot filtered by Bedrock service tag: `docs/evidence/bedrock_cost.png`

TRADE-OFF ACCEPTED:
- Haiku occasionally hallucinates page-number citations on slide content with sparse text. We mitigated by adding "If page reference is unclear, say 'see uploaded notes' instead of guessing" in the system prompt. Sonnet would have lower hallucination rate but cost ratio doesn't justify for a hackathon demo.

---

## Optional DECISION 3 — Chunking strategy (only if you tuned chunking)

DECISION: Default Bedrock KB chunking (300 tokens, 20% overlap) — OR — Custom chunking with ______ tokens, ______ overlap.

ALTERNATIVES CONSIDERED:
- **Semantic chunking via custom Lambda preprocessor** — eliminated/adopted because: ______
- **Larger chunks (1000 tokens)** — eliminated/adopted because: precision@5 went from ______ to ______ on probe questions

MEASUREMENT (fill in):
- precision@5 with default chunking = ______ / 5
- precision@5 with tuned chunking = ______ / 5
- 1 named failure case: query "______" returned chunk from doc "______" which is wrong because ______

EVIDENCE:
- `docs/evidence/chunking_ab_test.csv`

TRADE-OFF ACCEPTED:
- ______

---

## Anti-đối phó self-check (READ BEFORE SUBMITTING)

For each block above, can you answer YES to all 5:

- [ ] Did I name a specific service/parameter (not "we used Bedrock")?
- [ ] Did I name at least 2 alternatives with concrete elimination reasons?
- [ ] Do I have at least 1 number with a unit (cost in $, latency in ms, precision X/Y)?
- [ ] Do I have a file path or screenshot path I can hand to the trainer?
- [ ] Did I name a real trade-off (not "no trade-offs" — that means I didn't decide)?

If any NO → expand that block before Friday morning.
