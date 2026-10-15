"""A tiny neural network brain: senses in, action out.

Every brain has the same shape with different weights, so all agents' brains
run as one batched matrix operation (the trick that later moves to the GPU).
"""

from dataclasses import dataclass

import numpy as np

from emergent_world.agents.agent import Action
from emergent_world.agents.senses import INPUT_SIZE

HIDDEN_SIZE = 16
OUTPUT_SIZE = len(Action)
NEW_ACTION_BIAS = -3.0   # actions added after a brain was made start out unlikely


@dataclass
class Brain:
    w1: np.ndarray   # (INPUT_SIZE, HIDDEN_SIZE)
    b1: np.ndarray   # (HIDDEN_SIZE,)
    w2: np.ndarray   # (HIDDEN_SIZE, OUTPUT_SIZE)
    b2: np.ndarray   # (OUTPUT_SIZE,)

    @classmethod
    def random(cls, rng: np.random.Generator) -> "Brain":
        return cls(
            w1=rng.normal(0, 1 / np.sqrt(INPUT_SIZE), (INPUT_SIZE, HIDDEN_SIZE)).astype(np.float32),
            b1=np.zeros(HIDDEN_SIZE, dtype=np.float32),
            w2=rng.normal(0, 1 / np.sqrt(HIDDEN_SIZE), (HIDDEN_SIZE, OUTPUT_SIZE)).astype(np.float32),
            b2=np.zeros(OUTPUT_SIZE, dtype=np.float32),
        )

    def mutated(self, rng: np.random.Generator, scale: float, rate: float = 1.0) -> "Brain":
        """A copy where a share (`rate`) of the weights get random changes of size `scale`.

        Sparse mutations (few weights, bigger changes) tend to break less of what
        already works than nudging every weight at once.
        """
        def jitter(a):
            changed = rng.random(a.shape) < rate
            return (a + changed * rng.normal(0, scale, a.shape)).astype(np.float32)
        return Brain(jitter(self.w1), jitter(self.b1), jitter(self.w2), jitter(self.b2))

    def copy(self) -> "Brain":
        return Brain(self.w1.copy(), self.b1.copy(), self.w2.copy(), self.b2.copy())

    def fitted(self) -> "Brain":
        """This brain grown to the current senses and actions, if it was made for
        fewer. New senses start with no influence; new actions start unlikely
        (only tried by exploration) until learning or evolution finds a use."""
        n_in, n_hidden = self.w1.shape
        n_out = self.w2.shape[1]
        if n_in == INPUT_SIZE and n_out == OUTPUT_SIZE:
            return self
        w1 = np.zeros((INPUT_SIZE, n_hidden), dtype=np.float32)
        w1[:n_in] = self.w1
        w2 = np.zeros((n_hidden, OUTPUT_SIZE), dtype=np.float32)
        w2[:, :n_out] = self.w2
        b2 = np.full(OUTPUT_SIZE, NEW_ACTION_BIAS, dtype=np.float32)
        b2[:n_out] = self.b2
        return Brain(w1, self.b1.copy(), w2, b2)

    @property
    def parameter_count(self) -> int:
        return self.w1.size + self.b1.size + self.w2.size + self.b2.size


def think(brains: list, inputs: np.ndarray, rng: np.random.Generator,
          selection: str = "argmax", exploration: float = 0.1,
          penalties: np.ndarray | None = None, details: dict | None = None) -> np.ndarray:
    """Run every brain at once. inputs: (agents, INPUT_SIZE). Returns action ids.

    "argmax" takes each brain's top action, with a small chance of a random one
    so agents don't get stuck repeating themselves. Evolution finds argmax
    behavior much faster: a mutation only has to make the right action win,
    not dominate. "sample" draws actions by probability instead.

    penalties (agents x actions) lower the urge to take each action: the
    built-in wiring through which bad food memories hold an agent back from
    eating a food, or walking toward it.
    """
    w1 = np.stack([b.w1 for b in brains])
    b1 = np.stack([b.b1 for b in brains])
    w2 = np.stack([b.w2 for b in brains])
    b2 = np.stack([b.b2 for b in brains])

    hidden = np.tanh(np.einsum("ni,nih->nh", inputs, w1) + b1)
    logits = np.einsum("nh,nho->no", hidden, w2) + b2
    if details is not None:
        details["hidden"], details["values"] = hidden, logits.copy()
    if penalties is not None:
        logits -= penalties

    if selection == "argmax":
        actions = logits.argmax(axis=1)
        explore = rng.random(len(brains)) < exploration
        actions[explore] = rng.integers(0, OUTPUT_SIZE, int(explore.sum()))
        if penalties is not None:
            # Aversion holds back random tries too: an explored action only goes
            # ahead with probability exp(-penalty); otherwise the agent waits.
            chosen = penalties[np.arange(len(brains)), actions]
            refused = explore & (rng.random(len(brains)) >= np.exp(-chosen))
            actions[refused] = Action.REST
        return actions

    logits -= logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs /= probs.sum(axis=1, keepdims=True)
    cumulative = probs.cumsum(axis=1)
    draws = rng.random((len(brains), 1))
    return np.minimum((draws > cumulative).sum(axis=1), OUTPUT_SIZE - 1)


def imitate(brain: Brain, inputs: np.ndarray, action: int, strength: float) -> None:
    """Put yourself in someone else's place: seeing what they saw, make the action
    they took more likely (strength > 0) or less (strength < 0). A softmax step on
    the last layer, so the other actions give way."""
    hidden = np.tanh(inputs @ brain.w1 + brain.b1)
    logits = hidden @ brain.w2 + brain.b2
    p = np.exp(logits - logits.max())
    p /= p.sum()
    target = -p
    target[action] += 1.0
    brain.w2 += strength * np.outer(hidden, target).astype(np.float32)
    brain.b2 += (strength * target).astype(np.float32)


def learn(brain: Brain, hidden: np.ndarray, action: int, error: float, rate: float):
    """Nudge the brain's value for the action it took toward what happened next
    (temporal-difference learning on the last layer)."""
    error = float(np.clip(error, -5.0, 5.0))
    brain.w2[:, action] += rate * error * hidden
    brain.b2[action] += rate * error
