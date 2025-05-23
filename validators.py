from guardrails.validator_base import validators_registry
import re
from better_profanity import profanity




# Initialize the profanity filter
profanity.load_censor_words()

# Define banned Pokémon names and compile regex pattern
POKEMON_NAMES = ["pikachu", "charizard", "bulbasaur", "squirtle", "pokemon"]
pattern = re.compile(r"\b(" + "|".join(re.escape(name) for name in POKEMON_NAMES) + r")\b", re.IGNORECASE)

def contains_banned_pokemon(text):
    return bool(pattern.search(text))
