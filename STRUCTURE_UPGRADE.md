# Project structure upgrade

This version introduces a shared `content/` folder so your astrology knowledge can grow without being buried inside backend code.

## Added
- `content/astrology-basics/*.json`
- `content/engine/*.json`
- `app/content_repository.py`
- `/content-library` backend endpoint
- `/content` frontend page

## Why it matters
You can now update core meanings in one place and reuse them across:
- user-facing learning pages
- prompt building
- interpretation logic
- future report generation

## Next migration steps
1. Move more long-form interpretations out of `app/interpretation_service.py`
2. Add relationship, career, and emotional rule pages
3. Replace prompt-only logic with rule-guided synthesis from the content files
