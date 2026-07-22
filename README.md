# CAAI Conference Deadlines

Static deadline tracker for conferences recommended by the Chinese Association for Artificial Intelligence.

- Conference scope comes from `中国人工智能学会推荐国际学术会议和期刊目录.pdf`.
- Journals are excluded.
- Deadline details are matched from the public ccfddl RSS feed when the DBLP conference key overlaps.
- Conferences without a current matched deadline remain visible as `TBD`.

Open `index.html` directly, or run a local static server:

```bash
python3 -m http.server 5173
```

## Automatic Updates

`scripts/update_data.py` refreshes `data.js` from the public ccfddl RSS feed. The repository includes two GitHub Actions workflows:

- `.github/workflows/update-data.yml` runs every day at 18:23 UTC and commits refreshed `data.js` when it changes.
- `.github/workflows/pages.yml` deploys the static site to GitHub Pages on every push to `main`.
