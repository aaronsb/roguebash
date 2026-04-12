---
name: session
description: "Start, save, resume, or create D&D 5e campaign sessions. Manages the full session lifecycle."
---

# /session — Session Management

## Commands
- `/session start` or `/session resume` — Start or resume a session
- `/session new {campaign_name}` — Create a new campaign
- `/session save` — Save current session state
- `/session end` — End session with full save and logging

## Starting a Session

1. List all campaigns: `ls games/`
2. If multiple campaigns exist, ask which to play
3. Read these files from the chosen campaign:
   - `session-state.md` — where we left off
   - `calendar.md` — in-game date, time, weather
   - `quests/active.md` — current quests
   - `campaign.md` — campaign overview and tone
4. Present a "Last time..." summary from session-state.md
5. Announce current date, time of day, weather, and location
6. Ask: "What would you like to do?"

## Creating a New Campaign

1. Create the full directory structure under `games/{name}/`:
   ```
   campaign.md, session-state.md, calendar.md
   players/ (party.md)
   world/ (overview.md, regions/, locations/, factions/, npcs/npc-index.md, lore/)
   sessions/
   quests/ (active.md, completed.md, failed.md, hidden.md, rumors.md)
   combat/ (encounter-log.md, prepared/)
   economy/ (party-inventory.md, shops/)
   relationships/ (reputation.md, npc-attitudes.md)
   random-tables/
   narrative/ (arcs.md, threads.md, themes.md, secrets.md)
   ```

2. Prompt the player for campaign details:
   - Campaign name and setting (homebrew or published adventure?)
   - Tone: heroic, dark, comedic, political, sandbox, etc.
   - Starting level
   - Number of players and their characters

3. Guide character creation for each PC:
   - Race (reference `rules/races/`)
   - Class (reference `rules/classes/`)
   - Background (reference `rules/backgrounds/`)
   - Ability scores (point buy, standard array, or roll with `/roll stats`)
   - Equipment and spells
   - Personality traits, ideals, bonds, flaws
   - Write each character sheet to `players/{name}.md`

4. Populate initial campaign files
5. Begin Session 1 with an opening scene

## Saving a Session

Update these files:
1. `session-state.md`:
   - Current location
   - Party status (HP, conditions, key resources remaining)
   - Immediate situation description
   - Pending decisions
   - Active timers
   - Recent events summary (last 2-3 sessions)
2. `calendar.md`: current in-game date, time, weather
3. Any changed quest files
4. Any changed NPC files
5. Confirm: "Session state saved."

## Ending a Session

1. Determine session number (count directories in `sessions/`)
2. Create `sessions/session-{NNN}/` with:
   - `log.md` — narrative log of what happened this session
   - `summary.md` — 1-page summary: key events, decisions, consequences
   - `rewards.md` — XP earned, loot acquired, levels gained
   - `notes.md` — DM notes: follow-ups, NPC reactions, consequences to track
3. Perform a full save (same as `/session save`)
4. Summarize: "Session {N} complete. {brief summary}. See you next time!"
