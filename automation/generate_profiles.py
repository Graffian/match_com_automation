"""
Generate random profile CSVs for Match.com accounts.

Usage:
    python -m automation.generate_profiles --count 4 --output data/profiles.csv
"""
import csv
import random
import argparse
from pathlib import Path

GIRL_NAMES = [
    "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Mia", "Charlotte", "Amelia",
    "Harper", "Evelyn", "Abigail", "Emily", "Ella", "Elizabeth", "Camila",
    "Grace", "Chloe", "Victoria", "Riley", "Aria", "Lily", "Aurora", "Zoey",
    "Nora", "Hannah", "Stella", "Maya", "Savannah", "Penelope", "Layla",
]

ZIP_CODES_KY = [
    "40201", "40202", "40203", "40204", "40205", "40206", "40207", "40208",
    "40209", "40210", "40211", "40212", "40213", "40214", "40215", "40216",
    "40217", "40218", "40219", "40220", "40221", "40222", "40223", "40224",
]

JOBS = [
    "Marketing Coordinator", "Graphic Designer", "Registered Nurse",
    "Software Engineer", "Teacher", "Account Manager", "Data Analyst",
    "Content Writer", "Fitness Instructor", "Dental Hygienist",
    "Office Manager", "Social Media Manager", "Sales Associate",
    "Event Planner", "Barista", "Photographer", "Yoga Instructor",
    "Human Resources Specialist", "Customer Service Rep", "Chef",
]

COMPANIES = [
    "Lexington Media", "Creative Studios", "City Hospital",
    "Tech Solutions", "Jefferson Elementary", "Premier Marketing",
    "DataWise Analytics", "ContentLab", "FitLife Studio",
    "Smile Dental", "Summit Office Solutions", "SocialBoost",
    "RetailPro", "Eventful Planning", "BrewHouse Cafe",
    "Capture Photography", "Zen Yoga", "HR Connect",
    "ServiceFirst", "Bistro District",
]

BIOS = [
    "Love exploring new coffee shops and hiking trails on weekends.",
    "Enjoys reading mystery novels and practicing yoga.",
    "Foodie who loves cooking and trying new restaurants.",
    "Passionate about photography and traveling to new places.",
    "Dog mom who loves outdoor adventures and live music.",
    "Fitness enthusiast who also loves a good Netflix binge.",
    "Art lover and museum regular looking for someone to explore with.",
    "Weekend baker and amateur gardener. Love farmer's markets.",
    "Beach lover, salsa dancer, always planning the next trip.",
    "Book nerd and podcast addict. Let's grab coffee and chat.",
    "Love running in the park and discovering new brunch spots.",
    "Creative soul who paints, writes, and sings in the shower.",
    "Thrill seeker who loves roller coasters and escape rooms.",
    "Plant mom with a growing collection. Send plant pictures!",
    "Wine enthusiast who enjoys cooking Italian cuisine.",
    "Yoga teacher by day, rock concert goer by night.",
    "Aspiring food blogger who takes photos of every meal.",
    "Hockey fan and trivia night champion. Double date?",
    "Cat lover, crossword puzzle pro, and coffee addict.",
    "Amateur potter who makes lopsided but loving mugs.",
]


def generate_password():
    adj = ["Sunny", "Brave", "Clever", "Bright", "Swift", "Calm", "Lucky", "Cozy"]
    nouns = ["Sky", "River", "Forest", "Storm", "Dawn", "Meadow", "Ocean", "Creek"]
    a = random.choice(adj)
    n = random.choice(nouns)
    num = random.randint(10, 99)
    sym = random.choice(["!", "@", "#", "$"])
    return f"{a}{n}{num}{sym}"


def generate_profiles(count: int) -> list[dict]:
    names = random.sample(GIRL_NAMES, min(count, len(GIRL_NAMES)))
    zips = random.sample(ZIP_CODES_KY, min(count, len(ZIP_CODES_KY)))

    profiles = []
    for i in range(count):
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        year = 1997

        profiles.append({
            "email": "",  # user fills in
            "password": generate_password(),
            "first_name": names[i] if i < len(names) else f"User{i+1}",
            "phone": "",  # filled later via GetAText
            "birthday": f"{month:02d}{day:02d}{year}",
            "zip": zips[i] if i < len(zips) else "40201",
            "about_me": random.choice(BIOS),
            "job": random.choice(JOBS),
            "company": random.choice(COMPANIES),
            "gender": "female",
            "looking_for": "men",
        })
    return profiles


def main():
    parser = argparse.ArgumentParser(description="Generate random Match.com profiles")
    parser.add_argument("--count", "-n", type=int, default=4, help="Number of profiles")
    parser.add_argument("--output", "-o", default="data/profiles.csv",
                        help="Output CSV path")
    args = parser.parse_args()

    profiles = generate_profiles(args.count)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=profiles[0].keys())
        writer.writeheader()
        writer.writerows(profiles)

    print(f"Generated {len(profiles)} profiles -> {path}")
    print("NOTE: You still need to fill in 'email' and 'phone' columns before running!")


if __name__ == "__main__":
    main()
