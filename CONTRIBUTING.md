# Contributing to Thought Leader

Thanks for helping improve the Thought Leader plugin. This guide covers how to contribute.

---

## Fork & Clone

```bash
git clone https://github.com/detumnu-ai/thought-leader.git
cd thought-leader
```

---

## Create a Branch

```bash
git checkout -b feature/your-description
# or
git checkout -b fix/your-description
```

---

## What to Change

| What you want to change | File to edit |
|--------------------------|-------------|
| Dashboard design and layout | `skills/engagement-tracker/references/dashboard-template.html` |
| Data processing and scoring | `skills/engagement-tracker/references/build-dashboard.py` |
| Skill workflow (the 5 phases) | `skills/engagement-tracker/SKILL.md` |
| Slash command behavior | `commands/generate-tracker.md` |
| Main documentation | `README.md` |
| Data format specs | `skills/engagement-tracker/references/data-format.md` |
| Deployment guide | `skills/engagement-tracker/references/netlify-guide.md` |

---

## Test Your Changes

### Test the build script

Run the build with the example config and sample data:

```bash
python3 skills/engagement-tracker/references/build-dashboard.py \
  --config skills/engagement-tracker/references/client-configs/_example.json \
  --posts /path/to/your/test-posts.csv \
  --engagers /path/to/your/test-engagers.csv \
  --bob /path/to/your/test-bob.csv \
  --template skills/engagement-tracker/references/dashboard-template.html \
  --output ./output/index.html
```

### Verify the output

1. Open `output/index.html` in your browser
2. Check that the password gate works
3. Verify all sections render correctly (stats, tables, charts)
4. Search for `{{` in the output file -- no template markers should remain
5. Test with edge cases: empty CSVs, missing optional columns, special characters in names

### Test the skill workflow

1. Install the plugin locally: point Claude Code to your local clone
2. Run `/thought-leader:generate` and walk through all 5 phases
3. Verify each phase completes correctly

---

## Commit & Push

```bash
git add .
git commit -m "feat: description of your change"
git push origin feature/your-description
```

---

## Create a Pull Request

1. Go to [github.com/detumnu-ai/thought-leader](https://github.com/detumnu-ai/thought-leader)
2. Click **Compare & pull request**
3. Fill in the PR template:
   - **What changed**: Describe the change
   - **Why**: Explain the motivation
   - **How to test**: Steps to verify the change works
4. Submit the PR

---

## PR Review

- PRs need one approval before merge
- Reviewers will check for correctness, completeness, and that no template markers (`{{`) leak into output
- Address review feedback by pushing additional commits to the same branch

---

## Commit Convention

Use conventional commit prefixes:

| Prefix | Use for |
|--------|---------|
| `feat:` | New features (e.g., new dashboard section, new scoring factor) |
| `fix:` | Bug fixes (e.g., CSV parsing edge case, scoring error) |
| `docs:` | Documentation changes (e.g., README updates, new reference docs) |
| `refactor:` | Code restructuring without behavior change |

**Examples:**
```
feat: add engagement trend chart to dashboard
fix: handle UTF-8 BOM in CSV files
docs: add troubleshooting section for Excel exports
refactor: extract scoring logic into separate function
```

---

## Questions?

Tag **@detumnu-ai** in your PR or reach out on Slack.
