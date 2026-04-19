# Astrology content system

This folder is the editable knowledge layer for the app.

## How to use it
- `astrology-basics/` holds stable meanings like planets, signs, houses, aspects, rulers, elements, and modalities.
- `engine/` holds interpretation order, output templates, and topic-specific rule sets.
- Update these JSON files when your astrology method grows instead of hardcoding new meanings into Python files.

## First files to expand
- `astrology-basics/signs.json`
- `astrology-basics/houses.json`
- `engine/relationship_rules.json`
- `engine/output_templates.json`

## Current limitation
Detailed long-form interpretations in `app/interpretation_service.py` still exist for richer text output.
The app now reads the shared core definitions from this folder so the structure is ready for incremental migration.
