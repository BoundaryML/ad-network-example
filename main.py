"""People Finder: CLI tool for ranking people by ad engagement and category interest.

Usage:
    python main.py search --categories "Conveyor Systems,Cartoning"
    python main.py search --categories "Conveyor Systems" --in-market
    python main.py search --categories "Packaging" --sort-by intensity --limit 20
    python main.py list-categories
    python main.py list-ads [--category "Conveyor Systems"]
    python main.py person P-0001
    python main.py generate
"""

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass
class Category:
    id: str
    name: str


@dataclass
class Ad:
    id: str
    name: str
    category_ids: list[str]


@dataclass
class Person:
    id: str
    name: str
    company: str
    title: str
    email: str


@dataclass
class Click:
    person_id: str
    ad_id: str
    click_date: str  # YYYY-MM-DD


@dataclass
class DataStore:
    categories: dict[str, Category] = field(default_factory=dict)
    ads: dict[str, Ad] = field(default_factory=dict)
    people: dict[str, Person] = field(default_factory=dict)
    clicks: list[Click] = field(default_factory=list)

    # Derived indexes
    cat_name_to_id: dict[str, str] = field(default_factory=dict)
    cat_to_ads: dict[str, set[str]] = field(default_factory=dict)
    person_clicks: dict[str, list[Click]] = field(default_factory=dict)

    def build_indexes(self):
        self.cat_name_to_id = {
            c.name.lower(): c.id for c in self.categories.values()
        }
        self.cat_to_ads = {}
        for ad in self.ads.values():
            for cid in ad.category_ids:
                self.cat_to_ads.setdefault(cid, set()).add(ad.id)
        self.person_clicks = {}
        for click in self.clicks:
            self.person_clicks.setdefault(click.person_id, []).append(click)


def load_data() -> DataStore:
    store = DataStore()

    with open(os.path.join(DATA_DIR, "categories.csv")) as f:
        for row in csv.DictReader(f):
            store.categories[row["category_id"]] = Category(
                id=row["category_id"], name=row["category_name"]
            )

    with open(os.path.join(DATA_DIR, "ads.csv")) as f:
        for row in csv.DictReader(f):
            store.ads[row["ad_id"]] = Ad(
                id=row["ad_id"],
                name=row["ad_name"],
                category_ids=row["category_ids"].split("|"),
            )

    with open(os.path.join(DATA_DIR, "people.csv")) as f:
        for row in csv.DictReader(f):
            store.people[row["person_id"]] = Person(
                id=row["person_id"],
                name=row["name"],
                company=row["company"],
                title=row["title"],
                email=row["email"],
            )

    with open(os.path.join(DATA_DIR, "clicks.csv")) as f:
        for row in csv.DictReader(f):
            store.clicks.append(Click(
                person_id=row["person_id"],
                ad_id=row["ad_id"],
                click_date=row["click_date"],
            ))

    store.build_indexes()
    return store


# ---------------------------------------------------------------------------
# Ranking engine
# ---------------------------------------------------------------------------

@dataclass
class RankedPerson:
    person: Person
    absolute_clicks: int          # total matching ad clicks
    unique_ads_clicked: int       # distinct matching ads clicked
    intensity: float              # unique_ads_clicked / total_matching_ads
    category_coverage: float      # fraction of queried categories matched
    categories_matched: list[str] # which queried categories they matched
    in_market: bool               # clicked a matching ad in last 6 months
    score: float = 0.0            # composite weighted score


def resolve_categories(store: DataStore, category_input: str) -> list[str]:
    """Resolve comma-separated category names/IDs to category IDs."""
    resolved = []
    for raw in category_input.split(","):
        raw = raw.strip()
        if not raw:
            continue
        # Try exact ID match
        if raw in store.categories:
            resolved.append(raw)
            continue
        # Try case-insensitive name match
        lower = raw.lower()
        if lower in store.cat_name_to_id:
            resolved.append(store.cat_name_to_id[lower])
            continue
        # Try substring match
        matches = [
            cid for cname, cid in store.cat_name_to_id.items()
            if lower in cname
        ]
        if len(matches) == 1:
            resolved.append(matches[0])
        elif len(matches) > 1:
            names = [store.categories[m].name for m in matches]
            print(f"Ambiguous category '{raw}', matches: {names}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Unknown category: '{raw}'", file=sys.stderr)
            print("Use 'list-categories' to see available categories.", file=sys.stderr)
            sys.exit(1)
    return resolved


