#!/usr/bin/env python3
"""
Build script for the Engagement Tracker dashboard.

Reads a client config JSON, 3 CSV files (posts, engagers, book of business),
and an HTML template. Processes the data and produces a self-contained HTML dashboard.

Usage:
    python3 build-dashboard.py \
        --config client-config.json \
        --posts posts.csv \
        --engagers engagers.csv \
        --bob bob.csv \
        --template dashboard-template.html \
        --output ./output/index.html
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# 1. load_config
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Read JSON config file. Validate required fields, fill defaults."""
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Required fields
    for field in ("company_name", "influencer_name"):
        if not config.get(field):
            raise ValueError(f"Config is missing required field: '{field}'")

    # Defaults for optional scalar fields
    config.setdefault("influencer_role", "")
    config.setdefault("badge_label", "Demand Gen Intelligence")
    config.setdefault("bob_description", "target accounts")
    config.setdefault("bob_count", 0)
    config.setdefault("target_audience_label", "HR/People")
    config.setdefault("password", "")

    # Brand color defaults
    brand = config.setdefault("brand", {})
    brand.setdefault("primary_color", "#6B2DEF")
    brand.setdefault("primary_color_dark", "#5321C9")
    brand.setdefault("primary_color_light", "#EDE5FF")
    brand.setdefault("primary_color_mid", "#C4A8FF")
    brand.setdefault("accent_color", "#007A7A")
    brand.setdefault("accent_color_light", "#E0F2F2")

    # Validate colors (warn only)
    hex_re = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
    for key, val in brand.items():
        if not hex_re.match(val):
            print(f"WARNING: brand.{key} = '{val}' does not look like a hex color")

    return config


# ---------------------------------------------------------------------------
# 2. parse_posts_csv
# ---------------------------------------------------------------------------

def parse_posts_csv(path: str) -> list:
    """Read posts CSV. Returns list of dicts."""
    required = {"post_id", "post_url", "title", "content", "post_date"}
    return _parse_csv(path, required, "posts")


# ---------------------------------------------------------------------------
# 3. parse_engagers_csv
# ---------------------------------------------------------------------------

def parse_engagers_csv(path: str) -> list:
    """Read engagers CSV. Returns list of dicts with parsed booleans."""
    required = {"post_id", "name", "occupation", "profile_url"}
    rows = _parse_csv(path, required, "engagers")

    for row in rows:
        row["has_liked"] = _parse_bool(row.get("has_liked", "false"))
        row["has_commented"] = _parse_bool(row.get("has_commented", "false"))
        row.setdefault("company", "")
        row.setdefault("comment", "")
        row.setdefault("comment_url", "")
        row.setdefault("degree", "")

    return rows


# ---------------------------------------------------------------------------
# 4. parse_bob_csv
# ---------------------------------------------------------------------------

def parse_bob_csv(path: str) -> list:
    """Read Book of Business CSV. Returns list of dicts."""
    required = {"company_name"}
    rows = _parse_csv(path, required, "bob")

    for row in rows:
        # fire: 0-3, default 1
        try:
            row["fire"] = max(0, min(3, int(row.get("fire", "1") or "1")))
        except ValueError:
            row["fire"] = 1
        # tier: A/B/C or empty
        row["tier"] = (row.get("tier", "") or "").strip().upper()
        if row["tier"] not in ("A", "B", "C", ""):
            row["tier"] = ""

    return rows


# ---------------------------------------------------------------------------
# 5. classify_category
# ---------------------------------------------------------------------------

