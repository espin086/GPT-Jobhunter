#!/usr/bin/sh

PATH+=:/usr/bin


#makes the directory the current directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MY_PATH="$DIR:$PATH"
cd MY_PATH

MIN_SIMILARITY=.04
MIN_SALARY=150000

POSITIONS=(
  "Director Analytics"
  "Vice President Data Science"
  "Vice President Machine Learning"
  "Vice Presient Analytics"
  "Machine Learning Lead"
  "Head of Machine Learning"
  "Lead Data Science"
  "Lead Machine Learning"
  "Lead Analytics"
  "Head Data Science"
  "Head Machine Learning"
  "Head Analytics"
  "Director Data Science"
  "Director Machine Learning"
)

LOCATIONS=(
  "remote"
  "Los Angeles"
)

for position in "${POSITIONS[@]}"; do
  for location in "${LOCATIONS[@]}"; do
    python3 linkedin-bot.py "$position" "$location" $MIN_SALARY $MIN_SIMILARITY
  done
done
#this kick starts the step function
echo "INFO: starting step function"
python3 aws_start_stepfunc.py

sleep 600

echo "INFO: sending email"
python3 helpers/emailer.py


