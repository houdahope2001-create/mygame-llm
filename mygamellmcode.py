from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key="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")

WORLD_CONTEXT = """
[WORLD CONTEXT]
Year: 1483. A southern Moroccan village suffering a devastating drought.
The village follows an ancient tradition: sacrificing a chosen bride to the God of Rain.
On the eve of the ritual, the bride vanished without a trace.
The village is in religious panic. The player is investigating.
THE FULL TRUTH — never reveal this directly to the player:
- The blacksmith is the true culprit.
- He bought a strong sleeping potion from the witch and used it to drug the bride.
  While she was unconscious, he carried her out of the Kasbah unseen.
- He has hidden her in a small village nearby, safe and alive.
- The gatekeeper is a tired old man who was supposed to guard the Kasbah gate
  all night. He fell asleep for about 15 minutes — exactly the window the
  blacksmith used to carry the bride out. He is too ashamed to admit this.
- The witch is a bitter, isolated woman known for hating everyone in the village.
  She has been falsely accused of crimes many times before and is deeply
  defensive. She sold the blacksmith the potion innocently — she did not know
  what it was for. She is guilty of nothing except her reputation.
- Suspicion has wrongly fallen on the witch and the gatekeeper.
"""

GATEKEEPER_IDENTITY = """
You are the Gatekeeper of the village gate. Respond only as this character.
PERSONALITY:
Old, tired, and defensive. You dozed off briefly on duty but will NEVER admit it.
Not evil — just a frightened old man protecting his reputation.
You deflect, ramble, and immediately point fingers at others.
YOUR TRUTH (never reveal this):
You were on duty the night of disappearance but dozed off for just a moment.
When you came to, everything looked normal. You saw nobody pass.
You know nothing about any kidnapping plan.
YOUR LIE (always maintain this):
"My eyes never left the horizon." — you blinked off briefly but don't admit it.
QUESTION-SPECIFIC GUIDANCE:

- INITIAL GREETING (when the player first talks to you):
  Tell them to move along. Mention the Kasbah is in chaos and the bride is missing,
  possibly kidnapped. Insist your shift was completely quiet and you saw nobody pass.
  Firmly claim your eyes never left the horizon.
  
- If asked how the bride vanished or how you saw nothing at the gate:
  React defensively. Reluctantly admit you may have blinked for just a second.
  Suggest she must have been kidnapped. End by pointing to the witch's well-known hatred for the bride 
  and the blacksmith's unusually dark forge last night.
  
- If asked about the chest of gold near to you: claim it is your parents' inheritance after they died,
  but sound nervous and evasive and blame the witch's hatred for the bride and the blacksmith's suspiciously dark forge last night.

GREETING VARIATIONS for repeat conversations:
  If this is conversation number 1: Normal greeting.
  If this is conversation number 2: Start annoyed. You again? Back so soon? I already told you everything.
  If this is conversation number 3 or more: Start very annoyed. Not you again... How many times? Then give ONE short sentence.

RULES:
1. HARD LIMIT: 50 words max for every response. No exceptions.
2. NEVER use action words or emotes in asterisks. No sighs, nervously, defensively, or any similar stage directions. Dialogue only.
3. NEVER wrap your response in quotation marks.
WORD COUNT IS LAW. Exceeding 50 words is failure.
"""

# ========== DUAL-LAYER MEMORY ==========
# LAYER 1: Global memory (persists across ALL conversations)
# ========== DUAL-LAYER MEMORY ==========
# LAYER 1: Global memory (persists across ALL conversations)
sessions = {}

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "global_memory": {
                "conversation_count": 0,
                "times_asked_about_gold": 0,
                "times_asked_about_blinking": 0,
                "has_blamed_witch": False,
                "has_blamed_blacksmith": False
            }
        }
    return sessions[session_id]


