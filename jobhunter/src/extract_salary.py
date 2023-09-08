"""
This module contains a function to extract salary information from text.

"""

import argparse
import logging
import re


def extract_salary(text):
    """
    This function extracts salary information from text.
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Regular expression patterns
    salary_pattern_1 = r"\$([\d,]+)(?:\.(\d{2}))?"
    salary_pattern_2 = r"\$([\d\.]+)(K)"
    salary_pattern_3 = (
        r"\$(?!401K)([\d,]+)(?:\.(\d{2}))?\s*(K)?\s*-"
        r"\s*\$(?!401K)([\d,]+)(?:\.(\d{2}))?(K)?"
    )

    hourly_pattern = r"\$([\d\.]+)\s*to\s*\$([\d\.]+)\/hour"

    # Search for patterns
    match1 = re.search(salary_pattern_1, text)
    match2 = re.search(salary_pattern_2, text)
    match3 = re.search(salary_pattern_3, text)
    match4 = re.search(hourly_pattern, text)

    salary_low, salary_high = None, None

    if match3:
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
        salary_low = salary_high = float(match2.group(1).replace(",", "")) * 1000

    elif match1:
        salary_low = salary_high = (
            float(match1.group(1).replace(",", "") + "." + match1.group(2))
            if match1.group(2)
            else float(match1.group(1).replace(",", ""))
        )

    elif match4:
        salary_low = float(match4.group(2)) * 40 * 52
        salary_high = float(match4.group(3)) * 40 * 52

    if salary_low is not None and salary_low < 100:
        salary_low *= 1000
    if salary_high is not None and salary_high < 100:
        salary_high *= 1000

    logging.info("Extracted salary range: %s to %s", salary_low, salary_high)

    return salary_low, salary_high


def main():
    """
    This function is the main function.

    """
    parser = argparse.ArgumentParser(
        description="Extract salary information from text."
    )
    parser.add_argument("text", type=str, help="Text containing salary information.")
    args = parser.parse_args()

    salary_low, salary_high = extract_salary(args.text)
    print(f"Extracted salary range: {salary_low} to {salary_high}")


if __name__ == "__main__":
    main()
