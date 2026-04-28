# Corpus and annotation workflow

## Add transcriptions

Copy text files into `corpus/raw/`, then run:

```bash
python scripts/normalize_texts.py corpus/raw corpus/normalized
python scripts/rebuild_all.py
```

If you already have clean transcriptions, place them directly into `corpus/normalized/` or `corpus/cleaned/`.

## Review candidate links

Open the site locally or on GitHub Pages, go to **Candidate links**, edit statuses and notes, then export the review file.

Recommended statuses:

- `accepted`
- `rejected`
- `needs_context`
- `duplicate_existing`
- `uncertain`

Put exported reviews in `corpus/review/` or `corpus/annotated/`.

## Add context snippets locally

For private/local annotation with snippets:

```bash
python scripts/rebuild_all.py --include-context
```

Do this only for local/private work unless the text rights are clear.
