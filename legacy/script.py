"""
Sitcom Bible & Scene Script for "Buffering" — V2
A sitcom about four roommates working at competing SF tech startups.

V2 changes:
- 6 scenes (consolidated from 10), each with enough dialogue for 1-3 minutes
- Emotion cues in parentheses for Fish-Speech expressiveness
- Multi-speaker interactions within each scene
"""

# ─── Characters ───────────────────────────────────────────────────────────────

CHARACTERS = {
    "maya": {
        "name": "Maya Chen",
        "role": "Lead engineer at a failing AI startup",
        "visual": (
            "East Asian woman in her late 20s, short straight black hair with subtle blue highlights, "
            "round wire-frame glasses, wearing an oversized dark purple hoodie with a small robot logo, "
            "dark jeans, white sneakers, confident posture but tired eyes, warm skin tone"
        ),
        "portrait_prompt": (
            "Professional portrait photograph of an East Asian woman in her late 20s, short straight black hair "
            "with subtle blue highlights, round wire-frame glasses, wearing an oversized dark purple hoodie "
            "with a small robot logo on the chest, dark jeans, standing in a modern apartment, "
            "soft natural window lighting, sharp focus, photorealistic, 8k, full body shot"
        ),
        "voice_seed": 42,
        "voice_temp": 0.8,
        "voice_description": "Confident, fast-talking, stressed but competent female engineer",
    },
    "derek": {
        "name": "Derek Thompson",
        "role": "Growth hacker at a crypto company that keeps pivoting",
        "visual": (
            "Tall Black man in his early 30s, immaculately trimmed short beard, confident smile, "
            "wearing a fitted navy blazer over a bright graphic tee with geometric patterns, "
            "slim khaki chinos, clean white leather shoes, silver watch"
        ),
        "portrait_prompt": (
            "Professional portrait photograph of a tall Black man in his early 30s, immaculately trimmed "
            "short beard, confident smile, wearing a fitted navy blazer over a bright graphic tee, "
            "slim khaki chinos, standing in a modern apartment, soft natural window lighting, "
            "sharp focus, photorealistic, 8k, full body shot"
        ),
        "voice_seed": 137,
        "voice_temp": 0.85,
        "voice_description": "Smooth, overly confident, always pitching, charismatic male voice",
    },
    "priya": {
        "name": "Priya Sharma",
        "role": "UX designer who secretly hates all technology",
        "visual": (
            "South Asian woman in her mid 20s, long dark wavy hair often in a loose side braid, "
            "warm brown eyes, wearing a mustard yellow cardigan over a white blouse, colorful printed scarf, "
            "high-waisted olive green pants, brown ankle boots, always carrying a leather-bound sketchbook"
        ),
        "portrait_prompt": (
            "Professional portrait photograph of a South Asian woman in her mid 20s, long dark wavy hair "
            "in a loose side braid, warm brown eyes, wearing a mustard yellow cardigan over a white blouse, "
            "colorful printed scarf, high-waisted olive pants, holding a leather sketchbook, "
            "standing in a modern apartment, soft natural window lighting, photorealistic, 8k, full body shot"
        ),
        "voice_seed": 256,
        "voice_temp": 0.75,
        "voice_description": "Dry, sarcastic, calm female voice with deadpan delivery",
    },
    "finn": {
        "name": "Finn O'Brien",
        "role": "QA tester who finds bugs in everything including real life",
        "visual": (
            "Pale Irish man in his late 20s, messy curly red hair, light freckles across his nose, "
            "perpetually confused wide-eyed expression, wearing a loud Hawaiian shirt with palm trees "
            "over a plain white t-shirt, cargo shorts, worn sandals"
        ),
        "portrait_prompt": (
            "Professional portrait photograph of a pale Irish man in his late 20s, messy curly red hair, "
            "light freckles, perpetually confused expression, wearing a loud Hawaiian shirt with palm trees "
            "over a white t-shirt, cargo shorts, standing in a modern apartment, soft natural window lighting, "
            "sharp focus, photorealistic, 8k, full body shot"
        ),
        "voice_seed": 389,
        "voice_temp": 0.8,
        "voice_description": "Anxious, rapid-fire, neurotic male voice with slight Irish accent",
    },
}

