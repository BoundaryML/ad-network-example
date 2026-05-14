"""Flask web UI for People Finder."""

from flask import Flask, render_template, request

from main import load_data, rank_people

app = Flask(__name__)


def get_store():
    """Load data store (cached on app context in production, fresh per-request for dev)."""
    return load_data()


@app.route("/")
def index():
    """Search page - the main UI."""
    store = get_store()
    categories = sorted(store.categories.values(), key=lambda c: c.name)

    # Read query params
    selected_ids = request.args.getlist("categories")
    in_market = request.args.get("in_market") == "on"
    sort_by = request.args.get("sort_by", "score")

    results = []
    matching_ad_count = 0
    if selected_ids:
        results = rank_people(store, selected_ids, in_market_only=in_market)

        sort_keys = {
            "score": lambda r: r.score,
            "intensity": lambda r: r.intensity,
            "clicks": lambda r: r.absolute_clicks,
            "coverage": lambda r: r.category_coverage,
        }
        results.sort(key=sort_keys.get(sort_by, sort_keys["score"]), reverse=True)

        matching_ads = set()
        for cid in selected_ids:
            matching_ads.update(store.cat_to_ads.get(cid, set()))
        matching_ad_count = len(matching_ads)

    return render_template(
        "search.html",
        categories=categories,
        selected_ids=selected_ids,
        in_market=in_market,
        sort_by=sort_by,
        results=results,
        matching_ad_count=matching_ad_count,
    )


@app.route("/categories")
def categories():
    store = get_store()
    cats = []
    for cid, cat in sorted(store.categories.items()):
        ad_count = len(store.cat_to_ads.get(cid, set()))
        # Count unique people who clicked ads in this category
        ads_in_cat = store.cat_to_ads.get(cid, set())
        people_set = set()
        for click in store.clicks:
            if click.ad_id in ads_in_cat:
                people_set.add(click.person_id)
        cats.append({
            "id": cid,
            "name": cat.name,
            "ad_count": ad_count,
            "people_count": len(people_set),
        })
    return render_template("categories.html", categories=cats)


@app.route("/ads")
def ads():
    store = get_store()
    category_filter = request.args.get("category")

    ad_list = list(store.ads.values())
    filter_name = None

    if category_filter and category_filter in store.categories:
        matching = store.cat_to_ads.get(category_filter, set())
        ad_list = [a for a in ad_list if a.id in matching]
        filter_name = store.categories[category_filter].name

    enriched = []
    for ad in sorted(ad_list, key=lambda a: a.id):
        cat_names = [store.categories[c].name for c in ad.category_ids if c in store.categories]
        click_count = sum(1 for c in store.clicks if c.ad_id == ad.id)
        enriched.append({
            "id": ad.id,
            "name": ad.name,
            "categories": cat_names,
            "click_count": click_count,
        })

    all_categories = sorted(store.categories.values(), key=lambda c: c.name)
    return render_template(
        "ads.html",
        ads=enriched,
        filter_name=filter_name,
        category_filter=category_filter,
        all_categories=all_categories,
    )


@app.route("/person/<person_id>")
def person(person_id):
    store = get_store()
    person = store.people.get(person_id)
    if not person:
        return render_template("404.html", message=f"Person {person_id} not found"), 404

    clicks = store.person_clicks.get(person_id, [])

    # Group clicks by ad
    ad_clicks: dict[str, list[str]] = {}
    for c in clicks:
        ad_clicks.setdefault(c.ad_id, []).append(c.click_date)

    click_history = []
    for aid, dates in sorted(ad_clicks.items()):
        ad = store.ads.get(aid)
        if not ad:
            continue
        cat_names = [store.categories[c].name for c in ad.category_ids if c in store.categories]
        click_history.append({
            "ad_id": aid,
            "ad_name": ad.name,
            "categories": cat_names,
            "click_count": len(dates),
            "last_click": max(dates),
        })

    # Category engagement summary
    cat_clicks: dict[str, int] = {}
    for c in clicks:
        ad = store.ads.get(c.ad_id)
        if ad:
            for cid in ad.category_ids:
                cat_clicks[cid] = cat_clicks.get(cid, 0) + 1
    cat_engagement = []
    for cid, count in sorted(cat_clicks.items(), key=lambda x: x[1], reverse=True):
        cat_engagement.append({
            "id": cid,
            "name": store.categories[cid].name,
            "clicks": count,
        })

    return render_template(
        "person.html",
        person=person,
        click_history=click_history,
        cat_engagement=cat_engagement,
        total_clicks=len(clicks),
        unique_ads=len(ad_clicks),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