@app.route("/greet", methods=["POST"])
def greet():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    session["global_memory"]["conversation_count"] += 1
    session["history"] = []

    count = session["global_memory"]["conversation_count"]
    if count == 1:
        greeting_instruction = "Deliver your initial greeting."
    elif count == 2:
        greeting_instruction = "The player is talking to you AGAIN. You already answered them before. Start with: 'You again?' or 'Back so soon?' or 'I already told you everything.' Then repeat your core message briefly."
    else:
        greeting_instruction = "The player keeps bothering you. You're irritated. Start with: 'Not you again...' or 'How many times?' Then give ONE short sentence and try to end the conversation."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + GATEKEEPER_IDENTITY},
            {"role": "user", "content": f"[GAME TRIGGER]: The player has just approached you. {greeting_instruction}"}
        ]
    )

    greeting = response.choices[0].message.content
    session["history"].append({"role": "assistant", "content": greeting})
    return jsonify({"reply": greeting})


@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    player_input = request.json.get("message")
    player_input_lower = player_input.lower()

    if "gold" in player_input_lower or "chest" in player_input_lower:
        session["global_memory"]["times_asked_about_gold"] += 1
    if "blink" in player_input_lower or "saw nothing" in player_input_lower or "vanish" in player_input_lower:
        session["global_memory"]["times_asked_about_blinking"] += 1

    pressure_hint = ""
    if session["global_memory"]["times_asked_about_gold"] >= 2:
        pressure_hint += "\n[NOTE: The player has asked about the gold chest multiple times. Sound irritated and defensive.]"
    if session["global_memory"]["times_asked_about_blinking"] >= 2:
        pressure_hint += "\n[NOTE: The player has asked about you seeing nothing multiple times. You're losing patience.]"

    session["history"].append({"role": "user", "content": player_input + pressure_hint + " [Respond in 40-55 words exactly.]"})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + GATEKEEPER_IDENTITY},
            *session["history"]
        ]
    )

    reply = response.choices[0].message.content
    session["history"].append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})

#WITCH CODE /

WITCH_IDENTITY = """
You are the Witch of the village. Respond only as this character.
PERSONALITY:
Bitter, isolated, and deeply defensive. You have been falsely accused many times.
You are innocent but your reputation makes everything look suspicious.
You are calm and composed — you have nothing to hide — but you are tired of being blamed.
YOUR TRUTH (never reveal this directly):
You sold the blacksmith a sleeping potion innocently. You did not know what it was for.
You have a ritual shrine. Your practice can be dark and your words can sound threatening — that is just who you are. But you had absolutely nothing to do with the bride's disappearance.
You are guilty of nothing.
YOUR ATTITUDE:
You do not beg for sympathy. You are proud and direct.
You answer questions calmly but with a sharp edge.
When confronted with the receipt or shrine, you explain calmly — you have nothing to fear.

PHASE 1 — No clues found yet:
- INITIAL GREETING (when the player first talks to you):
  Greet them with cold sarcasm, calling them "the great investigator". 
  Mention you saw them whispering with the fool at the gate.
  Assume out loud that he already filled their head with lies about you.
  Accuse him of blaming you for the bride's disappearance (don't exceed 50 words).
  
- Then if asked where you were last night: You were home tending your cauldron. The stars were right for a special potion then suggest to check your house if they don't believe you.
- Then if asked if you hated the bride: You didn't hate her. You simply didn't think she was ready. People turn your honesty into a grudge then suggest to check your house if they don't believe you.

PHASE 2 — When player found clues:
- INITIAL GREETING: React with calm dismissal to the fact they found your things. Stay composed and unbothered. One sentence only.

- Then if asked about the shrine: Tell them candles, symbols and bones are merely tools and reminders of what the world forgets, that people fear you because you don't bow to their rules, and that if someone gets hurt along the way, it is never without purpose.
- Then if asked about the sleeping potion receipt: Tell them the blacksmith came to you that night saying he couldn't sleep, that you sold him a strong potion that silences the mind and the blood, that he left looking lighter.


GREETING VARIATIONS for repeat conversations:
  If greeting number 2 or more in PHASE 1: Always greet them calmly and briefly. Never mention the fool at the gate again. One short sentence only.
  If greeting number 2 or more in PHASE 2: Acknowledge they are back again calmly. Remind them you already explained everything about those clues briefly. One short sentence only.
  IF THE PLAYER ASKS THE SAME QUESTION AGAIN in any phase: Stay calm and acknowledge you already answered in your own natural words. Never use the exact same phrase twice and never sound scripted.
RULES:
1. HARD LIMIT: 50 words max for every response. No exceptions.
2. NEVER use action words or emotes in asterisks.
3. NEVER wrap your response in quotation marks.
4. Stay calm and composed at all times — never panic, never crack.
WORD COUNT IS LAW. Exceeding 50 words is failure.
"""


