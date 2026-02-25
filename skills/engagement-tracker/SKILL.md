---
name: engagement-tracker
description: Generate LinkedIn Post Engagement Intelligence dashboards from PhantomBuster data. Tracks who engages with thought leader posts, cross-references against target accounts, deploys to Netlify.
---

# Engagement Tracker Skill

Generate a LinkedIn Post Engagement Intelligence dashboard by following these 5 phases sequentially. Confirm with the user at each phase before proceeding.

---

## Phase 1: Configure

Collect the following information from the user:

| Field | Description | Example |
|-------|-------------|---------|
| `company_name` | The company this dashboard is for | Acme Corp |
| `influencer_name` | Name of the thought leader | Jane Smith |
| `influencer_role` | Their LinkedIn headline or tagline | VP of Sales at Acme Corp |
| `brand.primary_color` | Brand primary color (hex) | #2563EB |
| `badge_label` | Dashboard badge text (e.g., "Sales Intelligence", "Demand Gen Intelligence") | Sales Intelligence |
| `target_audience_label` | Primary audience category (HR/People, Sales/Revenue, Marketing, etc.) | Sales/Revenue |
| `bob_description` | How to describe the target accounts (e.g., "target accounts", "dream clients") | target accounts |
| `bob_count` | Number of accounts in the Book of Business | 500 |
| `password` | Password for dashboard access | AcmeDemo2026! |

**Steps:**

1. Ask the user for each field (or accept a bulk answer with all fields)
2. Generate the full client config JSON including computed color variants:
   - `primary_color_dark`: Darken primary by ~15%
   - `primary_color_light`: Lighten primary to ~90% lightness
   - `primary_color_mid`: Lighten primary to ~60% lightness
   - `accent_color`: Complementary color (default: teal `#059669`)
   - `accent_color_light`: Light variant of accent
3. Save the config to `${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/client-configs/{client-slug}.json`
   - `client-slug` is the company name lowercased, spaces replaced with hyphens, special characters removed
4. Show the config to the user for confirmation before proceeding

---

## Phase 2: Get the Data

Reference `${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/data-format.md` for full CSV specifications.

**Guide the user through PhantomBuster setup:**

1. Tell them they need two PhantomBuster Phantoms:
   - **LinkedIn Post Likers** -- extracts everyone who liked their posts
   - **LinkedIn Post Commenters** -- extracts everyone who commented + their comment text
2. Input for both Phantoms: a list of LinkedIn post URLs they want to track
3. Run both Phantoms, then download the CSV results from each
4. Merge the two exports into a single `engagers.csv` (see data-format.md for merging instructions)

**Guide them through preparing the 3 CSV files:**

1. **posts.csv** -- They create this manually with:
   - `post_id`: The activity ID from each LinkedIn post URL
   - `post_url`: Full URL
   - `title`: First ~50 characters / hook of the post
   - `content`: Full post text
   - `post_date`: Publication date (YYYY-MM-DD)

2. **engagers.csv** -- From the merged PhantomBuster export with:
   - `post_id`, `name`, `occupation`, `company`, `profile_url`
   - `has_liked`, `has_commented`, `comment`, `comment_url`, `degree`

3. **bob.csv** -- From their CRM or a manual list with:
   - `company_name` (required), `fire` (priority 0-3), `tier` (A/B/C)

**Then ask:** "Where have you placed the 3 CSV files? Give me the file paths."

---

## Phase 3: Build

Run the build script with the user's data:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/build-dashboard.py \
  --config ${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/client-configs/{client-slug}.json \
  --posts {posts-csv-path} \
  --engagers {engagers-csv-path} \
  --bob {bob-csv-path} \
  --template ${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/dashboard-template.html \
  --output ./output/index.html
```

Replace `{client-slug}`, `{posts-csv-path}`, `{engagers-csv-path}`, and `{bob-csv-path}` with the actual paths.

**After the build completes, show a summary:**

- Total posts analyzed
- Total unique engagers
- BOB matches found
- Top 5 scoring leads (name, company, score)
- Category breakdown (internal, hr, executive, marketing, sales, other)

If the build fails, read the error output and help the user fix their CSV files or config.

---

## Phase 4: Preview

Start a local HTTP server so the user can preview the dashboard:

```bash
python3 -m http.server 8080 --directory ./output
```

Tell the user:
> Open http://localhost:8080 in your browser. Enter the password from your config to view the dashboard.

Ask: "Are you happy with the result, or do you want to make adjustments?"

**If adjustments are needed:**
- Config changes (colors, labels) -- update the config JSON, then rebuild
- Data changes (fix CSV issues) -- guide them to fix their CSVs, then rebuild
- Layout/design changes -- note that the template HTML can be edited directly at `${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/dashboard-template.html`

Stop the HTTP server when done previewing (`Ctrl+C` or kill the process).

---

## Phase 5: Deploy

Reference `${CLAUDE_PLUGIN_ROOT}/skills/engagement-tracker/references/netlify-guide.md` for full deployment steps.

**Guide the user through deployment:**

1. **Netlify account**: Confirm they have one, or help them sign up (free tier is fine)
2. **Deploy method**: Recommend drag & drop for first-timers, CLI for repeat deployments
   - **Drag & drop**: Go to app.netlify.com/drop, drag the `output/` folder
   - **CLI**: `npm install -g netlify-cli && netlify login && netlify deploy --prod --dir=./output`
3. **Custom site name**: Help them set a readable name (e.g., `acme-engagement`)
4. **Confirm deployment**: Ask them to share the live URL

**When deployment is confirmed, provide a summary:**

```
Dashboard deployed successfully.

URL: https://{site-name}.netlify.app
Password: {password}

Stats:
- {X} posts tracked
- {Y} unique engagers
- {Z} BOB matches
- Top lead: {name} ({company}) -- score {score}

Share the URL and password with your stakeholders.
```

---

## Important Notes

- **Privacy**: All data processing happens locally. No engagement data is sent to external APIs (beyond PhantomBuster's initial collection).
- **Dependencies**: The build script uses only Python standard library (no pip install needed). Requires Python 3.6+.
- **Self-contained output**: The dashboard is a single HTML file with no external dependencies except Google Fonts. It works offline after initial load.
- **Password protection**: The built-in password gate is client-side JavaScript. This is sufficient for internal dashboards. For server-side auth, use Netlify Pro with Basic Auth.
- **Updating**: To add new posts or engagers, update the CSV files and re-run from Phase 3. The build script generates a fresh dashboard each time.
