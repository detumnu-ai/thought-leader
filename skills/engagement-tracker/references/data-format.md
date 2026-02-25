# Data Format Reference

This document specifies the 3 CSV input formats and the full PhantomBuster pipeline for collecting LinkedIn engagement data.

---

## PhantomBuster Pipeline (4 Phantoms)

You run 4 Phantoms in sequence. Each one feeds into the next.

### Phantom 1: LinkedIn Post Scraper

Scrapes the thought leader's LinkedIn posts to get content, dates, and URLs.

- **Input:** The thought leader's LinkedIn profile URL
- **Settings:** Set a date range (e.g., "posts from December 2025 onwards") to limit scope
- **Output:** CSV with post URLs, full post content, publication dates, engagement counts
- **Why this matters:** You need the post URLs as input for Phantoms 2 and 3. The post dates power the dashboard's time filter (30/60/90 days).

> **Alternative:** You can also collect posts using the Cowork Chrome extension or a custom Chrome extension. PhantomBuster is the most reliable automated option.

### Phantom 2: LinkedIn Post Likers

Extracts everyone who liked each post.

- **Input:** Post URLs from Phantom 1 (copy the post URL column into the Phantom's input)
- **Output:** CSV with `name`, `occupation`, `profileUrl`, `postUrl` for every liker
- **Tip:** You can run all post URLs at once — the Phantom processes them sequentially

### Phantom 3: LinkedIn Post Commenters

Extracts all commenters and their comment text from the same posts.

- **Input:** Same post URLs from Phantom 1
- **Output:** CSV with `name`, `occupation`, `profileUrl`, `comment`, `commentUrl`, `postUrl`
- **Tip:** Run this in parallel with Phantom 2 to save time — they don't depend on each other

### Phantom 4: LinkedIn Profile Scraper

Enriches the profiles from Phantoms 2 and 3 with complete company names, titles, and connection degree.

- **Input:** Deduplicated profile URLs from the liker + commenter exports. Combine the `profileUrl` columns, remove duplicates, then feed into this Phantom.
- **Output:** CSV with current company name, full job title, connection degree, and other profile data
- **Why this matters:** LinkedIn headlines are often incomplete (e.g., "Marketing Leader" without a company name). The profile scraper fills in the gaps, which dramatically improves BOB (Book of Business) matching accuracy.

### How to Export

1. Go to [PhantomBuster](https://phantombuster.com) and open each Phantom's results page
2. Click **Download CSV** to export the full result set
3. Save each file locally:
   - Phantom 1 → `posts-export.csv`
   - Phantom 2 → `likers-export.csv`
   - Phantom 3 → `commenters-export.csv`
   - Phantom 4 → `profiles-export.csv`

---

## Preparing the 3 Input CSVs

After running all 4 Phantoms, you prepare 3 files for the build script.

### posts.csv — From Phantom 1

Take the Post Scraper output and map it to the `posts.csv` format (see column spec below). You need the post ID (activity number from the URL), the full URL, a short title, the full content, and the date.

### engagers.csv — Merge Phantoms 2 + 3 + 4

Combine the liker and commenter exports into a single `engagers.csv`, enriched with profile data.

**Step-by-step:**

1. Take `likers-export.csv` (Phantom 2) — add columns `has_liked=true`, `has_commented=false`
2. Take `commenters-export.csv` (Phantom 3) — add columns `has_liked=false`, `has_commented=true`
3. Combine both into one file
4. Enrich with `profiles-export.csv` (Phantom 4) — match by `profileUrl` to fill in company names, connection degree, and full titles
5. Map PhantomBuster columns to the `engagers.csv` format (see mapping table below)

**Handling duplicates:** If someone both liked AND commented on the same post, you can either:
- **Option A (recommended):** Merge into a single row with `has_liked=true`, `has_commented=true`
- **Option B (also fine):** Keep separate rows — the build script deduplicates by `profile_url` within each post

### bob.csv — From Your CRM

Export your target account list from your CRM, or create manually. Just needs company names with optional priority/tier.

### Mapping PhantomBuster Columns

| PhantomBuster Column | engagers.csv Column |
|---------------------|---------------------|
| `postUrl` | `post_id` (extract the activity ID from the URL) |
| `name` or `firstName` + `lastName` | `name` |
| `occupation` | `occupation` |
| `companyName` | `company` |
| `profileUrl` | `profile_url` |
| `comment` | `comment` |
| `commentUrl` | `comment_url` |
| `degree` | `degree` |

Extract the `post_id` from the LinkedIn post URL. The activity ID is the numeric string in the URL path, e.g., from `https://www.linkedin.com/feed/update/urn:li:activity:7654321098765432100/` the post_id is `7654321098765432100`.

---

## CSV Specifications

### posts.csv (From Phantom 1: Post Scraper)

Map the Post Scraper output to this format. Extract the post ID (activity number) from each URL.

| Column | Required | Description |
|--------|----------|-------------|
| `post_id` | Yes | LinkedIn activity ID extracted from the post URL |
| `post_url` | Yes | Full LinkedIn post URL |
| `title` | Yes | Short title or hook (first ~50 characters of the post) |
| `content` | Yes | Full post text |
| `post_date` | Yes | Publication date in `YYYY-MM-DD` format |

**Example:**

```csv
post_id,post_url,title,content,post_date
7654321098765432100,https://www.linkedin.com/feed/update/urn:li:activity:7654321098765432100/,Stop chasing MQLs,"Full post text goes here...",2026-02-15
```

### engagers.csv (Merged from Phantoms 2 + 3 + 4)

Combined and enriched export of likers, commenters, and profile data.

| Column | Required | Description |
|--------|----------|-------------|
| `post_id` | Yes | Which post this engagement belongs to (must match a `post_id` in posts.csv) |
| `name` | Yes | Full name of the engager |
| `occupation` | Yes | LinkedIn headline / occupation |
| `company` | No | Company name (extracted from headline via "at Company" pattern if empty) |
| `profile_url` | Yes | LinkedIn profile URL |
| `has_liked` | No | `true` or `false` (default: `true`) |
| `has_commented` | No | `true` or `false` (default: `false`) |
| `comment` | No | Comment text (if they commented) |
| `comment_url` | No | Direct link to the comment on LinkedIn |
| `degree` | No | Connection degree: `1st`, `2nd`, or `3rd` |

**Example:**

```csv
post_id,name,occupation,company,profile_url,has_liked,has_commented,comment,comment_url,degree
7654321098765432100,John Doe,Head of Sales at TechCo,TechCo,https://www.linkedin.com/in/johndoe/,true,true,"Great insights!",https://www.linkedin.com/feed/update/urn:li:activity:7654321098765432100?commentUrn=...,1st
7654321098765432100,Sarah Lee,Marketing Manager at StartupXYZ,StartupXYZ,https://www.linkedin.com/in/sarahlee/,true,false,,,2nd
```

### bob.csv (From CRM or Manual)

Your Book of Business — the list of target accounts you want to cross-reference against engagers.

| Column | Required | Description |
|--------|----------|-------------|
| `company_name` | Yes | Target account company name |
| `fire` | No | Priority level 0-3 (default: `1`). Higher = hotter lead. |
| `tier` | No | Account tier `A`, `B`, or `C` (default: empty) |

**Example:**

```csv
company_name,fire,tier
TechCo,3,A
StartupXYZ,2,B
Enterprise Inc,1,C
```

---

## Category Classification

The build script classifies each engager into a category based on keywords found in their `occupation` field. Classification is case-insensitive.

| Category | Keywords |
|----------|----------|
| **internal** | Matches against the company name from the client config |
| **hr** | `hr`, `human resources`, `people`, `talent`, `recruiting`, `recruitment`, `l&d`, `learning`, `development`, `training`, `culture`, `employee experience`, `workforce`, `organizational` |
| **executive** | `ceo`, `cfo`, `coo`, `cto`, `cmo`, `chief`, `founder`, `co-founder`, `owner`, `president`, `vp`, `vice president`, `director`, `managing director`, `partner`, `head of`, `general manager` |
| **marketing** | `marketing`, `brand`, `content`, `growth`, `demand gen`, `digital`, `communications`, `comms`, `pr`, `public relations`, `social media` |
| **sales** | `sales`, `business development`, `account executive`, `account manager`, `revenue`, `commercial`, `partnerships` |
| **other** | Everything that does not match the above categories |

Categories are evaluated in the order listed. The first match wins.

---

## Scoring Algorithm

Each engager receives a score based on the following factors:

| Factor | Points |
|--------|--------|
| Commented on post | +3 |
| Liked post (not commented) | +2 |
| BOB match (company is in target account list) | +3 |
| Executive title (matches executive category keywords) | +1 |
| 1st degree connection | +1 |
| **Maximum possible score** | **10** |

Scores are calculated per person across all posts. If someone engages with multiple posts, their engagement points accumulate (each like = +2, each comment = +3), but BOB match, executive title, and connection degree bonuses are applied only once.

---

## BOB Fuzzy Matching

The build script uses fuzzy string matching to cross-reference engager companies against the Book of Business.

- **Algorithm**: Python's `difflib.SequenceMatcher`
- **Threshold**: Similarity ratio >= `0.85` counts as a match
- **Company extraction**: If the `company` field is empty, the script attempts to extract the company name from the `occupation` field using the pattern `"... at {Company}"` (case-insensitive)
- **Comparison**: Case-insensitive, leading/trailing whitespace stripped
- **Examples of matches**:
  - `"TechCo"` matches `"Techco"` (case difference)
  - `"TechCo Inc"` matches `"TechCo"` if similarity >= 0.85
  - `"TechCo B.V."` matches `"TechCo"` if similarity >= 0.85
