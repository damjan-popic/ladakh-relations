# Corpus workspace

This directory is the local/private text workspace.

Recommended flow:

1. Put OCR/transcribed texts in `corpus/raw/`.
2. Run `python scripts/normalize_texts.py corpus/raw corpus/normalized`.
3. Manually clean improved versions into `corpus/cleaned/` when needed.
4. Store reviewed annotation JSON/CSV in `corpus/annotated/`.
5. Run `python scripts/rebuild_all.py` to refresh public `data/*.json` files.

By default, `.gitignore` excludes text files in these corpus folders so that copyrighted/private transcriptions are not accidentally published on GitHub Pages. The public site uses derived metadata in `data/` instead.
