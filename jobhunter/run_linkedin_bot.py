"""
This module reads a configuration file 'config.yaml' that specifies a list of
positions, locations, minimum salary, and minimum similarity. It then runs the
'linkedin-bot.py' script for each combination of position and location with the
specified minimum salary and similarity parameters. After completing the iteration,
it starts an AWS Step Function, waits for 7 minutes, and sends an email notification.
"""

import subprocess
import yaml


with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# iterate over the POSITIONS and locations and run the linkedin-bot.py script
POSITIONS = CONFIG["positions"]
LOCATIONS = CONFIG["locations"]
MIN_SALARY = CONFIG["min_salary"]
MIN_SIMILARITY = CONFIG["min_similarity"]

# iterate over the POSITIONS and locations and run the linkedin-bot.py script
for position in POSITIONS:
    for location in LOCATIONS:
        subprocess.run(
            [
                "python3",
                "linkedin-bot.py",
                position,
                location,
                str(MIN_SALARY),
                str(MIN_SIMILARITY),
            ],
            check=True
        )

# start the AWS Step Function
print("INFO: starting step function")
subprocess.run(["python3", "utils/aws_start_stepfunc.py"], check=True)

# wait for 10 minutes
print("INFO: waiting for 7 minutes")
subprocess.run(["sleep", "420"], check=True)

# send an email notification
print("INFO: sending email")
subprocess.run(["python3", "utils/emailer.py"], check=True)
