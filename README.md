# Thought Leader Engagement Tracker

A Claude Code plugin that generates **LinkedIn Post Engagement Intelligence dashboards**. Track who engages with a thought leader's LinkedIn posts, cross-reference against your company's Book of Business (target accounts), and deploy an interactive web dashboard to share with your team.

The dashboard shows engagement patterns, identifies hot leads from target accounts, and surfaces demand gen signals — all from LinkedIn post data exported via PhantomBuster.

## Quick Start

```bash
# 1. Install the plugin
claude plugin install thought-leader@detumnu-ai

# 2. Generate a dashboard
/thought-leader:generate acme

# 3. Follow the guided 5-phase workflow
```

The guided workflow walks you through configuration, data preparation, building, previewing, and deploying your dashboard.

## How It Works

1. **Configure** — Set your company name, influencer, brand colors, and target audience
2. **Get the data** — Export engagement data from PhantomBuster + prepare your Book of Business
3. **Build** — The build script processes CSVs and generates a self-contained HTML dashboard
4. **Preview** — Review locally in your browser
5. **Deploy** — Drag & drop to Netlify for a live, password-protected URL

## Getting Your Data (PhantomBuster)

You run **4 PhantomBuster Phantoms** in sequence. Each one feeds into the next.

### Step 1: Post Scraper

**Phantom:** LinkedIn Post Scraper

Scrape the thought leader's posts to get content, dates, and post URLs. This gives you the `posts.csv` data.

- **Input:** The thought leader's LinkedIn profile URL
- **Settings:** Set a date range (e.g., posts from December onwards)
- **Output:** CSV with post URLs, content, dates, engagement counts
- **Why:** You need post URLs for steps 2-3, and post dates for the dashboard's time filter

