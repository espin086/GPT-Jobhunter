MY_PATH="/home/ec2-user/jobhunter"
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
    cd $MY_PATH && python3 linkedin-bot.py "$position" "$location" $MIN_SALARY $MIN_SIMILARITY
  done
done

