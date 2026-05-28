import random
import unicodedata

WORDS = [
    "minecraft",
    "naruto",
    "matrix",
    "colombia",
    "pikachu",
    "terminator",
    "discord",
    "python",
    "batman",
    "spiderman",
    "pokemon",
    "harrypotter"
]

HANGMAN_STAGES = [
    """
 +---+
 |   |
     |
     |
     |
     |
=========
""",
    """
 +---+
 |   |
 O   |
     |
     |
     |
=========
""",
    """
 +---+
 |   |
 O   |
 |   |
     |
     |
=========
""",
    """
 +---+
 |   |
 O   |
/|   |
     |
     |
=========
""",
    """
 +---+
 |   |
 O   |
/|\\  |
     |
     |
=========
""",
    """
 +---+
 |   |
 O   |
/|\\  |
/    |
     |
=========
""",
    """
 +---+
 |   |
 O   |
/|\\  |
/ \\  |
     |
=========
"""
]


def get_hangman(errors: int):
    return HANGMAN_STAGES[min(errors, 6)]


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text)\
        .encode("ascii", "ignore")\
        .decode()\
        .lower()\
        .strip()


def get_random_word():
    return random.choice(WORDS)


def create_progress(word: str):
    return ["_" for _ in word]


def render_progress(progress: list):
    return " ".join(progress)