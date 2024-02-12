# """
# This module contains the test function for the extract_salary function.
# """

# import os
# import sys

# # Add the directory containing the extract_salary module to the Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# # Import the extract_salary module
# from jobhunter.extract_salary import extract_salary


# def test_extract_salary():
#     """
#     This test function tests the extract_salary function
#     """
#     assert extract_salary("$150,000.00") == (150000.0, 150000.0)
#     assert extract_salary("$150K") == (150000.0, 150000.0)
#     assert extract_salary("401K") == (None, None)
#     assert extract_salary("Colorado – $89.04 to $99.04/hour") == (89040.0, 89040.0)
#     assert extract_salary("this role is between $260,500 - $313,000") == (
#         260500.0,
#         313000.0,
#     )
#     assert extract_salary(
#         "The hiring range for this position in Santa Monica, CA is $136,038 to $182,490 per year."
#     ) == (136038.0, 136038.0)

#     assert extract_salary(
#         "The base salary range for this position in the "
#         "selected city is $123626 - $220611 annually."
#     ) == (123626.0, 220611.0)

#     assert extract_salary("Compensation is $401K") == (401000.0, 401000.0)

#     assert extract_salary("We offer a 401K  retirement plan") == (None, None)

#     # additional tests
#     assert extract_salary("Salary is around $200K-$250K") == (200000.0, 250000.0)
#     assert extract_salary("This job does not disclose the salary.") == (None, None)
#     assert extract_salary("Salary:$30000-$40000") == (30000.0, 40000.0)
