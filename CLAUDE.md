# Minecraft-Style Convention (PROJECT RULE — applies to every change, every session)

Ourcraft 2 is a Minecraft clone. **All gameplay content and mechanics MUST follow Minecraft Java
Edition conventions** unless the user explicitly asks otherwise. This is a standing instruction: it
applies in every future chat, to every new block, item, mob, recipe, or system added later
(redstone, nether, enchanting, brewing, etc. should all behave like Minecraft when added).

When adding or changing anything, match Minecraft for:
- **Ore generation** — Y-level distribution, rarity, vein sizes, deepslate variants below y≈8.
  (See `world_generator.py` `_ORE_SPECS` / `_DEEPSLATE_ORE_MAP`. e.g. copper peaks ~y48, diamond
  near bedrock, gold low, coal high.)
- **Drop tables** — what a block/mob drops, counts, tool-gated drops (ore needs the right pickaxe
  tier or drops nothing). See `player.py` `_BLOCK_DROP_ITEM` and `items.py` `BLOCK_TOOL_INFO`.
- **Tool tiers & gating** — wood < stone < iron < diamond; mining speed and which tier can harvest
  which block follow Minecraft (`items.py` `ToolTier`, `BLOCK_TOOL_INFO`, `get_tool_multiplier`).
- **Crafting recipe shapes** — recipe patterns match Minecraft exactly (`recipes.py`). Tools, armor
  (helmet `XXX/X.X`, chestplate `X.X/XXX/XXX`, leggings `XXX/X.X/X.X`, boots `X.X/X.X`), storage
  blocks (9→block, block→9), smelting inputs/outputs.
- **Item properties** — stack sizes (tools/armor = 1, most items = 64), durability values, armor
  defense points (full diamond set = 20 pts ≈ 80% reduction via `dmg*(1-min(20,pts)/25)`), food
  hunger/saturation. See `items.py` `ItemDef`.
- **Block properties** — hardness, correct tool, transparency/occlusion (leaves are alpha-cutout
  and non-occluding, water/lava translucent), light behavior.
- **Mob behavior & physics** — health, AI, drops, spawn rules, gravity/knockback should mirror
  Minecraft.
- **Materials Minecraft doesn't support** — do NOT invent non-Minecraft recipes (e.g. copper makes
  ingots/blocks/decorative items, NOT tools or armor in Java Edition). Ask the user before deviating.

If a requested feature has no Minecraft equivalent, ask the user how it should behave rather than
guessing.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
