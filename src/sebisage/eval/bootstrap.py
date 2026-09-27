"""Bootstrap confidence intervals for retrieval metrics.

Percentile bootstrap over per-question hit/reciprocal-rank values. These are
rough uncertainty estimates, not statistically rigorous CIs — the test set is
small (n<25), so intervals are wide. Label them as such wherever reported.
"""

import random


def bootstrap_ci(
    hits: list[bool | float],
    n_iter: int = 1000,
    seed: int = 42,
    ci: float = 0.95,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of `hits`.

    Deterministic for a given seed: resamples n_iter times with replacement,
    computes the mean of each resample, and returns the (ci*100)% central
    interval of those means.
    """
    if not hits:
        raise ValueError("hits must be non-empty")

    n = len(hits)
    rng = random.Random(seed)
    means = sorted(sum(hits[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_iter))

    alpha = (1 - ci) / 2
    lower_idx = int(alpha * n_iter)
    upper_idx = min(n_iter - 1, int((1 - alpha) * n_iter) - 1)
    return means[lower_idx], means[upper_idx]