def rank_people(
    store: DataStore,
    category_ids: list[str],
    *,
    in_market_only: bool = False,
    in_market_days: int = 180,
    weight_absolute: float = 0.3,
    weight_intensity: float = 0.3,
    weight_coverage: float = 0.25,
    weight_recency: float = 0.15,
) -> list[RankedPerson]:
    """Rank people by engagement with ads in the given categories.

    Scoring signals:
      - absolute_clicks: raw count of clicks on matching ads (more = more engaged)
      - intensity: fraction of matching ads clicked (higher = deeper interest)
      - category_coverage: fraction of queried categories the person has engaged with
      - in_market (recency): whether they clicked recently (last 6 months)

    Weights are normalized and combined into a 0-100 composite score.
    """
    # Collect all ads that belong to any of the selected categories
    matching_ads: set[str] = set()
    cat_ads_map: dict[str, set[str]] = {}  # per-category ad sets
    for cid in category_ids:
        ads_in_cat = store.cat_to_ads.get(cid, set())
        matching_ads.update(ads_in_cat)
        cat_ads_map[cid] = ads_in_cat

    if not matching_ads:
        return []

    total_matching_ads = len(matching_ads)
    cutoff_date = datetime(2026, 5, 14) - timedelta(days=in_market_days)

    results: list[RankedPerson] = []

    for person_id, clicks in store.person_clicks.items():
        # Filter to clicks on matching ads
        relevant_clicks = [c for c in clicks if c.ad_id in matching_ads]
        if not relevant_clicks:
            continue

        person = store.people[person_id]
        unique_ads = set(c.ad_id for c in relevant_clicks)
        absolute_clicks = len(relevant_clicks)
        unique_count = len(unique_ads)
        intensity = unique_count / total_matching_ads

        # Category coverage: how many of the queried categories did they touch?
        matched_cats = []
        for cid in category_ids:
            if unique_ads & cat_ads_map.get(cid, set()):
                matched_cats.append(store.categories[cid].name)
        coverage = len(matched_cats) / len(category_ids)

        # Recency: any click in the last N days?
        has_recent = any(
            datetime.strptime(c.click_date, "%Y-%m-%d") >= cutoff_date
            for c in relevant_clicks
        )

        results.append(RankedPerson(
            person=person,
            absolute_clicks=absolute_clicks,
            unique_ads_clicked=unique_count,
            intensity=intensity,
            category_coverage=coverage,
            categories_matched=matched_cats,
            in_market=has_recent,
        ))

    if in_market_only:
        results = [r for r in results if r.in_market]

    # Normalize and score
    if results:
        max_abs = max(r.absolute_clicks for r in results) or 1
        max_unique = max(r.unique_ads_clicked for r in results) or 1

        for r in results:
            norm_abs = r.absolute_clicks / max_abs
            norm_intensity = r.intensity  # already 0-1
            norm_coverage = r.category_coverage  # already 0-1
            recency_val = 1.0 if r.in_market else 0.0

            r.score = (
                weight_absolute * norm_abs
                + weight_intensity * norm_intensity
                + weight_coverage * norm_coverage
                + weight_recency * recency_val
            ) * 100

    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------

def print_table(headers: list[str], rows: list[list[str]], max_widths: dict[int, int] | None = None):
    """Print a formatted ASCII table."""
    max_widths = max_widths or {}
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Apply max width caps
    for i, cap in max_widths.items():
        col_widths[i] = min(col_widths[i], cap)

    def fmt_row(cells):
        parts = []
        for i, cell in enumerate(cells):
            s = str(cell)
            w = col_widths[i]
            if len(s) > w:
                s = s[: w - 1] + "\u2026"
            parts.append(s.ljust(w))
        return "  ".join(parts)

    print(fmt_row(headers))
    print("  ".join("-" * w for w in col_widths))
    for row in rows:
        print(fmt_row(row))


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_search(args):
    store = load_data()
    category_ids = resolve_categories(store, args.categories)

    cat_names = [store.categories[c].name for c in category_ids]
    print(f"Searching categories: {', '.join(cat_names)}")
    if args.in_market:
        print("Filter: in-market only (clicked in last 6 months)")
    print()

    results = rank_people(
        store,
        category_ids,
        in_market_only=args.in_market,
    )

    if not results:
        print("No matching people found.")
        return

    # Apply sort override
    sort_keys = {
        "score": lambda r: r.score,
        "intensity": lambda r: r.intensity,
        "clicks": lambda r: r.absolute_clicks,
        "coverage": lambda r: r.category_coverage,
    }
    sort_fn = sort_keys.get(args.sort_by, sort_keys["score"])
    results.sort(key=sort_fn, reverse=True)

    limit = args.limit or len(results)
    results = results[:limit]

    headers = ["Rank", "Name", "Company", "Title", "Score", "Clicks", "Intensity", "Coverage", "In Market"]
    rows = []
    for i, r in enumerate(results, 1):
        rows.append([
            str(i),
            r.person.name,
            r.person.company,
            r.person.title,
            f"{r.score:.1f}",
            str(r.absolute_clicks),
            f"{r.intensity:.0%}",
            f"{r.category_coverage:.0%}" + f" ({', '.join(r.categories_matched)})",
            "Yes" if r.in_market else "No",
        ])

    print_table(headers, rows, max_widths={7: 50})

    print(f"\nShowing {len(rows)} of {len(results)} results")
    total_matching = sum(
        len(store.cat_to_ads.get(cid, set())) for cid in category_ids
    )
    # deduplicated
    matching_ads = set()
    for cid in category_ids:
        matching_ads.update(store.cat_to_ads.get(cid, set()))
    print(f"Total matching ads across selected categories: {len(matching_ads)}")