def classify_category(occupation: str, company: str, internal_company_name: str) -> str:
    """Keyword-based classification of an engager's role."""
    occ_lower = (occupation or "").lower()
    comp_lower = (company or "").lower()
    internal_lower = (internal_company_name or "").lower()

    # --- internal ---
    if internal_lower and (
        internal_lower in comp_lower
        or internal_lower in occ_lower
        or _fuzzy_match(company, internal_company_name, 0.85)
    ):
        return "internal"

    # --- hr ---
    hr_keywords = [
        "human resources", "people operations", "people ops",
        "talent acquisition", "talent management", "recruitment",
        "recruiting", "hiring", "hrbp", "hr ", " hr",
        "chro", "people & culture", "people and culture",
        "workforce", "employer brand",
    ]
    # CPO needs context check — "Chief People" = HR, "Chief Product" = not HR
    if any(kw in occ_lower for kw in hr_keywords):
        return "hr"
    if "cpo" in occ_lower.split() or "cpo" in re.split(r"[\s|/,;]", occ_lower):
        # Only HR if "people" context, not "product"
        if "people" in occ_lower or "human" in occ_lower:
            return "hr"
        if "product" not in occ_lower:
            return "hr"

    # --- executive ---
    exec_titles = [
        "ceo", "cto", "cfo", "coo", "cmo", "cro", "cio", "cso",
        "vp ", "vice president", "managing director", "founder",
        "co-founder", "cofounder", "partner", "president",
        "chief executive", "chief technology", "chief financial",
        "chief operating", "chief marketing", "chief revenue",
        "chief information", "chief strategy", "chief product",
        "chief commercial", "chief digital", "chief people",
        "general manager", "board member", "director general",
        "owner", "principal",
    ]
    if any(kw in occ_lower for kw in exec_titles):
        return "executive"
    # Standalone "Chief" as a word
    if re.search(r"\bchief\b", occ_lower):
        return "executive"

    # --- marketing ---
    mktg_keywords = [
        "marketing", "brand", "content", "growth", "demand gen",
        "demand generation", "digital marketing", "social media",
        "communications", "comms", "creative director",
        "community manager", "public relations", "pr manager",
        "pr director", "copywriter", "seo", "sem",
    ]
    if any(kw in occ_lower for kw in mktg_keywords):
        return "marketing"

    # --- sales ---
    sales_keywords = [
        "sales", "account executive", "business development",
        "bdr", "sdr", "account manager", "customer success",
        "revenue", "commercial director", "commercial manager",
        "partnerships", "key account", "enterprise account",
        "inside sales", "field sales", "new business",
    ]
    if any(kw in occ_lower for kw in sales_keywords):
        return "sales"

    # --- other ---
    return "other"


# ---------------------------------------------------------------------------
# 6. match_bob
# ---------------------------------------------------------------------------

def match_bob(company_from_engager: str, occupation: str, bob_list: list) -> dict | None:
    """Fuzzy-match an engager's company against the Book of Business."""
    company = (company_from_engager or "").strip()

    # Try to extract from occupation if company is empty
    if not company and occupation:
        m = re.search(r"\bat\s+(.+?)(?:\s*[-|]|$)", occupation, re.IGNORECASE)
        if m:
            company = m.group(1).strip()

    if not company:
        return None

    company_lower = company.lower().strip()

    for entry in bob_list:
        bob_name = entry["company_name"].strip()
        bob_lower = bob_name.lower().strip()

        # Exact match (case-insensitive)
        if company_lower == bob_lower:
            return {"n": bob_name, "f": entry["fire"], "t": entry["tier"]}

        # Fuzzy match
        if _fuzzy_match(company, bob_name, 0.85):
            return {"n": bob_name, "f": entry["fire"], "t": entry["tier"]}

    return None


# ---------------------------------------------------------------------------
# 7. score_engager
# ---------------------------------------------------------------------------

def score_engager(engager: dict) -> int:
    """Score an engager 0-10 based on interaction, BOB match, role, degree."""
    score = 0

    # Interaction: +3 for comment, +2 for like-only (max 3)
    if engager.get("hasCommented"):
        score += 3
    elif engager.get("hasLiked"):
        score += 2

    # BOB match: +3
    if engager.get("bobMatch"):
        score += 3

    # Executive: +1
    if engager.get("category") == "executive":
        score += 1

    # 1st degree: +1
    degree = (engager.get("degree") or "").strip().lower()
    if degree in ("1st", "1"):
        score += 1

    return min(score, 10)


# ---------------------------------------------------------------------------
# 8. build_data
# ---------------------------------------------------------------------------

