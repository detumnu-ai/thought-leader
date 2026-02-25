# Data Format Reference

This document specifies the 3 CSV input formats and the PhantomBuster workflow for collecting LinkedIn engagement data.

---

## PhantomBuster Setup

You need two PhantomBuster Phantoms to collect engagement data from LinkedIn posts.

### 1. LinkedIn Post Likers Phantom

Extracts all people who liked specific LinkedIn post URLs.

- **Input**: A list of LinkedIn post URLs (one per line, or a Google Sheet/CSV with a column of URLs)
- **Output**: CSV with columns including `name`, `occupation`, `company`, `profileUrl`, `postUrl`, etc.

### 2. LinkedIn Post Commenters Phantom

Extracts all commenters and their comment text from specific LinkedIn post URLs.

- **Input**: Same list of LinkedIn post URLs
- **Output**: CSV with columns including `name`, `occupation`, `company`, `profileUrl`, `comment`, `commentUrl`, `postUrl`, etc.

### 3. How to Export

1. Go to [PhantomBuster](https://phantombuster.com) and open each Phantom's results page
2. Click **Download CSV** to export the full result set
3. Save each file locally (e.g., `likers-export.csv` and `commenters-export.csv`)

---

## Merging Liker + Commenter Exports

Before feeding data into the build script, combine both PhantomBuster exports into a single `engagers.csv`.

### Option A: Merged Rows (Recommended)

1. Open both CSVs
2. Create a new `engagers.csv` with the columns specified below
3. For each liker, add a row with `has_liked=true`, `has_commented=false`
4. For each commenter, add a row with `has_liked=false`, `has_commented=true`
5. If a person appears in both exports (same `profile_url` on the same `post_id`), merge into a single row with `has_liked=true`, `has_commented=true` and include their comment text

### Option B: Separate Rows (Also Fine)

Keep likers and commenters as separate rows. The build script deduplicates by `profile_url` within each post when calculating scores, so duplicate entries will not inflate engagement counts.

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

### posts.csv (Manually Created)

You create this file yourself with metadata about each LinkedIn post you want to track.

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

### engagers.csv (From PhantomBuster)

Combined export of likers and commenters from PhantomBuster.

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
