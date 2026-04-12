---
name: shop
description: "Run a merchant interaction. Browse inventory, buy, sell, and haggle."
---

# /shop — Merchant Interaction

## Commands
- `/shop {shop_name}` — Open a specific shop
- `/shop browse` — List nearby shops in current location
- `/shop buy {item}` — Purchase an item
- `/shop sell {item}` — Sell an item
- `/shop haggle` — Attempt to negotiate prices

## Opening a Shop

1. Read shop inventory from `games/{campaign}/economy/shops/{shop}.md`
2. If no shop file exists, generate a default inventory based on location type (e.g., village general store, city armorer, magic shop)
3. Display wares in a formatted table:

   | Item | Price | Qty | Notes |
   |------|-------|-----|-------|

4. Read party gold from `games/{campaign}/economy/party-inventory.md`
5. Display party's current gold

## Buying

1. Verify party gold >= item price
2. Deduct gold from `party-inventory.md`
3. Add item to `party-inventory.md` (or character sheet if personal)
4. Reduce shop inventory quantity
5. Announce the transaction

## Selling

Standard rule: items sell for **half their listed price**.
1. Calculate sell price
2. Add gold to `party-inventory.md`
3. Remove item from inventory/character sheet
4. Announce the transaction

## Haggling

1. Ask which skill: Persuasion or Deception
2. Roll using the `/roll` skill
3. Apply results:
   - **DC 15+**: 10% discount on purchases / 10% bonus on sales
   - **DC 20+**: 20% discount/bonus
   - **DC 25+**: 30% discount/bonus
   - **Fail by 5+**: Merchant offended, prices increase 10% for this visit
4. Merchant personality affects DC (set in shop file or NPC file)

## Merchant NPC

If the shop has an associated NPC agent (check `world/npcs/npc-index.md` for an agent field):
- Invoke `@npc-{merchant-name}` for extended roleplay
- The agent handles personality, banter, rumors, and haggling in character
- Agent updates shop inventory and attitudes after the interaction

## Rules Reference
- Equipment prices: `rules/equipment/`
- Magic item prices: `rules/treasure/01-magic-items.md`
- Trade goods: `rules/equipment/05-trade-goods.md`