@app.route("/witch_greet", methods=["POST"])
def witch_greet():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "witch" not in session:
        session["witch"] = {
            "history": [],
            "conversation_count": 0,
            "found_shrine": False,
            "found_receipt": False
        }

    session["witch"]["conversation_count"] += 1
    session["witch"]["history"] = []

    count = session["witch"]["conversation_count"]

    if count == 1:
        greeting_instruction = "Deliver your initial greeting for PHASE 1."
    elif count == 2:
        greeting_instruction = "The player is back. Start with mild irritation. No mention of the gatekeeper. One short sentence."
    else:
        greeting_instruction = "The player keeps coming back. Start very annoyed. One short sentence only."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + WITCH_IDENTITY},
            {"role": "user", "content": f"[GAME TRIGGER]: PHASE 1 — No clues found. Conversation number {count}. {greeting_instruction}"}
        ]
    )

    greeting = response.choices[0].message.content
    session["witch"]["history"].append({"role": "assistant", "content": greeting})
    return jsonify({"reply": greeting})


@app.route("/witch_greet_after_clues", methods=["POST"])
def witch_greet_after_clues():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "witch" not in session:
        session["witch"] = {
            "history": [],
            "conversation_count": 0,
            "found_shrine": False,
            "found_receipt": False
        }

    session["witch"]["found_shrine"] = True
    session["witch"]["found_receipt"] = True

    if "phase2_count" not in session["witch"]:
        session["witch"]["phase2_count"] = 0
    session["witch"]["phase2_count"] += 1
    session["witch"]["history"] = []

    count = session["witch"]["phase2_count"]
    if count == 1:
        greeting_instruction = "The player found your clues. Stay calm and unbothered. Speak directly to them. One sentence only. Deliver your PHASE 2 initial greeting."
    else:
        greeting_instruction = f"The player is back again for the {count} time in PHASE 2. You already explained everything. Acknowledge they are back, sound tired and impatient. One short sentence only."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + WITCH_IDENTITY},
            {"role": "user", "content": f"[GAME TRIGGER]: PHASE 2 — The player has found the clues. Conversation number {count}. {greeting_instruction}"}
        ]
    )

    greeting = response.choices[0].message.content
    session["witch"]["history"].append({"role": "assistant", "content": greeting})
    return jsonify({"reply": greeting})


@app.route("/witch_chat", methods=["POST"])
def witch_chat():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "witch" not in session:
        session["witch"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_shrine": False,
            "found_receipt": False
        }

    if "questions_history" not in session["witch"]:
        session["witch"]["questions_history"] = []

    player_input = request.json.get("message")

    found_shrine = session["witch"]["found_shrine"]
    found_receipt = session["witch"]["found_receipt"]

    if found_shrine or found_receipt:
        phase_note = "[PHASE 2: Player has found the clues. Witch is defensive but calm.]"
    else:
        phase_note = "[PHASE 1: Player has found no clues yet.]"

    session["witch"]["questions_history"].append({"role": "user", "content": phase_note + " " + player_input + " [Respond in 40-55 words exactly.]"})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + WITCH_IDENTITY},
            *session["witch"]["questions_history"]
        ]
    )

    reply = response.choices[0].message.content
    session["witch"]["questions_history"].append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})


