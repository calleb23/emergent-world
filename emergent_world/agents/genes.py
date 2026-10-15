"""Learning genes: how each person learns is itself inherited and can evolve.

Three genes set how fast someone learns from their own experience, how strongly
watching others shapes them, and how often they try something at random. A
child's genes are the geometric mean of its parents' with a little random
variation, so evolution can tune learning itself (the Baldwin effect: learning
changes which inherited starting points do well).

With `config.learning_genes` off, genes are still inherited and varied exactly
the same way but have no effect, so any change in them is pure drift: the
control that shows whether real selection is at work.
"""

import numpy as np

GENES = ("learn_rate", "imitation_rate", "exploration")
LIMITS = {"learn_rate": (1e-4, 0.1), "imitation_rate": (1e-5, 0.05), "exploration": (0.01, 0.5)}


def founder_genes(rng, config) -> dict:
    """A founder's genes: the configured values, varied widely."""
    return {g: _clip(g, getattr(config, g) * float(np.exp(rng.normal(0, config.gene_founder_spread))))
            for g in GENES}


def inherit(rng, config, parent, father=None) -> dict:
    sources = [p for p in (parent, father) if p is not None and p.genes]
    if not sources:
        return founder_genes(rng, config)
    out = {}
    for g in GENES:
        log_mean = float(np.mean([np.log(p.genes[g]) for p in sources]))
        out[g] = _clip(g, float(np.exp(log_mean + rng.normal(0, config.gene_mutation))))
    return out


def value(agent, config, gene: str) -> float:
    """The gene's effect on behaviour: the agent's own value, or the configured one in the control."""
    if config.learning_genes and agent.genes:
        return agent.genes[gene]
    return getattr(config, gene)


def _clip(gene, v):
    lo, hi = LIMITS[gene]
    return float(min(hi, max(lo, v)))