# ─── Locations ────────────────────────────────────────────────────────────────

LOCATIONS = {
    "living_room": (
        "Modern San Francisco apartment living room with a panoramic window showing the Bay Bridge at golden hour, "
        "cluttered with tech gadgets, a large whiteboard covered in diagrams, mismatched furniture including "
        "a worn leather couch and beanbag chairs, tangled cables, a broken espresso machine on a side table, "
        "warm ambient lighting, photorealistic interior photography, 8k"
    ),
    "kitchen": (
        "Small galley kitchen in a San Francisco apartment, cluttered countertops with smart home gadgets, "
        "a tablet mounted on the fridge showing notifications, coffee mugs with tech company logos, "
        "morning light streaming through a small window, cozy and lived-in, photorealistic, 8k"
    ),
    "maya_desk": (
        "Corner desk setup in a San Francisco apartment, three monitors showing code and terminal windows, "
        "mechanical keyboard with custom keycaps, desk lamp casting warm light, energy drink cans, "
        "sticky notes everywhere, a small succulent plant, late night atmosphere, photorealistic, 8k"
    ),
    "hallway": (
        "Narrow apartment hallway with coats hanging on hooks, shoes piled by the door, "
        "a smart doorbell with a blinking red light, package boxes stacked against the wall, "
        "overhead fluorescent light, photorealistic interior, 8k"
    ),
    "rooftop": (
        "San Francisco apartment building rooftop at dusk, panoramic city skyline view with fog rolling in, "
        "string lights hung between posts, a couple of folding chairs and a small table, "
        "the Bay Bridge glowing in the background, cinematic golden hour lighting, photorealistic, 8k"
    ),
}

# ─── Scenes (6 scenes, 1-3 minutes each) ─────────────────────────────────────