> **Alternative:** You can also use the [Cowork Chrome extension](https://cowork.com) or build a custom Chrome extension to scrape posts. PhantomBuster is just the most reliable option.

### Step 2: Likers Export

**Phantom:** LinkedIn Post Likers

Scrape everyone who liked each post.

- **Input:** Post URLs from Step 1 (copy the post URL column)
- **Output:** CSV with name, occupation, profile URL for every liker per post
- **Tip:** Run this for all posts at once — the Phantom handles multiple URLs

### Step 3: Commenters Export

**Phantom:** LinkedIn Post Commenters

Scrape everyone who commented, including their comment text.

- **Input:** Same post URLs from Step 1
- **Output:** CSV with name, occupation, profile URL, comment text, comment URL per post
- **Tip:** Run in parallel with Step 2 to save time

### Step 4: Profile Scraper

**Phantom:** LinkedIn Profile Scraper

Enrich the profiles from Steps 2 and 3 with full company names, titles, and connection degree.

- **Input:** Profile URLs from the liker + commenter exports (deduplicate first to avoid scraping the same person twice)
- **Output:** Enriched CSV with current company, full title, connection degree
- **Why:** LinkedIn headlines are often incomplete (missing company name). The profile scraper fills in the gaps, which improves BOB matching accuracy.

### Preparing the 3 Input CSVs

After running all 4 Phantoms, you prepare 3 files for the build script:

| File | Source | What it contains |
|------|--------|-----------------|
| `posts.csv` | From Phantom 1 (Post Scraper) | Post IDs, URLs, titles, content, dates |
| `engagers.csv` | Merge Phantoms 2 + 3, enrich with Phantom 4 | All engagement data per post |
| `bob.csv` | Your CRM / target account list | Company names with priority scores |

**Merging likers + commenters into `engagers.csv`:**
1. Take the likers CSV (Phantom 2) — add column `has_liked=true`, `has_commented=false`
2. Take the commenters CSV (Phantom 3) — add column `has_liked=false`, `has_commented=true`
3. Combine both into one file
4. Enrich with company/degree data from the Profile Scraper (Phantom 4)
5. For people who appear in both, you can merge into a single row or keep separate — the build script deduplicates by profile URL within each post

See `skills/engagement-tracker/references/data-format.md` for full column specs, column mapping, and examples.

## CSV Format Reference

### posts.csv

| Column | Required | Description |
|--------|----------|-------------|
| post_id | Yes | LinkedIn activity ID (from the post URL) |
| post_url | Yes | Full LinkedIn post URL |
| title | Yes | Short title/hook (first ~50 chars of post) |
| content | Yes | Full post text |
| post_date | Yes | YYYY-MM-DD format |

### engagers.csv

| Column | Required | Description |
|--------|----------|-------------|
| post_id | Yes | Which post this engagement belongs to |
| name | Yes | Full name |
| occupation | Yes | LinkedIn headline |
| company | No | Company name (extracted from headline if empty) |
| profile_url | Yes | LinkedIn profile URL |
| has_liked | No | true/false (default: true) |
| has_commented | No | true/false (default: false) |
| comment | No | Comment text |
| comment_url | No | Direct link to comment |
| degree | No | Connection degree (1st, 2nd, 3rd) |

### bob.csv

| Column | Required | Description |
|--------|----------|-------------|
| company_name | Yes | Target account company name |
| fire | No | Priority score 0-3 (default: 1) |
| tier | No | Account tier A/B/C (default: empty) |

## Client Configuration

All settings are stored in a JSON config file. The guided workflow creates this for you.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| company_name | Yes | — | Your company name |
| influencer_name | Yes | — | The thought leader's name |
| influencer_role | No | "" | Their LinkedIn headline/tagline |
| brand.primary_color | No | #6B2DEF | Main brand color (hex) |
| brand.primary_color_dark | No | #5321C9 | Dark variant |
| brand.primary_color_light | No | #EDE5FF | Light variant |
| brand.primary_color_mid | No | #C4A8FF | Mid variant |
| brand.accent_color | No | #007A7A | Secondary/accent color |
| brand.accent_color_light | No | #E0F2F2 | Accent light variant |
| badge_label | No | Demand Gen Intelligence | Nav badge text |
| bob_description | No | target accounts | BOB description label |
| bob_count | No | (from CSV) | Total target accounts |
| target_audience_label | No | HR/People | Primary audience filter label |
| password | No | "" | Dashboard password (empty = no gate) |
| netlify_site_name | No | "" | Custom Netlify subdomain |

See `skills/engagement-tracker/references/client-configs/_template.json` for the full template and `_example.json` for a working example.

## Deployment

The build produces a single `output/index.html` file. Deploy it anywhere that serves static HTML.

**Netlify (recommended):**
1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag the `output/` folder onto the page
3. Your dashboard is live

Or via CLI:
```bash
npx netlify-cli deploy --prod --dir=./output
```

The dashboard includes a built-in password gate (set in your client config). See `skills/engagement-tracker/references/netlify-guide.md` for the full deployment guide including custom domains.

## Example

Using the included `_example.json` config (fictional "Acme Corp" with influencer "Jane Smith"):

```bash
python3 skills/engagement-tracker/references/build-dashboard.py \
  --config skills/engagement-tracker/references/client-configs/_example.json \
  --posts posts.csv \
  --engagers engagers.csv \
  --bob bob.csv \
  --template skills/engagement-tracker/references/dashboard-template.html \
  --output ./output/index.html
```

Output:
```
Dashboard built successfully!
  Posts:        2
  Engagers:     12
  BOB matches:  7
  Output:       ./output/index.html
```

## Dashboard Features

- **Post slider** — Browse posts ranked by engagement, click to filter
- **Time filtering** — Filter by date range (30/60/90 days or custom)
- **BOB matching** — Fuzzy company name matching against your target account list
- **Audience breakdown** — Category distribution (HR, Marketing, Sales, Executive, Internal)
- **Demand gen signals** — Auto-detected hot intent signals (BOB + target audience overlap)
- **Engager cards** — Scored 0-10 with tags, comments, and BOB match indicators
- **Search & filter** — Filter by category, BOB status, comments, hot intent
- **Password protection** — Optional client-side password gate
- **Fully self-contained** — Single HTML file, no server required

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Missing column" error | Check CSV headers match the expected format (case-sensitive) |
| No BOB matches showing | Verify company names in `bob.csv` closely match those in engager headlines |
| Password not working | Check the `password` field in your client config JSON |
| Dashboard shows no data | Verify `post_id` values in `engagers.csv` match those in `posts.csv` |
| Build script won't run | Ensure Python 3.6+ is installed (`python3 --version`) |
| Encoding errors | Save CSVs as UTF-8 (PhantomBuster exports are UTF-8 by default) |

## Contributing

We welcome improvements! See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR workflow.

## License

MIT — see [LICENSE](LICENSE).
