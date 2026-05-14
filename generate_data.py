"""Generate synthetic data for the people-finder ad ranking system.

Creates four CSV files in data/:
  - categories.csv: category_id, category_name
  - ads.csv: ad_id, ad_name, category_ids (pipe-separated)
  - people.csv: person_id, name, company, title, email
  - clicks.csv: person_id, ad_id, click_date
"""

import csv
import random
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

CATEGORIES = [
    "Conveyor Systems",
    "Cartoning",
    "Packaging",
    "Labeling",
    "Palletizing",
    "Inspection Systems",
    "Filling Equipment",
    "Wrapping",
    "Coding & Marking",
    "Material Handling",
    "Robotics & Automation",
    "Quality Control",
    "Warehousing",
    "Sorting Systems",
    "Printing & Finishing",
]

# Each ad maps to 1-3 categories (by index into CATEGORIES)
ADS = [
    ("FlexMove Belt Conveyor Series", [0, 9]),
    ("SpeedPack Cartoner 3000", [1, 2]),
    ("AutoLabel Pro X1", [3, 8]),
    ("PalletMax Robotic Palletizer", [4, 10]),
    ("VisionGuard Inline Inspector", [5, 11]),
    ("LiquidFill Precision Filler", [6, 2]),
    ("WrapTight Stretch Wrapper", [7, 2]),
    ("JetMark Industrial Coder", [8, 14]),
    ("GripSort Automated Sorter", [13, 9]),
    ("MegaLift AGV Fleet", [9, 12]),
    ("RoboArm Pick & Place", [10, 4]),
    ("QC-Scan 360 Defect Detector", [11, 5]),
    ("SmartStore WMS Platform", [12, 9]),
    ("ConveyorLink Modular System", [0, 9, 10]),
    ("CartoPack Integrated Line", [1, 2, 7]),
    ("LabelJet High-Speed Applicator", [3, 14]),
    ("PalletWrap Combo System", [4, 7]),
    ("FillSeal Pouch Machine", [6, 2, 3]),
    ("CodeVision Print & Verify", [8, 5, 14]),
    ("AutoSort Distribution Hub", [13, 12, 9]),
    ("InspectAI Deep Learning QC", [5, 11, 10]),
    ("FlexiConveyor Curve Module", [0]),
    ("NanoPrint Inkjet Coder", [8]),
    ("BoxForm Carton Erector", [1]),
    ("ShrinkPro Tunnel System", [7, 2]),
    ("PadApply Cushion Inserter", [2, 9]),
    ("TrayPack Denesting System", [2, 1, 4]),
    ("WeighCheck Dynamic Scale", [5, 11]),
    ("StackBot Layer Palletizer", [4, 10]),
    ("RackMaster AS/RS System", [12, 9]),
    ("FlexGrip Robotic Packer", [10, 2, 4]),
    ("ServoFill Gravity Filler", [6]),
    ("WrapStar Orbital Wrapper", [7]),
    ("MetalScan Detector Pro", [5, 11]),
    ("DigiPrint Variable Data", [14, 8]),
    ("SmartBelt IoT Conveyor", [0, 10]),
    ("CartonSeal Tape Machine", [1, 2]),
    ("RFID-Tag Inline Labeler", [3, 8, 5]),
    ("HygiePack Clean Room Line", [2, 6, 11]),
    ("DockBot Loading System", [9, 12, 10]),
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen",
    "Daniel", "Lisa", "Matthew", "Nancy", "Anthony", "Betty", "Mark",
    "Margaret", "Steven", "Sandra", "Paul", "Ashley", "Andrew", "Dorothy",
    "Joshua", "Kimberly", "Kenneth", "Emily", "Kevin", "Donna",
    "Brian", "Michelle", "George", "Carol", "Timothy", "Amanda",
    "Ronald", "Melissa", "Edward", "Deborah", "Jason", "Stephanie",
    "Jeffrey", "Rebecca", "Ryan", "Sharon", "Jacob", "Laura",
    "Gary", "Cynthia", "Nicholas", "Kathleen", "Eric", "Amy",
    "Jonathan", "Angela", "Stephen", "Shirley", "Larry", "Anna",
    "Justin", "Brenda", "Scott", "Pamela", "Brandon", "Emma",
    "Benjamin", "Nicole", "Samuel", "Helen", "Raymond", "Samantha",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Chen", "Wu", "Patel", "Shah", "Kim", "Park",
    "Nakamura", "Muller", "Weber", "Fischer", "Schneider", "Becker",
]

COMPANIES = [
    "ProPack Industries", "Summit Manufacturing", "Velocity Packaging Co.",
    "Apex Automation Group", "Meridian Food Systems", "TrueForm Containers",
    "Nexus Logistics Corp", "PrimeLine Bottling", "Atlas Warehouse Solutions",
    "Precision Pharma Pack", "Coastal Beverage Co.", "GreenLeaf Organics",
    "SteelRidge Fabrication", "FreshDirect Foods", "Pacific Paper Products",
    "Quantum Plastics Inc.", "Heritage Dairy Corp", "BlueWave Cosmetics",
    "Ironclad Distribution", "Sterling Pet Foods", "Nordic Ice Cream Co.",
    "ClearView Glass Works", "Titan Cement Corp", "SunBright Solar Mfg",
    "EverFresh Produce", "SafeGuard Medical", "Continental Snacks",
    "RapidShip Fulfillment", "AgroTech Processing", "Diamond Chemical Co.",
    "Pinnacle Electronics", "OceanSpray Seafood", "CraftBrew United",
    "MetroPrint Solutions", "EcoWrap Sustainable", "NovaChem Labs",
    "VitalHealth Nutrition", "CoreSteel Industries", "BrightStar Energy",
    "FarmFresh Cooperative",
]

