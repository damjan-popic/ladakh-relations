# GitHub Pages deployment

## Static branch deployment

Upload the repository contents to GitHub. Make sure these files are in the repository root:

```text
index.html
app.js
style.css
.nojekyll
data/
docs/
scripts/
corpus/
schema/
```

Then enable **Settings → Pages → Deploy from branch → main → root**.

## GitHub Actions deployment

A workflow is included in `.github/workflows/pages.yml`. To use it, change Pages source to **GitHub Actions**.

## Important

If your corpus contains copyrighted transcriptions, do not commit them to a public repo. The `.gitignore` excludes `corpus/raw/*.txt`, `corpus/normalized/*.txt`, `corpus/cleaned/*.txt`, and private annotation exports by default.