def build_data(config: dict, posts: list, engagers: list, bob: list) -> dict:
    """Main processing: group, classify, match, score, aggregate."""
    internal_name = config["company_name"]

    # Group engagers by post_id
    engagers_by_post = {}
    for eng in engagers:
        pid = eng["post_id"]
        engagers_by_post.setdefault(pid, []).append(eng)

    posts_out = []
    total_engagers = 0
    total_bob_matches = 0

    for post in posts:
        pid = post["post_id"]
        post_engagers_raw = engagers_by_post.get(pid, [])

        processed = []
        post_bob_count = 0
        post_comment_count = 0
        post_like_count = 0

        for eng in post_engagers_raw:
            category = classify_category(eng["occupation"], eng.get("company", ""), internal_name)
            bob_match = match_bob(eng.get("company", ""), eng["occupation"], bob)

            company_val = (eng.get("company", "") or "").strip()
            # Also try extracting from occupation for unknownCompany flag
            if not company_val and eng["occupation"]:
                m = re.search(r"\bat\s+(.+?)(?:\s*[-|]|$)", eng["occupation"], re.IGNORECASE)
                if m:
                    company_val = m.group(1).strip()

            unknown_company = not bool(company_val)

            processed_eng = {
                "name": eng["name"],
                "occupation": eng["occupation"],
                "company": eng.get("company", ""),
                "profileUrl": eng["profile_url"],
                "hasLiked": eng["has_liked"],
                "hasCommented": eng["has_commented"],
                "comment": eng.get("comment", ""),
                "commentUrl": eng.get("comment_url", ""),
                "degree": eng.get("degree", ""),
                "category": category,
                "isTargetAccount": False,  # set after scoring
                "bobMatch": bob_match,
                "unknownCompany": unknown_company,
                "score": 0,  # set below
            }

            processed_eng["score"] = score_engager(processed_eng)
            processed_eng["isTargetAccount"] = bool(bob_match) or processed_eng["score"] >= 7

            if bob_match:
                post_bob_count += 1
                total_bob_matches += 1

            if eng["has_commented"]:
                post_comment_count += 1
            if eng["has_liked"]:
                post_like_count += 1

            processed.append(processed_eng)

        # Sort engagers by score descending
        processed.sort(key=lambda e: e["score"], reverse=True)

        # Build title: use title field, fall back to first ~40 chars of content
        title = (post.get("title") or "").strip()
        if not title:
            content = (post.get("content") or "").strip()
            title = content[:40] + ("..." if len(content) > 40 else "")

        post_out = {
            "id": pid,
            "url": post["post_url"],
            "title": title,
            "content": post.get("content", ""),
            "postDate": post.get("post_date", ""),
            "engager_count": len(processed),
            "comment_count": post_comment_count,
            "like_count": post_like_count,
            "bob_count": post_bob_count,
            "engagers": processed,
        }

        total_engagers += len(processed)
        posts_out.append(post_out)

    # Sort posts by engager_count descending
    posts_out.sort(key=lambda p: p["engager_count"], reverse=True)

    # BOB JSON
    bob_json_list = [{"n": b["company_name"], "f": b["fire"], "t": b["tier"]} for b in bob]

    return {
        "posts_json": json.dumps(posts_out, ensure_ascii=False),
        "bob_json": json.dumps(bob_json_list, ensure_ascii=False),
        "counts": {
            "posts": len(posts_out),
            "engagers": total_engagers,
            "bob_matches": total_bob_matches,
            "bob_total": len(bob),
        },
    }


# ---------------------------------------------------------------------------
# 9. render_template
# ---------------------------------------------------------------------------

