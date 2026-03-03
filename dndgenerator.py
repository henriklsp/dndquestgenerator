"""
dndgenerator.py — D&D scenario generator using Mistral AI via LangChain.

Exposes generate_scenario() for use by the Streamlit app (app.py).
Can also be run directly from the command line for quick console output.
"""

from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import PromptTemplate
import os
import random


# ---------------------------------------------------------------------------
# Scenario ingredient lists
# Each run picks one value at random from each list (except theme, which can
# be overridden by the caller).
# ---------------------------------------------------------------------------

quest_list = [
    "explore",
    "retrive a lost item",
    "rescue someone",
    "defend people in danger",
    "do mercenary work",
    "deliver an item (ambush!)",
    "investigate a mystery",
    "investigate, but the deceitful quest giver lays a trap",
    "exterminate pests",
    "scout",
    "participate in a contest",
    "escape the minions of a tyrant",
    "Assist a higher-level hero",
]

location_list = [
    "Abandoned cellars",
    "Old ruins",
    "A secret crypt",
    "Caves and tunnels",
    "A dangerous forest trail",
    "A hidden lair",
    "A Classic Dungeon Crawl",
    "Hazardous terrain",
    "An epic fantasy location",
    "Remnants of a battlefield littered with broken fortifications, tents, wagons, and corpses",
]

theme_list = [
    "Marauding monsters",
    "A sinister intelligent item",
    "Lurking evil",
    "Unexplained magical phenomenon",
    "Rumors and legends, partially true, but with a shocking twist.",
    "Inevitable betrayal",
    "A hazardous journey",
    "The aftermath of a magic duel with lingering magical effects",
    "An enchanted person acting against their will",
    "A band of monstrous humanoids",
    "A cunning illusion",
    "A powerful monster that must be avoided or appeased",
]