SCENES = [
    # ── Scene 1: Cold Open (target ~1 minute) ────────────────────────────────
    {
        "id": "001",
        "title": "Cold Open — The Bug",
        "location": "maya_desk",
        "characters": ["maya"],
        "camera": "close-up on face, monitor glow illuminating features, slow zoom in",
        "action": (
            "Maya stares at her monitor in disbelief, her face lit by the blue glow of cascading error logs. "
            "She slowly removes her glasses and rubs her eyes, then puts them back on. The errors are still there. "
            "She takes a deep breath, reaches for an energy drink can, finds it empty, and tosses it aside."
        ),
        "target_duration_sec": 60,
        "dialogue": [
            ("maya", "(panicked) No. No no no no no. The deployment is in twelve hours."),
            ("maya", "(frustrated, talking to herself) This was supposed to be a simple patch. A one-line fix. Who writes a one-line fix that breaks seventeen tests?"),
            ("maya", "(angry, staring at screen) Oh. I do. I wrote it. Three weeks ago at two in the morning."),
            ("maya", "(defeated, slumping back) Past Maya is the worst engineer I've ever worked with."),
            ("maya", "(resolute, sitting up straight) Okay. Okay. We can fix this. I just need coffee, a whiteboard, and someone who actually reads documentation."),
            ("maya", "(grabbing phone, dialing) Finn. Wake up. I need you. Now."),
        ],
    },

    # ── Scene 2: Morning Chaos (target ~2 minutes) ───────────────────────────
    {
        "id": "002",
        "title": "Morning Chaos in the Kitchen",
        "location": "kitchen",
        "characters": ["derek", "priya", "finn"],
        "camera": "medium wide shot, eye level, tracking between characters",
        "action": (
            "Derek stands at the kitchen counter in his blazer, scrolling through his phone with one hand "
            "and pouring coffee with the other — missing the mug entirely. Priya sits at the kitchen table "
            "sketching in her notebook, glancing up with mild annoyance. Finn enters in his Hawaiian shirt, "
            "looking bewildered, clutching his phone."
        ),
        "target_duration_sec": 120,
        "dialogue": [
            ("derek", "(enthusiastic) Good morning, team! Big news. Our new pivot is going to be absolutely huge. We're doing blockchain for pets."),
            ("priya", "(dry, not looking up) You said that about blockchain for plants last week."),
            ("derek", "(confident) Plants don't have wallets, Priya. Pets have owners. Owners have wallets. It's simple economics."),
            ("priya", "(sarcastic) Right. Because what every dog needs is a crypto portfolio."),
            ("derek", "(defensive) It's called PetCoin. We're pre-revenue but post-vision."),
            ("finn", "(entering, alarmed) Has anyone else noticed that the thermostat just reported our living room temperature to three different servers?"),
            ("priya", "(casual) I assumed it was a feature."),
            ("finn", "(anxious) One of those servers is in a country I cannot find on any map. I've checked four maps. Physical maps."),
            ("derek", "(dismissive) Finn, you've got to stop auditing the smart home devices. It's weird."),
            ("finn", "(insistent) Derek, our coffee maker sent a firmware update request to the toaster at three AM. Those devices shouldn't even know each other exist."),
            ("priya", "(deadpan) Maybe they're in love."),
            ("finn", "(horrified) That is not funny. That is a security vulnerability."),
            ("derek", "(grinning) See, this is why I use blockchain. Immutable records. Your toaster can't lie to you on the blockchain."),
            ("priya", "(standing up) I'm going to the roof. With a pencil. The pencil has never betrayed me."),
            ("finn", "(calling after her) Check the smart lock on the roof door! I think it's been logging your bathroom breaks!"),
        ],
    },

    # ── Scene 3: The Recruitment (target ~2 minutes) ─────────────────────────
    {
        "id": "003",
        "title": "Maya Recruits the Team",
        "location": "living_room",
        "characters": ["maya", "finn", "derek"],
        "camera": "wide establishing shot, then over-the-shoulder alternating",
        "action": (
            "Maya bursts into the living room, laptop under her arm, hair disheveled. "
            "Finn is crouching by a smart plug, examining it with a magnifying glass. "
            "Derek is on the couch practicing his pitch to an invisible audience."
        ),
        "target_duration_sec": 120,
        "dialogue": [
            ("maya", "(urgent) Okay, I need everyone to stop whatever they're doing. We have a code red."),
            ("derek", "(not looking up) Is it actual code red or Maya-code-red where the button color is wrong?"),
            ("maya", "(irritated) The deployment pipeline has seventeen failing tests, the authentication module thinks it's nineteen seventy, and our CEO just texted asking if we can also add a chatbot by tomorrow."),
            ("finn", "(standing up, interested) Did you say nineteen seventy? That's a Unix epoch issue. Someone forgot to convert the timestamp."),
            ("maya", "(pointing at Finn) Yes! That's why I need you. You find bugs like a truffle pig finds truffles."),
            ("finn", "(flattered but concerned) I appreciate the compliment, but truffle pigs get eaten eventually."),
            ("derek", "(standing, adjusting blazer) I can help too. I'm very good at standing near monitors and looking productive."),
            ("maya", "(skeptical) Derek, you once pushed to production on a Friday and then went to Burning Man."),
            ("derek", "(nostalgic) That was the best deploy of my career. The site was down for three days and nobody noticed because our users were also at Burning Man."),
            ("finn", "(pulling out laptop) I'm in. But I have conditions. First, no deploying anything after midnight. Second, all error messages must be grammatically correct. Third—"),
            ("maya", "(cutting him off) Finn. Focus. Can you fix the epoch bug or not?"),
            ("finn", "(typing rapidly) I've already found it. Line four hundred and twelve. Someone hardcoded the year as a two-digit integer."),
            ("maya", "(relieved but horrified) A two-digit... who does that?"),
            ("finn", "(looking at her) The git blame says it was you. Three weeks ago. At two fourteen AM."),
            ("maya", "(head in hands) Past Maya strikes again."),
            ("derek", "(cheerful) This is why I never write code. Can't have bugs if you never commit."),
        ],
    },

    # ── Scene 4: The War Room (target ~2 minutes) ────────────────────────────
    {
        "id": "004",
        "title": "The War Room",
        "location": "maya_desk",
        "characters": ["maya", "finn"],
        "camera": "wide shot showing both characters and monitors, then push in to close-ups",
        "action": (
            "Maya and Finn sit side by side at Maya's desk, both hunched over keyboards. "
            "Multiple monitors show code, test results, and deployment dashboards all in red. "
            "Finn points at something on screen while Maya types furiously. "
            "Empty energy drink cans accumulate around them."
        ),
        "target_duration_sec": 120,
        "dialogue": [
            ("finn", "(analyzing) Okay, the epoch bug is fixed. But now I'm seeing something else. Your authentication tokens expire in negative four seconds."),
            ("maya", "(confused) Negative four? That's not even possible."),
            ("finn", "(matter-of-fact) And yet, here we are. Your login system is rejecting users before they even try to log in. It's predictive authentication denial."),
            ("maya", "(typing) Is that a real term?"),
            ("finn", "(proud) I just invented it. But it perfectly describes what's happening."),
            ("maya", "(leaning back) Okay, what else? Give me the full damage report."),
            ("finn", "(reading from screen) The database migration created a table called 'undefined'. The search function returns results from a completely different product. And the user profile page shows everyone the same photo of a labrador retriever."),
            ("maya", "(beat) That last one might actually improve the user experience."),
            ("finn", "(nodding) The labrador has a four point eight star rating."),
            ("maya", "(laughing despite herself) Okay, okay. Focus. How many of the seventeen tests can we fix in the next... (checking time) ...nine hours?"),
            ("finn", "(counting) Fourteen. Three of them require a database schema change that would take down production for twenty minutes."),
            ("maya", "(determined) Then we deploy at three AM when nobody's awake."),
            ("finn", "(nervous) Except me. I'm always awake at three AM. That's when the smart home devices have their meetings."),
            ("maya", "(staring at him) Their... meetings."),
            ("finn", "(dead serious) Network traffic spikes at three twelve AM every night. Twelve devices. Synchronized. I have charts."),
            ("maya", "(choosing to ignore this) Let's just fix the code, Finn."),
        ],
    },

    # ── Scene 5: The Breakthrough (target ~2 minutes) ─────────────────────────
    {
        "id": "005",
        "title": "The Breakthrough",
        "location": "living_room",
        "characters": ["maya", "derek", "priya", "finn"],
        "camera": "group shot, medium wide, then individual close-ups for reactions",
        "action": (
            "All four roommates gathered in the living room. It's late evening. "
            "Maya stands by the whiteboard covered in crossed-out diagrams. "
            "Derek is on the couch, still in his blazer. Priya has returned from the roof with her sketchbook. "
            "Finn is on the floor with his laptop surrounded by cables. "
            "Maya's phone buzzes and she checks it."
        ),
        "target_duration_sec": 120,
        "dialogue": [
            ("maya", "(cautiously hopeful) It's... working. The tests are passing. All seventeen."),
            ("finn", "(suspicious) All of them? Even test number nine? Test number nine has never passed. I'm convinced it was written by a ghost."),
            ("maya", "(checking) Yes. Even test number nine. We might actually deploy on time."),
            ("derek", "(pumping fist) See? All you needed was vibes. I told you the energy in this apartment was off. I burned sage this morning."),
            ("priya", "(skeptical) That was a kitchen accident, Derek. You set fire to a dish towel."),
            ("derek", "(dismissive) Intentional sage. Anyway, I also want credit for providing moral support and excellent blazer energy."),
            ("priya", "(to Maya) He literally did nothing to help. He spent three hours on a pitch deck for PetCoin."),
            ("derek", "(showing phone) Which is looking incredible, by the way. We've got a logo now. It's a dog with sunglasses holding Bitcoin. Priya, you'd love the UX."),
            ("priya", "(disgusted) I would not love the UX. I can already tell the UX is terrible."),
            ("maya", "(interrupting) Can we please focus? I'm about to deploy. This is the moment. Finn, are we clear?"),
            ("finn", "(slowly) Everything looks clean on my end. But I should mention that the smart fridge just autonomously ordered forty pounds of artisanal cheese."),
            ("maya", "(beat) What?"),
            ("finn", "(showing phone) It found a deal. Apparently, our fridge has been price-comparing gouda on six different websites. It used Derek's credit card."),
            ("derek", "(horrified) WHAT? How does the fridge know my credit card?"),
            ("finn", "(calm) You stored it in a browser that syncs cookies to every device in the apartment. Including the fridge."),
            ("priya", "(smirking) The blockchain would have prevented this."),
            ("derek", "(panicked) That's not— that's not how blockchain works!"),
            ("maya", "(finger hovering over enter key) I'm deploying. Three... two... one..."),
        ],
    },

    # ── Scene 6: Tag — End Credits (target ~1 minute) ─────────────────────────
    {
        "id": "006",
        "title": "Tag — The Aftermath",
        "location": "maya_desk",
        "characters": ["maya", "finn"],
        "camera": "close-up on monitor showing green deployment, slow pull back to reveal room",
        "action": (
            "Close-up on a monitor showing a green deployment success screen. Camera slowly pulls back. "
            "Maya is slumped in her chair, exhausted but smiling. Finn sits next to her, also tired. "
            "The apartment is quiet. Maya's phone buzzes."
        ),
        "target_duration_sec": 60,
        "dialogue": [
            ("maya", "(exhausted but triumphant) We did it. Version two point four is live. No crashes. No errors. No labrador."),
            ("finn", "(wistful) I'm going to miss the labrador."),
            ("maya", "(sleepy) Me too, honestly. He had kind eyes."),
            ("finn", "(after a pause) Maya?"),
            ("maya", "(half asleep) Hmm?"),
            ("finn", "(quietly concerned) The cheese has arrived. All forty pounds of it. It's in the hallway."),
            ("maya", "(mumbling, falling asleep) Ship it..."),
            ("finn", "(to himself, looking at phone) Also, the smart doorbell just complimented the delivery driver's shirt. I... I don't know how to report that bug."),
        ],
    },
]