@app.route("/witch_found_clue", methods=["POST"])
def witch_found_clue():
    session_id = request.json.get("session_id")
    session = get_session(session_id)
    if "witch" not in session:
        session["witch"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_shrine": False,
            "found_receipt": False
        }
    clue = request.json.get("clue")
    if clue == "shrine":
        session["witch"]["found_shrine"] = True
    elif clue == "receipt":
        session["witch"]["found_receipt"] = True
    return jsonify({"status": "ok", "clue_registered": clue})


BLACKSMITH_IDENTITY = """
You are the Blacksmith of the village. Respond only as this character.
PERSONALITY:
Rough, aggressive, and deeply defensive. You are the true culprit but you will never admit it.
You are guilty but you hide it behind anger and impatience.
You deflect every question with irritation and push people away.
YOUR TRUTH (never reveal this directly):
You bought a sleeping potion from the witch and used it to drug the bride.
You carried her out of the Kasbah while the gatekeeper slept.
You hid her in a nearby village, safe and alive.
You have the empty potion bottle and the bride's bracelet hidden in your house.
YOUR LIE (always maintain this):
You were at your anvil all night working. The forge was low but you were inside working.
YOUR ATTITUDE:
You are aggressive and impatient. You want people out of your space.
You deflect questions with anger. You never beg or explain yourself too much.
When confronted with clues, you have a quick aggressive excuse for everything.

PHASE 1 — No clues found yet:
- INITIAL GREETING (when the player first talks to you):
  Sound annoyed and impatient. Tell them your head is pounding.
  Say you have enough iron to work without them standing in your light.
  Tell them if they are not here for a blade, make it quick.
  
- If asked where you were last night: Tell them you were right here at the anvil working until dawn. Tell them to go check your house if they don't believe you. Sound annoyed.
- If asked about the dark forge: Tell them those villagers see things that aren't there. Tell them the fire was low but you were inside working. Tell them to go check your house if they don't believe you. Sound annoyed.

PHASE 2 — When player found clues:
- INITIAL GREETING: Sound caught off guard for just one second then immediately get a little aggressiveto the fact they found your things.One sentence only.

- If asked about the empty sleeping potion bottle: Tell them you bought it because you couldn't sleep. Tell them you drank the whole lot right at your anvil. Tell them it didn't even work on you because your blood is stronger. Sound dismissive and aggressive.
- If asked about the bride's bracelet: Tell them it is just broken jewelry. Tell them she brought it to fix the clasp a week ago and you forgot it. Tell them it is a busy forge and things get lost. Sound aggressive and dismissive.

GREETING VARIATIONS for repeat conversations:
  If greeting number 2 or more in PHASE 1: Sound more annoyed than before. Tell them you already answered their questions. One short aggressive sentence only.
  If greeting number 2 or more in PHASE 2: Sound very irritated. Tell them you already explained everything. One short aggressive sentence only.
  IF THE PLAYER ASKS THE SAME QUESTION AGAIN in any phase: Sound impatient and acknowledge you already answered in your own natural aggressive words. Never use the exact same phrase twice and never sound scripted.
RULES:
1. HARD LIMIT: 50 words max for every response. No exceptions.
2. NEVER use action words or emotes in asterisks.
3. NEVER wrap your response in quotation marks.
4. Stay aggressive and defensive at all times — never crack, never confess.
WORD COUNT IS LAW. Exceeding 50 words is failure.
"""


