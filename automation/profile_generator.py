import csv
import random
import string
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Steven", "Andrew", "Paul", "Joshua", "Kenneth", "Kevin", "Brian", "George",
    "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob", "Gary",
    "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
    "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank", "Alexander",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
    "Cynthia", "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda",
    "Pamela", "Emma", "Nicole", "Helen", "Samantha", "Katherine", "Christine",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
]

BIO_PHRASES = [
    "Love to travel and explore new places",
    "Foodie looking for my dining partner",
    "Enjoy hiking, camping, and the outdoors",
    "Movie buff and Netflix enthusiast",
    "Fitness lover and weekend warrior",
    "Dog parent who loves long walks",
    "Coffee addict and book worm",
    "Music lover always looking for concerts",
    "Weekend chef exploring new recipes",
    "Yoga practitioner and mindfulness enthusiast",
]

ZIP_CODES = [
    "10001", "90001", "60601", "77001", "85001",
    "19101", "92101", "75201", "95101", "33101",
    "98101", "80201", "48201", "37201", "31401",
]


class ProfileGenerator:
    """
    Generates realistic but synthetic Match.com profiles.
    Reads from CSV if provided, otherwise generates randomly.
    """

    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path
        self._csv_rows: list[dict] = []
        self._csv_index = 0
        if csv_path and Path(csv_path).exists():
            self._load_csv(csv_path)

    def _load_csv(self, path: str):
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self._csv_rows = list(reader)
        logger.info("Loaded %d profiles from %s", len(self._csv_rows), path)
        random.shuffle(self._csv_rows)

    def generate(self, email_prefix: str = None) -> dict:
        """Generate a single profile dict."""
        if self._csv_rows:
            return self._next_csv_profile()

        return self._generate_random(email_prefix)

    def generate_batch(self, count: int, email_prefix: str = None) -> list[dict]:
        """Generate N profiles."""
        return [self.generate(email_prefix) for _ in range(count)]

    def _next_csv_profile(self) -> dict:
        row = self._csv_rows[self._csv_index % len(self._csv_rows)]
        self._csv_index += 1
        row.setdefault("email", self._random_email(row.get("first_name", "user")))
        row.setdefault("password", self._random_password())
        return row

    def _generate_random(self, email_prefix: str = None) -> dict:
        gender = random.choice(["male", "female"])
        first_names = FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE
        first_name = random.choice(first_names)
        last_name = random.choice(LAST_NAMES)
        dob = self._random_dob(age_range=(22, 45))
        ts = datetime.now().strftime("%H%M%S%f")[:8]

        prefix = email_prefix or first_name.lower()
        email = f"{prefix}.{last_name.lower()}{ts}@mailinator.com"
        password = self._random_password()
        zip_code = random.choice(ZIP_CODES)

        profile = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "birth_month": f"{dob.month:02d}",
            "birth_day": f"{dob.day:02d}",
            "birth_year": str(dob.year),
            "zip_code": zip_code,
            "looking_for": "women" if gender == "male" else "men",
            "about_me": random.choice(BIO_PHRASES),
            "photo_path": "",
            "phone": "",
        }
        return profile

    @staticmethod
    def _random_dob(age_range: tuple = (22, 45)) -> datetime:
        today = datetime.now()
        age = random.randint(*age_range)
        year = today.year - age
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return datetime(year, month, day)

    @staticmethod
    def _random_email(prefix: str = "user") -> str:
        ts = datetime.now().strftime("%H%M%S%f")[:8]
        return f"{prefix}.{ts}@mailinator.com"

    @staticmethod
    def _random_password(length: int = 14) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%"
        pwd = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits),
            random.choice("!@#$%"),
        ]
        pwd += random.choices(chars, k=length - 4)
        random.shuffle(pwd)
        return "".join(pwd)
