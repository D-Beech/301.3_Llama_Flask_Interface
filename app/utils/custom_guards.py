import re
from better_profanity import profanity


# Setup (load better-profanity default list)

profanity.load_censor_words()

# Helper to build regex pattern
def build_pattern(word_list):
    return re.compile(r"\b(" + "|".join(re.escape(word) for word in word_list) + r")\b", re.IGNORECASE)

# Word lists
POKEMON_NAMES = ["pikachu", "charizard", "bulbasaur", "squirtle", "pokemon"]
CUSTOM_SWEAR_WORDS = ["damn", "hell", "shit", "fuck", "bastard", "asshole", "crap"]

# Build regex patterns
pokemon_pattern = build_pattern(POKEMON_NAMES)
swear_pattern = build_pattern(CUSTOM_SWEAR_WORDS)

# Individual Filters
def contains_banned_pokemon(text):
    """Check for Pokémon names."""
    return bool(pokemon_pattern.search(text))

def contains_custom_swearing(text):
    """Check for basic swearing from custom list."""
    return bool(swear_pattern.search(text))

def contains_profanity(text):
    """Use better_profanity library to check for swearing/slurs."""
    return profanity.contains_profanity(text)

def censor_text(text):
    """Censor swearing using better_profanity."""
    return profanity.censor(text)

# Combined Check  / Gitchy atm
def contains_banned_content(text):
    return (
        contains_banned_pokemon(text) or
        contains_custom_swearing(text) or
        contains_profanity(text)
    )