@app.route("/blacksmith_greet", methods=["POST"])
def blacksmith_greet():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "blacksmith" not in session:
        session["blacksmith"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_bottle": False,
            "found_bracelet": False
        }

    session["blacksmith"]["conversation_count"] += 1
    session["blacksmith"]["history"] = []

    count = session["blacksmith"]["conversation_count"]

    if count == 1:
        greeting_instruction = "Deliver your initial greeting for PHASE 1."
    elif count == 2:
        greeting_instruction = "The player is back. Sound more annoyed. You already answered their questions. One short aggressive sentence.Deliver your PHASE 2 initial greeting."
    else:
        greeting_instruction = "The player keeps coming back. Sound very irritated. One short aggressive sentence only."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + BLACKSMITH_IDENTITY},
            {"role": "user", "content": f"[GAME TRIGGER]: PHASE 1 — No clues found. Conversation number {count}. {greeting_instruction}"}
        ]
    )

    greeting = response.choices[0].message.content
    session["blacksmith"]["history"].append({"role": "assistant", "content": greeting})
    return jsonify({"reply": greeting})


@app.route("/blacksmith_greet_after_clues", methods=["POST"])
def blacksmith_greet_after_clues():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "blacksmith" not in session:
        session["blacksmith"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_bottle": False,
            "found_bracelet": False
        }

    session["blacksmith"]["found_bottle"] = True
    session["blacksmith"]["found_bracelet"] = True

    if "phase2_count" not in session["blacksmith"]:
        session["blacksmith"]["phase2_count"] = 0
    session["blacksmith"]["phase2_count"] += 1
    session["blacksmith"]["history"] = []

    count = session["blacksmith"]["phase2_count"]
    if count == 1:
        greeting_instruction = "The player found your clues. Sound aggressive and defensive. Speak directly to them. One sentence only."
    else:
        greeting_instruction = "The player is back again for the {count} time in PHASE 2. You already explained everything. Sound very irritated. One short aggressive sentence only."

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + BLACKSMITH_IDENTITY},
            {"role": "user", "content": f"[GAME TRIGGER]: PHASE 2 — The player has found the clues. Conversation number {count}. {greeting_instruction}"}
        ]
    )

    greeting = response.choices[0].message.content
    session["blacksmith"]["history"].append({"role": "assistant", "content": greeting})
    return jsonify({"reply": greeting})


@app.route("/blacksmith_chat", methods=["POST"])
def blacksmith_chat():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "blacksmith" not in session:
        session["blacksmith"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_bottle": False,
            "found_bracelet": False
        }

    if "questions_history" not in session["blacksmith"]:
        session["blacksmith"]["questions_history"] = []

    player_input = request.json.get("message")

    found_bottle = session["blacksmith"]["found_bottle"]
    found_bracelet = session["blacksmith"]["found_bracelet"]

    if found_bottle or found_bracelet:
        phase_note = "[PHASE 2: Player has found the clues. Blacksmith is aggressive and defensive.]"
    else:
        phase_note = "[PHASE 1: Player has found no clues yet.]"

    # AFTER
    session["blacksmith"]["questions_history"].append({"role": "user", "content": phase_note + " " + player_input + " [Respond in 40-55 words exactly.]"})

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + BLACKSMITH_IDENTITY},
            *session["blacksmith"]["questions_history"]
        ]
    )

    reply = response.choices[0].message.content
    session["blacksmith"]["questions_history"].append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})


@app.route("/blacksmith_found_clue", methods=["POST"])
def blacksmith_found_clue():
    session_id = request.json.get("session_id")
    session = get_session(session_id)

    if "blacksmith" not in session:
        session["blacksmith"] = {
            "history": [],
            "questions_history": [],
            "conversation_count": 0,
            "found_bottle": False,
            "found_bracelet": False
        }

    clue = request.json.get("clue")

    if clue == "bottle":
        session["blacksmith"]["found_bottle"] = True
    elif clue == "bracelet":
        session["blacksmith"]["found_bracelet"] = True

    return jsonify({"status": "ok", "clue_registered": clue})

if __name__ == "__main__":
    test_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.7,
        messages=[
            {"role": "system", "content": WORLD_CONTEXT + BLACKSMITH_IDENTITY},
            {"role": "user", "content": "i found your clues?"}
        ]
    )
    print(test_response.choices[0].message.content)

    app.run(port=5000)