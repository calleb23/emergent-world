"""Names for people, so their stories read like stories.

Every person gets a short made-up given name. Founders also start a family line
named after them, and everyone born into it carries that line: "Mirel of the
Tavo line". Names are for the observer only; agents never perceive them.
"""

ONSETS = ("", "b", "d", "f", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z",
          "br", "dr", "kr", "th", "sh", "tr", "gr")
VOWELS = ("a", "e", "i", "o", "u", "ai", "ei", "ou", "ia")
CODAS = ("", "", "", "n", "l", "r", "s", "th", "m", "k")


def make_name(rng) -> str:
    """Two syllables, like 'Tavo', 'Mirel', 'Shoun'."""
    def pick(options):
        return options[int(rng.integers(0, len(options)))]
    first = pick(ONSETS) + pick(VOWELS[:5])
    second = pick(ONSETS[1:16]) + pick(VOWELS) + pick(CODAS)
    return (first + second).capitalize()


def label(agent) -> str:
    """How people are named in stories: 'Mirel (#14)'."""
    return f"{agent.name} (#{agent.id})" if agent.name else f"#{agent.id}"