# Duration is a single-item list; kept as a list so it can be expanded later.
duration_list = ["A single session."]


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate_scenario(level: int, theme_override: str, user_key: str | None, fallback_key: str) -> tuple[str, str, str, str]:
    """
    Generate a D&D scenario using Mistral AI in two passes:
      1. Build the full scenario (plot, locations, enemies, items, etc.)
      2. Review it for consistency and add follow-up Q&A and extra creatures.

    Args:
        level:          Party level (1–20). Controls Challenge Rating in the prompts.
        theme_override: If non-empty, use this theme instead of picking one at random.
        user_key:       Mistral API key supplied by the user. If provided, uses
                        mistral-medium for richer output.
        fallback_key:   Built-in API key used when no user key is given, or when the
                        user key fails. Always uses mistral-tiny to stay within the
                        free-tier limits.

    Returns:
        A tuple (scenario_text, extra_text, summary, error).
        summary is a one-line description of the randomly chosen ingredients,
        shown at the top of the output so the DM knows what was rolled.
        error is an empty string on success, or a short message describing
        what went wrong (displayed in red in the UI).
    """

    # --- Pick random ingredients ---
    quest    = random.choice(quest_list)
    location = random.choice(location_list)
    theme    = theme_override if theme_override else random.choice(theme_list)
    duration = random.choice(duration_list)
    level_str = str(level)

    # Human-readable summary of what was rolled, returned for display in the UI
    summary = f"The quest to {quest} in {location} with {theme} for a level {level_str} party.".capitalize()

    # --- Choose model and API key ---
    # Use mistral-medium when the user supplies their own key (better output).
    # Fall back to mistral-tiny with the built-in key otherwise.
    if not user_key:
        llm = ChatMistralAI(model="mistral-tiny", api_key=fallback_key)
    else:
        llm = ChatMistralAI(model="mistral-medium", api_key=user_key)

    # --- Pass 1: generate the scenario ---
    # templatetext uses LangChain {placeholders} that are filled in below.
    # The text is intentionally verbose so the LLM produces structured output.
    templatetext = (
        "Write a D&D scenario suitable for a duration of {duration}. The player(s) are given a quest to {quest}, "
        "which leads to {location}. The plot should revolve around {theme}. Encounters and obstacles Challenge Rating must "
        "be suitable for a party of level {level}. Write the following sections: Plot, Quest, Setting, Surprise, Start, "
        "Endings, Locations, Enemies, Creatures, Items, Problems. Information must be consistent, e.g. creatures mentioned "
        "in locations must be described in Enemies or Creatures section, items in a location or carried by a creature must "
        "be described in the Items section, and the Items and Problems sections contains only those mentioned in earlier sections. \n"
        "Write in plain text without formatting or special characters except line breaks. \n\n Section details: \n"
        "* Plot (summary for DM up to 100 words); \n"
        "* Quest (description told to players in up to 100 words); \n"
        "* Setting (up to 20 words); \n"
        "* Surprise (event, plot twist, or something to investigate during the quest to surprise players); \n"
        "* Start location (up to 5 words); \n"
        "* Endings (what is the final challenge? Good ending, bad ending, alternative ending); \n"
        "* Rewards (gold or valuables paid, found or looted on succesful completion); \n"
        "* A list of 3 to 6 locations or rooms - for each location write: Name, Type (eg. room, trail, cave, area), size and layout, "
        "Description (environment, atmosphere, first visual impression; up to 5 words),"
        "Exits (which locations/rooms can the heroes go to and how), Points of interest (obstacles, props, hazards, interactables, "
        " curios, anything remarkable), enemies/creatures, items (loot, treasure, useful things); \n"
        "* A list of Enemies (up to Challenge Rating {level}) - for each enemy write: Name, Size category, Appearance (up to 10 words), Hit Points, Armor Class, "
        "Speed, Attack(s), Damage, Special Attacks, Special Qualities, Behavior (up to 10 words), Items carried if any; \n"
        "* Creatures - 1 to 3 non hostile creatures or NPCs - for each, write: Name, Appearance (up to 10 words), Attitude (1 word), "
        "Motivation (up to 10 words) \n"
        "* A list of the 5 most significant items in the scenario - for each write: "
        "Name, Appearance (up to 10 words), GP value, Possible uses, Significance in the scenario; \n"
        "* A list of 1 to 5 hazards, problems or traps - for each write: description, effect, skill/ability check, "
        "saving throw (if applicable), suggested solution, alternative solution, suggested items, suggested spells."
    )

    prompt = PromptTemplate(
        input_variables=["quest", "theme", "level", "location", "duration"],
        template=templatetext,
    ).format(
        quest=quest,
        location=location,
        theme=theme,
        level=level_str,
        duration=duration,
    )

    error = ""

    # First attempt. If the user-supplied key is rejected, fall back to the
    # built-in key with mistral-tiny and flag it so the UI can inform the user.
    try:
        response = llm.invoke(prompt)
    except Exception:
        error = "(Mistral API key failed)"
        llm = ChatMistralAI(model="mistral-tiny", api_key=fallback_key)
        try:
            response = llm.invoke(prompt)
        except Exception:
            return ("", "", summary, "(LLM call failed. Cannot generate scenario)")

    # --- Pass 2: review and enrich the scenario ---
    # extraprompt feeds the first response back to the LLM and asks it to:
    #   - spot inconsistencies and answer Why/How/What-if questions
    #   - add one extra friendly NPC and one extra enemy
    # The long example block at the end steers the LLM toward the desired format.
    extraprompt = (
        "For the following AI-generated D&D scenario, identify inconsistencies and missing or unclear information "
        "by asking three 'Why' questions, three 'How' questions and three 'What if the players...' questions. "
        "For each question, provide a definitive logical answer and make up the missing details. "
        "Simple, straightforward and logical is better than far-fetched, creative and convoluted. "
        "Finally add one potentially helpful creature or NPC and one extra enemy of Challenge Rating " + level_str + "\n\n"
        "Write in plain text without formatting or special characters except line breaks. \n"
        "Use this format: \n - Why is the villain doing xxx? Because he intends to xxx.\n"
        " - Why is that item there? Because it was xxx.\n"
        " - Why is that creature hostile? Because it wants xxx.\n"
        " - How did the villain do xxx? By using the xxx to xxx.\n"
        " - How does the monster avoid the trap? It has been restricted to only xxx.\n"
        " - How can the heroes get to xxx? By going from xxx through xxx using xxx.\n"
        " - What if the players kill xxx? Then they will have to xxx.\n"
        " - What if the players go the wrong way? Then they will be blocked by xxx.\n"
        " - What if the players cannot xxx? Then xxx helps them by xxx.\n"
        " Extra NPC: Elf druid travelling the forest trail. Can cure wounds or give advice for a small fee. \n"
        " Extra enemy: Viper hiding under the chest: AC 15, 9 HP, bite d4+poison. Can be scared away with a DC 15 intimidate check. \n\n"
        "  Or another example:\n - Why is there a bridge underground? There is a deep crevasse intersecting the tunnel. Climbing up from the bridge with a DC 10 climb check leads to the top of the cliffs. \n"
        " - Why did the wizard hire the heroes in stead of doing it themselves? Because she is too busy crafting a magic item to deal with such a trivial matter and will be annoyed if they ask for help.\n"
        " - Why is there a valuable magic dagger lying around? Because it was carried by an adventurer who was eaten by the giant spider. His armor and backpack can be found in the spider web under the ceiling.\n"
        " - How did the monster get into the locked cellar? It is summoned by a warding glyph on the door and disappears when the summoning ends after 1 minute.\n"
        " - How can goblins be hiding in the middle of a human town? They only come out from the hidden tunnel at night. The night watch are noisy in their heavy armor and easy to evade.\n"
        " - How can the heroes defeat the troll? With fire. There are oil barrels in the storage room and two bottles of alchemist fire on the shelf.\n"
        " - What if the players keep the gem in stead of returning it? Then they get no reward but can sell the gem for 1000gp. The quest giver will later send bounty hunters to retrieve it.\n"
        " - What if the players cannot figure out the puzzle? They can circumvent it by destroying the door, but the noise attacts two guards: level 1, AC 13, 10 HP, armed with d6 longspear.\n"
        " - What if the players attack the helpful gnome? Treat him as a level 3 wizard: AC 10, 14 HP, casts Gust of Wind (save DC 13 or be blown back and off balance). Will try to escape.\n\n"
        " Extra creature: Raven perched on a tombstone. If given food, it will squawk loudly to reveal the tiger waiting in ambush. \n"
        " Extra enemy: A dragon statue in the courtyard. The evil sorcerer can use a scroll to animate it: AC 14, 31 HP, Hardness 10, slam d6+1. Reverts to an inanimate statue after 5 rounds. \n"
        " The scenario is the following: .\n\n" + response.content
    )

    extraresponse = llm.invoke(extraprompt)

    # Strip any LLM preamble before the first "Why" question.
    # Mistral sometimes adds an intro sentence or horizontal rule before the
    # Q&A block. We find "Why", walk back to the start of that line (rfind "\n")
    # so the line marker is preserved regardless of character (-, *, 1., etc.),
    # then discard everything before it. If "Why" isn't found, text is left intact.
    extra = extraresponse.content
    idx = extra.find("Why")
    if idx > 0:
        line_start = extra.rfind("\n", 0, idx)
        if line_start >= 0:
            extra = extra[line_start + 1:]

    return (response.content, extra, summary, error)


# ---------------------------------------------------------------------------
# Command-line entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Welcome to your D&D scenario generator!")
    print("Importing LangChain and Mistral...")

    # Read the API key from the environment so it is never hard-coded here.
    # Set MISTRAL_API_KEY before running, e.g.:  export MISTRAL_API_KEY=your_key
    fallback = os.environ.get("MISTRAL_API_KEY", "")

    response_content, extra_content, summary, error = generate_scenario(
        level=1,
        theme_override="",
        user_key=None,
        fallback_key=fallback,
    )

    print(response_content)
    print(extra_content)