TITLES = [
    "VP of Operations", "Plant Manager", "Director of Engineering",
    "Packaging Manager", "Production Supervisor", "Supply Chain Director",
    "Automation Engineer", "Maintenance Manager", "Quality Director",
    "Manufacturing Engineer", "Logistics Manager", "Procurement Manager",
    "COO", "VP of Manufacturing", "Director of Packaging",
    "Continuous Improvement Manager", "Technical Director", "Warehouse Manager",
    "VP of Supply Chain", "Process Engineer", "Facilities Manager",
    "Director of Procurement", "Operations Manager", "Line Supervisor",
    "VP of Engineering", "R&D Manager", "Capital Projects Manager",
]


def generate_categories(writer: csv.writer):
    for i, name in enumerate(CATEGORIES):
        writer.writerow([f"CAT-{i+1:03d}", name])


def generate_ads(writer: csv.writer):
    for i, (name, cat_indices) in enumerate(ADS):
        cat_ids = "|".join(f"CAT-{idx+1:03d}" for idx in cat_indices)
        writer.writerow([f"AD-{i+1:03d}", name, cat_ids])


def generate_people(writer: csv.writer, count: int = 200) -> list[str]:
    """Generate people and return list of person_ids."""
    person_ids = []
    used_names = set()
    for i in range(count):
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            if (first, last) not in used_names:
                used_names.add((first, last))
                break
        pid = f"P-{i+1:04d}"
        company = random.choice(COMPANIES)
        title = random.choice(TITLES)
        email = f"{first.lower()}.{last.lower()}@{company.lower().replace(' ', '').replace('.', '').replace(',', '')}.com"
        writer.writerow([pid, f"{first} {last}", company, title, email])
        person_ids.append(pid)
    return person_ids


def generate_clicks(
    writer: csv.writer,
    person_ids: list[str],
    num_ads: int,
    *,
    min_clicks: int = 0,
    max_clicks: int = 15,
    recent_bias: float = 0.6,
):
    """Generate click events.

    Some people are 'heavy clickers' focused on specific categories,
    some are light browsers. recent_bias controls how many clicks fall
    in the last 6 months vs older.
    """
    now = datetime(2026, 5, 14)
    six_months_ago = now - timedelta(days=180)
    two_years_ago = now - timedelta(days=730)

    ad_ids = [f"AD-{i+1:03d}" for i in range(num_ads)]

    # Build category->ads mapping for realistic clustering
    cat_to_ads: dict[int, list[str]] = {}
    for i, (_, cat_indices) in enumerate(ADS):
        for ci in cat_indices:
            cat_to_ads.setdefault(ci, []).append(ad_ids[i])

    for pid in person_ids:
        # Decide this person's click profile
        click_count = random.randint(min_clicks, max_clicks)
        if click_count == 0:
            continue

        # Pick 1-3 interest categories for this person (cluster their clicks)
        num_interests = random.randint(1, 3)
        interest_cats = random.sample(range(len(CATEGORIES)), num_interests)

        # Weight ads toward their interest categories
        interest_ads = set()
        for cat_idx in interest_cats:
            interest_ads.update(cat_to_ads.get(cat_idx, []))

        clicked_ads = set()
        for _ in range(click_count):
            # 75% chance to click an ad from interest categories
            if interest_ads and random.random() < 0.75:
                ad = random.choice(list(interest_ads))
            else:
                ad = random.choice(ad_ids)
            clicked_ads.add(ad)

        # Generate click dates for each unique ad click
        for ad in clicked_ads:
            if random.random() < recent_bias:
                # Recent click (last 6 months)
                days_ago = random.randint(0, 180)
            else:
                # Older click (6 months to 2 years ago)
                days_ago = random.randint(181, 730)
            click_date = now - timedelta(days=days_ago)
            writer.writerow([pid, ad, click_date.strftime("%Y-%m-%d")])

            # Some people click the same ad multiple times
            if random.random() < 0.15:
                days_ago2 = max(0, days_ago - random.randint(1, 60))
                click_date2 = now - timedelta(days=days_ago2)
                writer.writerow([pid, ad, click_date2.strftime("%Y-%m-%d")])


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    random.seed(42)  # Reproducible data

    # Categories
    with open(os.path.join(DATA_DIR, "categories.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category_id", "category_name"])
        generate_categories(w)
    print(f"Generated {len(CATEGORIES)} categories")

    # Ads
    with open(os.path.join(DATA_DIR, "ads.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ad_id", "ad_name", "category_ids"])
        generate_ads(w)
    print(f"Generated {len(ADS)} ads")

    # People
    with open(os.path.join(DATA_DIR, "people.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["person_id", "name", "company", "title", "email"])
        person_ids = generate_people(w, count=200)
    print(f"Generated {len(person_ids)} people")

    # Clicks
    with open(os.path.join(DATA_DIR, "clicks.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["person_id", "ad_id", "click_date"])
        generate_clicks(w, person_ids, len(ADS))

    # Count clicks
    with open(os.path.join(DATA_DIR, "clicks.csv")) as f:
        click_count = sum(1 for _ in f) - 1  # minus header
    print(f"Generated {click_count} click events")

    print(f"\nData written to {DATA_DIR}/")


if __name__ == "__main__":
    main()
