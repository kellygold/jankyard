"""Anonymous username generator"""
import random

ADJECTIVES = [
    "Sneaky", "Goofy", "Mighty", "Clever", "Sleepy", "Happy", "Grumpy", "Dizzy",
    "Funky", "Jazzy", "Cosmic", "Electric", "Mystic", "Epic", "Brave", "Swift",
    "Wild", "Chill", "Fancy", "Rusty", "Golden", "Silver", "Turbo", "Mega",
    "Ultra", "Super", "Hyper", "Ninja", "Pirate", "Robot", "Cyber", "Neon",
    "Blazing", "Frozen", "Ancient", "Quantum", "Stealth", "Rapid", "Savage", "Noble",
    "Rogue", "Mystic", "Stellar", "Crimson", "Azure", "Emerald", "Radiant", "Shadow",
    "Chaos", "Alpha"
]

NOUNS = [
    "Panther", "Dragon", "Phoenix", "Tiger", "Wolf", "Eagle", "Shark", "Bear",
    "Falcon", "Raven", "Lion", "Cobra", "Viper", "Hawk", "Panda", "Koala",
    "Penguin", "Wizard", "Knight", "Samurai", "Warrior", "Champion", "Hero",
    "Legend", "Master", "Sage", "Oracle", "Shadow", "Storm", "Flame", "Thunder",
    "Serpent", "Kraken", "Griffin", "Hydra", "Titan", "Golem", "Sentinel", "Hunter",
    "Reaper", "Phantom", "Wraith", "Paladin", "Ronin", "Gladiator", "Spartan", "Viking",
    "Berserker", "Striker"
]

def generate_anonymous_username() -> str:
    """Generate a fun anonymous username like 'GoofyPanther42' or 'MightyDragon69'"""
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    # Add 2-digit random number to ensure uniqueness
    number = random.randint(10, 99)
    return f"{adjective}{noun}{number}"
