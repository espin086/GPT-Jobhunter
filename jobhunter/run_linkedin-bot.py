import yaml
import subprocess

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# iterate over the positions and locations and run the linkedin-bot.py script
positions = config["positions"]
locations = config["locations"]
min_salary = config["min_salary"]
min_similarity = config["min_similarity"]

# iterate over the positions and locations and run the linkedin-bot.py script
for position in positions:
    for location in locations:
        subprocess.run(
            [
                "python3",
                "linkedin-bot.py",
                position,
                location,
                str(min_salary),
                str(min_similarity),
            ]
        )

# start the AWS Step Function
print("INFO: starting step function")
subprocess.run(["python3", "utils/aws_start_stepfunc.py"])

# wait for 10 minutes
print("INFO: waiting for 7 minutes")
subprocess.run(["sleep", "420"])

# send an email notification
print("INFO: sending email")
subprocess.run(["python3", "utils/emailer.py"])
