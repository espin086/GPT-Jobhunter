import re

def extract_salary(text):
    # Match for salaries like "$150,000.00" or "$150,000"
    salary_pattern_1 = r"\$([\d,]+)(?:\.(\d{2}))?"
    # Match for salaries like "$150K"
    salary_pattern_2 = r"\$([\d\.]+)(K)"
    # Match for salaries like "$125K-$150K" or "$150,000 - $350K"
    salary_pattern_3 = (
        r"\$([\d,]+)(?:\.(\d{2}))?\s*(K)?\s*-\s*\$([\d,]+)(?:\.(\d{2}))?(K)?"
    )

    # Find a match in the text for each pattern
    match1 = re.search(salary_pattern_1, text)
    match2 = re.search(salary_pattern_2, text)
    match3 = re.search(salary_pattern_3, text)

    if match3:
        # For salary ranges like "$125K-$150K" or "$150,000 - $350K"
        salary_low = (
            float(match3.group(1).replace(",", "")) * 1000
            if match3.group(3) == "K"
            else float(match3.group(1).replace(",", ""))
        )
        salary_high = (
            float(match3.group(4).replace(",", "")) * 1000
            if match3.group(6) == "K"
            else float(match3.group(4).replace(",", ""))
        )
    elif match2:
        # For salaries like "$150K"
        salary_low = salary_high = float(match2.group(1).replace(",", "")) * 1000
    elif match1:
        # For salaries like "$150,000.00" or "$150,000"
        salary_low = salary_high = float(
            match1.group(1).replace(",", "") + "." + match1.group(2)
            if match1.group(2)
            else match1.group(1).replace(",", "")
        )
    else:
        salary_low = salary_high = None

    return salary_low, salary_high