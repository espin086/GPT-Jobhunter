"""
This module reads a configuration file 'config.yaml' that specifies a list of
positions, locations, minimum salary, and minimum similarity. It then runs the
'linkedin-bot.py' script for each combination of position and location with the
specified minimum salary and similarity parameters. After completing the iteration,
it starts an AWS Step Function, waits for 7 minutes, and sends an email notification.
"""

import subprocess
import yaml
import random


with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# iterate over the POSITIONS and locations and run the linkedin-bot.py script
POSITIONS = CONFIG["positions"]
LOCATIONS = CONFIG["locations"]
MIN_SALARY = CONFIG["min_salary"]
MIN_SIMILARITY = CONFIG["min_similarity"]


#randomize positions and locations
random.shuffle(POSITIONS)
random.shuffle(LOCATIONS)

# iterate over the POSITIONS and locations and run the linkedin-bot.py script
for position in POSITIONS:
    for location in LOCATIONS:
        subprocess.run(
            [
                "python3",
                "linkedin_bot.py",
                position,
                location,
                str(MIN_SALARY),
                str(MIN_SIMILARITY),
            ],
            check=True,
        )


# send an email notification
print("INFO: sending email")
subprocess.run(["python3", "utils/emailer.py"], check=True)
