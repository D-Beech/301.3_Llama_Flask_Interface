import re
from better_profanity import profanity


# Load default profanity list
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

# Filter functions
def contains_banned_pokemon(text):
    return bool(pokemon_pattern.search(text))

def contains_custom_swearing(text):
    return bool(swear_pattern.search(text))

def contains_profanity(text):
    return profanity.contains_profanity(text)

def censor_text(text):
    return profanity.censor(text)

PII_PATTERNS = {
    "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?\d{1,3})?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
}


# Register filters with names
FILTERS = {
    "pokemon": contains_banned_pokemon,
    "custom_swear": contains_custom_swearing,
    "profanity_lib": contains_profanity,
}

# Elegant check using filter map
def contains_banned_content(text):
    for name, func in FILTERS.items():
        if func(text):
            return True, name #returns bool for if it's bad also name of guard that triggered for logging

    #Checking PII Regex Patterns
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            return True, "PII: " + pii_type
    return False, None