def cmd_list_categories(args):
    store = load_data()
    headers = ["ID", "Category", "# Ads"]
    rows = []
    for cid, cat in sorted(store.categories.items()):
        ad_count = len(store.cat_to_ads.get(cid, set()))
        rows.append([cid, cat.name, str(ad_count)])
    print_table(headers, rows)


def cmd_list_ads(args):
    store = load_data()
    ads = list(store.ads.values())

    if args.category:
        cat_ids = resolve_categories(store, args.category)
        matching = set()
        for cid in cat_ids:
            matching.update(store.cat_to_ads.get(cid, set()))
        ads = [a for a in ads if a.id in matching]
        cat_names = [store.categories[c].name for c in cat_ids]
        print(f"Ads in categories: {', '.join(cat_names)}\n")

    headers = ["ID", "Ad Name", "Categories"]
    rows = []
    for ad in sorted(ads, key=lambda a: a.id):
        cat_names = [store.categories[c].name for c in ad.category_ids if c in store.categories]
        rows.append([ad.id, ad.name, ", ".join(cat_names)])
    print_table(headers, rows)
    print(f"\n{len(rows)} ads")


def cmd_person(args):
    store = load_data()

    # Resolve person by ID or name substring
    person = None
    if args.person_id in store.people:
        person = store.people[args.person_id]
    else:
        query = args.person_id.lower()
        matches = [p for p in store.people.values() if query in p.name.lower()]
        if len(matches) == 1:
            person = matches[0]
        elif len(matches) > 1:
            print(f"Multiple matches for '{args.person_id}':")
            for p in matches[:10]:
                print(f"  {p.id}  {p.name} ({p.company})")
            return
        else:
            print(f"No person found matching '{args.person_id}'")
            return

    print(f"Person:  {person.name}")
    print(f"ID:      {person.id}")
    print(f"Company: {person.company}")
    print(f"Title:   {person.title}")
    print(f"Email:   {person.email}")
    print()

    clicks = store.person_clicks.get(person.id, [])
    if not clicks:
        print("No click history.")
        return

    # Group by ad
    ad_clicks: dict[str, list[str]] = {}
    for c in clicks:
        ad_clicks.setdefault(c.ad_id, []).append(c.click_date)

    print(f"Click history ({len(clicks)} clicks on {len(ad_clicks)} ads):\n")
    headers = ["Ad", "Ad Name", "Categories", "Clicks", "Last Click"]
    rows = []
    for aid, dates in sorted(ad_clicks.items()):
        ad = store.ads[aid]
        cat_names = [store.categories[c].name for c in ad.category_ids]
        rows.append([
            aid,
            ad.name,
            ", ".join(cat_names),
            str(len(dates)),
            max(dates),
        ])
    print_table(headers, rows)

    # Show category engagement summary
    print("\nCategory engagement:")
    cat_click_count: dict[str, int] = {}
    for c in clicks:
        ad = store.ads.get(c.ad_id)
        if ad:
            for cid in ad.category_ids:
                cat_click_count[cid] = cat_click_count.get(cid, 0) + 1
    for cid, count in sorted(cat_click_count.items(), key=lambda x: x[1], reverse=True):
        cat_name = store.categories[cid].name
        print(f"  {cat_name}: {count} clicks")


def cmd_generate(args):
    from generate_data import main as gen_main
    gen_main()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="People Finder: rank people by ad engagement and category interest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s search --categories "Conveyor Systems,Cartoning"
  %(prog)s search --categories "Packaging" --in-market --limit 10
  %(prog)s list-categories
  %(prog)s list-ads --category "Conveyor Systems"
  %(prog)s person P-0001
  %(prog)s generate
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="command to run")

    # search
    p_search = subparsers.add_parser("search", help="Search and rank people by category interest")
    p_search.add_argument(
        "--categories", "-c", required=True,
        help="Comma-separated category names or IDs (supports substring match)",
    )
    p_search.add_argument(
        "--in-market", action="store_true",
        help="Only show people who clicked in the last 6 months",
    )
    p_search.add_argument(
        "--limit", "-n", type=int, default=None,
        help="Max results to show",
    )
    p_search.add_argument(
        "--sort-by", choices=["score", "intensity", "clicks", "coverage"],
        default="score",
        help="Sort results by this field (default: score)",
    )
    p_search.set_defaults(func=cmd_search)

    # list-categories
    p_cats = subparsers.add_parser("list-categories", help="List all categories")
    p_cats.set_defaults(func=cmd_list_categories)

    # list-ads
    p_ads = subparsers.add_parser("list-ads", help="List ads, optionally filtered by category")
    p_ads.add_argument("--category", help="Filter by category name")
    p_ads.set_defaults(func=cmd_list_ads)

    # person
    p_person = subparsers.add_parser("person", help="Show person details and click history")
    p_person.add_argument("person_id", help="Person ID (e.g. P-0001) or name substring")
    p_person.set_defaults(func=cmd_person)

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate synthetic data")
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
