# SebiSage End-to-End Evaluation Report (test set)

n test questions: 23

## Retrieval (Phase 3, test set)

- recall_at_1: 0.6190476190476191
- recall_at_3: 0.8571428571428571
- recall_at_5: 0.9047619047619048
- mrr_at_10: 0.7468253968253968

## Routing

- Router accuracy (dev, Phase 5): 1.0
- Router accuracy (test): 1.0
- Refusal precision (test, n=2 out-of-scope): 1.0
- Refusal recall (test, n=2 out-of-scope): 1.0

## Grounding

- Grounding pass rate (test, regulation-routed answers, n=21): 1.0

## EvalForge

- n evaluated: 17 (n_failed reported by EvalForge: 17)
- mean format: 0.6824
- mean relevance: 0.8172
- mean length: 0.8838
- mean keyword_overlap: 0.7059
- judged (of 17): 0
- EvalForge's LLM-judge scores are a secondary, caveated signal only - EvalForge's own inter-annotator kappa for its judge was low. Rule-based (length, keyword_overlap, format) and embedding (relevance) scores are the primary signal here.

## Cost, Latency, Cache

- Latency p50 / p95: 35381.5ms / 79836.1ms
- Mean tokens in/out: 898.6 / 63.8
- Mean estimated cost per query: $0.00032
- LLM disk-cache hit rate (this run): 0.0