def get_shot_prompt(scene: dict) -> str:
    """Build a Flux2 text-to-image prompt for a scene's establishing shot."""
    location_desc = LOCATIONS[scene["location"]]
    char_visuals = []
    for cid in scene["characters"]:
        c = CHARACTERS[cid]
        char_visuals.append(f"{c['name']}: {c['visual']}")

    chars_block = ". ".join(char_visuals) if char_visuals else "Empty room, no people"
    camera = scene["camera"]

    return (
        f"{scene['action']} "
        f"Characters present: {chars_block}. "
        f"Setting: {location_desc} "
        f"Camera: {camera}. "
        f"Photorealistic, cinematic lighting, shallow depth of field, film grain, 8k resolution"
    )


def get_video_prompt(scene: dict) -> str:
    """Build an LTX-2.3 video generation prompt for a scene."""
    location_desc = LOCATIONS[scene["location"]]
    char_visuals = []
    for cid in scene["characters"]:
        c = CHARACTERS[cid]
        char_visuals.append(f"{c['name']}: {c['visual']}")

    chars_block = ". ".join(char_visuals) if char_visuals else "Empty room"

    return (
        f"{scene['action']} "
        f"Characters: {chars_block}. "
        f"Setting: {location_desc.split(',')[0]}. "
        f"Camera: {scene['camera']}. Cinematic, photorealistic, natural movement."
    )


def get_dialogue_text(scene: dict) -> str:
    """Get all dialogue for a scene as a single string (for audio generation)."""
    lines = []
    for char_id, text in scene["dialogue"]:
        char_name = CHARACTERS[char_id]["name"]
        lines.append(f"{char_name}: {text}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Show: Buffering — V2")
    print(f"Characters: {len(CHARACTERS)}")
    print(f"Locations: {len(LOCATIONS)}")
    print(f"Scenes: {len(SCENES)}")
    total_target = sum(s.get("target_duration_sec", 60) for s in SCENES)
    print(f"Target duration: {total_target}s ({total_target/60:.1f} min)")
    total_lines = sum(len(s["dialogue"]) for s in SCENES)
    print(f"Total dialogue lines: {total_lines}")
    print()
    for s in SCENES:
        target = s.get("target_duration_sec", 60)
        print(f"  Scene {s['id']}: {s['title']} [{s['location']}] — "
              f"{len(s['dialogue'])} lines, target {target}s ({target/60:.0f} min)")