def render_template(template_html: str, config: dict, data: dict, bob: list) -> str:
    """Replace all placeholders in the template HTML."""
    # Compute initials: first letter of each word, up to 2 chars
    name_parts = config["influencer_name"].split()
    initials = "".join(p[0].upper() for p in name_parts if p)[:2]

    # Internal category slug
    internal_category = config["company_name"].lower().replace(" ", "")

    # Build date: "Mon YYYY"
    build_date = datetime.now().strftime("%b %Y")

    # BOB count: config override or actual count
    bob_count = config.get("bob_count") or len(bob)

    replacements = {
        "{{COMPANY_NAME}}": config["company_name"],
        "{{INFLUENCER_NAME}}": config["influencer_name"],
        "{{INFLUENCER_ROLE}}": config.get("influencer_role", ""),
        "{{INFLUENCER_INITIALS}}": initials,
        "{{PRIMARY_COLOR}}": config["brand"]["primary_color"],
        "{{PRIMARY_COLOR_DARK}}": config["brand"]["primary_color_dark"],
        "{{PRIMARY_COLOR_LIGHT}}": config["brand"]["primary_color_light"],
        "{{PRIMARY_COLOR_MID}}": config["brand"]["primary_color_mid"],
        "{{ACCENT_COLOR}}": config["brand"]["accent_color"],
        "{{ACCENT_COLOR_LIGHT}}": config["brand"]["accent_color_light"],
        "{{BADGE_LABEL}}": config.get("badge_label", "Demand Gen Intelligence"),
        "{{BOB_DESCRIPTION}}": config.get("bob_description", "target accounts"),
        "{{BOB_COUNT}}": str(bob_count),
        "{{TARGET_AUDIENCE_LABEL}}": config.get("target_audience_label", "HR/People"),
        "{{PASSWORD}}": config.get("password", ""),
        "{{POSTS_DATA}}": data["posts_json"],
        "{{BOB_DATA}}": data["bob_json"],
        "{{INTERNAL_CATEGORY}}": internal_category,
        "{{BUILD_DATE}}": build_date,
    }

    result = template_html
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    # Validate no remaining placeholders
    remaining = re.findall(r"\{\{[A-Z_]+\}\}", result)
    if remaining:
        unique = sorted(set(remaining))
        raise ValueError(
            f"Template has unreplaced placeholders: {', '.join(unique)}"
        )

    return result


# ---------------------------------------------------------------------------
# 10. main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build the Engagement Tracker HTML dashboard."
    )
    parser.add_argument("--config", required=True, help="Path to client config JSON")
    parser.add_argument("--posts", required=True, help="Path to posts CSV")
    parser.add_argument("--engagers", required=True, help="Path to engagers CSV")
    parser.add_argument("--bob", required=True, help="Path to Book of Business CSV")
    parser.add_argument("--template", required=True, help="Path to HTML template")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()

    # Load config
    print(f"Loading config: {args.config}")
    config = load_config(args.config)

    # Parse CSVs
    print(f"Parsing posts: {args.posts}")
    posts = parse_posts_csv(args.posts)

    print(f"Parsing engagers: {args.engagers}")
    engagers = parse_engagers_csv(args.engagers)

    print(f"Parsing BOB: {args.bob}")
    bob = parse_bob_csv(args.bob)

    # Process data
    print("Processing data...")
    data = build_data(config, posts, engagers, bob)

    # Read template
    print(f"Reading template: {args.template}")
    with open(args.template, "r", encoding="utf-8") as f:
        template_html = f.read()

    # Render
    print("Rendering dashboard...")
    output_html = render_template(template_html, config, data, bob)

    # Create output directory if needed
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Write output
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output_html)

    counts = data["counts"]
    print(f"\nDashboard built successfully!")
    print(f"  Posts:        {counts['posts']}")
    print(f"  Engagers:     {counts['engagers']}")
    print(f"  BOB matches:  {counts['bob_matches']}")
    print(f"  BOB total:    {counts['bob_total']}")
    print(f"  Output:       {os.path.abspath(args.output)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(path: str, required_columns: set, label: str) -> list:
    """Generic CSV parser with validation, BOM handling, and whitespace stripping."""
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            print(f"WARNING: {label} CSV is empty (no header row): {path}")
            return []

        # Strip whitespace from field names
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

        # Check required columns
        actual = set(reader.fieldnames)
        missing = required_columns - actual
        if missing:
            raise ValueError(
                f"{label} CSV is missing required columns: {', '.join(sorted(missing))}. "
                f"Found columns: {', '.join(sorted(actual))}"
            )

        for row in reader:
            # Strip all string values
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v or "") for k, v in row.items()}
            rows.append(cleaned)

    if not rows:
        print(f"WARNING: {label} CSV has a header but no data rows: {path}")

    return rows


def _parse_bool(value) -> bool:
    """Parse boolean from various string representations."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def _fuzzy_match(a: str, b: str, threshold: float = 0.85) -> bool:
    """Check if two strings are fuzzy-equal using SequenceMatcher."""
    if not a or not b:
        return False
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= threshold


if __name__ == "__main__":
    main()
