# Setup

1. Create a public repo named exactly `lewis-shearer` on GitHub (that's the special profile repo).
2. Push this folder to it:
   ```bash
   git init && git add . && git commit -m "Profile README card" && git branch -M main
   git remote add origin https://github.com/lewis-shearer/lewis-shearer.git && git push -u origin main
   ```
3. Repo → Settings → Actions → General → Workflow permissions → "Read and write". Then Actions tab → "Update README card" → Run workflow.

## Editing
- `data/stack.json`: icon slugs from simpleicons.org, grouped (a dot separates groups).
- `data/profile.json`: name, tagline, languages to ignore.
- `data/tokens.json`: refresh with `/usr/bin/python3 scripts/token_spend.py`, commit, push. Delete the file to hide that section.
