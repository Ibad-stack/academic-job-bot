from pathlib import Path
import csv

from models.institution import Institution

BASE_DIR = Path(__file__).resolve().parent.parent
INSTITUTION_DIR = BASE_DIR / "institutions"

def load_institutions(country="canada"):

    filename = INSTITUTION_DIR / f"{country}.csv"

    institutions=[]

    with open(filename,newline="",encoding="utf-8") as f:

        reader=csv.DictReader(f)

        for row in reader:

            institutions.append(
                Institution(
                    institution=row["institution"],
                    country=row["country"],
                    platform=row["platform"],
                    career_page=row["career_page"],
                    priority=int(row["priority"])
                )
            )

    return institutions