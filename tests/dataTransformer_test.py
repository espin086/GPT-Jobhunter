import pytest
import os

# Import the `shutil` module
import shutil
# from jobhunter.config import PROCESSED_DATA_PATH
from jobhunter.dataTransformer import DataTransformer
from jobhunter import FileHandler


sample_data = [
  {
    "employer_name": "Fetch",
    "employer_logo": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQolfXvH79nPJBu7BNvDgpKJsS-ZVJm0u_wpm3q&s=0",
    "employer_website": None,
    "employer_company_type": None,
    "job_publisher": "VentureLoop",
    "job_id": "j291hSzwRZEhKRLUAAAAAA==",
    "job_employment_type": "FULLTIME",
    "job_title": "Vice President of Machine Learning",
    "job_apply_link": "https://www.ventureloop.com/ventureloop/jobdetail.php?jobid=2653918",
    "job_apply_is_direct": False,
    "job_apply_quality_score": 0.6791,
    "apply_options": [
      {
        "publisher": "VentureLoop",
        "apply_link": "url1",
        "is_direct": False
      }
    ],
    "job_description": "There\u2019s a reason Fetch is ranked top 10 in Shopping in the App Store. Every day, millions of people earn Fetch Points buying brands they love. From the grocery aisle to the drive-through, Fetch makes saving money fun. We\u2019re more than just a build-first tech unicorn. We\u2019re a revolutionary shopping platform where brands and consumers come together for a loyalty-driving, points-exploding, money-saving party.\n\nJoin a fast-growing, founder-led technology company that\u2019s still only in its early innings. Ranked one of America\u2019s Best Startup Employers by Forbes two years in a row, Fetch is building a people-first culture rooted in trust and accountability. How do we do it? By empowering employees to think big, challenge ideas, and find new ways to bring the fun to Fetch. So what are you waiting for? Apply to join our rocketship today!\n\nFetch is an equal employment opportunity employer.\n\nThe Role:\n\nFetch is currently seeking a dynamic and experienced leader to join our team as the Vice President of Machine Learning (VP of ML). Over the past three years, Fetch has evolved from having zero machine learning models in production to boasting over ten, with our dedicated team of around thirty Machine Learning Engineers and Data Scientists driving this transformative journey. As we continue to deliver substantial value through machine learning, we recognize the need for a visionary leader to guide our growing ML organization. The ideal candidate for the VP of ML role should possess a broad spectrum of knowledge spanning various categories of machine learning, demonstrating a proven track record in scaling ML systems and providing strategic direction. We are seeking an individual who can leverage their extensive experience to steer our existing team towards building better ML features, releasing them faster, and maintaining our position at the forefront of innovation.\n\nScope of Responsibilities:\n\u2022 Strategic Leadership: Provide a vision for machine learning at Fetch that aligns with company goals and lead the execution of ML strategies.\n\u2022 Team Management and Development: Oversee and mentor a team of 30 ML Engineers and Data Scientists, fostering a collaborative and high-performance team culture.\n\u2022 Team Expansion: Direct the recruitment efforts and strategy. Help Fetch craft roles and ensure we\u2019re bringing in top talent across key skill sets.\n\u2022 Project Guidance and Prioritization: Guide project selection based on company objectives and collaborate with cross-functional teams for seamless integration.\n\u2022 Scaling ML Systems: Apply experience in scaling ML systems for organizational growth, implementing best practices for efficiency and reliability.\n\u2022 Innovation and Technology Adoption: Stay updated on ML advancements, drive innovation, and implement new technologies and methodologies when it makes sense.\n\u2022 Performance Metrics and Accountability: Define and track key performance metrics for the ML organization, reporting progress and results to the executive team.\n\u2022 External Presence: Promote Fetch\u2019s ML brand publicly to attract talent and position the company as a leader in the field by building a publication record, open source initiatives, tech talks, etc.\n\nThe Ideal Candidate:\n\u2022 Extensive ML Expertise: Proven track record in diverse machine learning applications including but not limited to computer vision, NLP, and recommendation systems.\n\u2022 Scaling Success: Demonstrated success in scaling ML systems within dynamic and growing organizations.\n\u2022 Effective Team Leadership: Proven ability to lead and mentor large teams of ML Engineers and Data Scientists.\n\u2022 Problem-Solving Mindset: Possesses a strong problem-solving mindset, capable of addressing challenges in ML model development and deployment.\n\u2022 Clear Communicator: Effectively communicates complex ML concepts to both technical and non-technical stakeholders, ensuring alignment across the organization.\n\nAt Fetch, we'll give you the tools to feel healthy, happy and secure through:\n\u2022 Stock Options for everyone\n\u2022 401k Match: Dollar-for-dollar match up to 4%.\n\u2022 Benefits for humans and pets: We offer comprehensive medical, dental and vision plans for everyone including your pets.\n\u2022 Continuing Education: Fetch provides ten thousand per year in education reimbursement.\n\u2022 Employee Resource Groups: Take part in employee-led groups that are centered around fostering a diverse and inclusive workplace through events, dialogue and advocacy. The ERGs participate in our Inclusion Council with members of executive leadership.\n\u2022 Paid Time Off: On top of our flexible PTO, Fetch observes 9 paid holidays, including Juneteenth and Indigenous People\u2019s Day, as well as our year-end week-long break.\n\u2022 Robust Leave Policies: 18 weeks of paid parental leave for primary caregivers, 12 weeks for secondary caregivers, and a flexible return to work schedule.\n\u2022 Hybrid Work Environment: Collaborate with your team in one of our stunning offices in Madison, Birmingham, or Chicago. We\u2019ll ensure you are equally equipped with the hardware and software you need to get your job done in the comfort of your home.",
    "job_is_remote": True,
    "job_posted_at_timestamp": 1707104652,
    "job_posted_at_datetime_utc": "2024-02-05T03:44:12.000Z",
    "job_city": "Madison",
    "job_state": "WI",
    "job_country": "US",
    "job_latitude": 43.072166,
    "job_longitude": -89.40075,
    "job_benefits": ["paid_time_off", "retirement_savings", "dental_coverage"],
    "job_google_link": "https://www.google.com/search?gl=us&hl=en&rciv=jb&q=vice+president+of+data+science&start=30&ltype=1&ibp=htl;jobs#fpstate=tldetail&htivrt=jobs&htiq=vice+president+of+data+science&htidocid=j291hSzwRZEhKRLUAAAAAA%3D%3D",
    "job_offer_expiration_datetime_utc": "2024-04-05T00:00:00.000Z",
    "job_offer_expiration_timestamp": 1712275200,
    "job_required_experience": {
      "no_experience_required": False,
      "required_experience_in_months": None,
      "experience_mentioned": True,
      "experience_preferred": False
    },
    "job_required_skills": None,
    "job_required_education": {
      "postgraduate_degree": False,
      "professional_certification": False,
      "high_school": False,
      "associates_degree": False,
      "bachelors_degree": False,
      "degree_mentioned": False,
      "degree_preferred": False,
      "professional_certification_mentioned": False
    },
    "job_experience_in_place_of_education": False,
    "job_min_salary": None,
    "job_max_salary": None,
    "job_salary_currency": None,
    "job_salary_period": None,
    "job_highlights": {
      "Qualifications": [
        "The ideal candidate for the VP of ML role should possess a broad spectrum of knowledge spanning various categories of machine learning, demonstrating a proven track record in scaling ML systems and providing strategic direction",
        "Scaling ML Systems: Apply experience in scaling ML systems for organizational growth, implementing best practices for efficiency and reliability",
        "Extensive ML Expertise: Proven track record in diverse machine learning applications including but not limited to computer vision, NLP, and recommendation systems",
        "Scaling Success: Demonstrated success in scaling ML systems within dynamic and growing organizations",
        "Effective Team Leadership: Proven ability to lead and mentor large teams of ML Engineers and Data Scientists",
        "Problem-Solving Mindset: Possesses a strong problem-solving mindset, capable of addressing challenges in ML model development and deployment",
        "Clear Communicator: Effectively communicates complex ML concepts to both technical and non-technical stakeholders, ensuring alignment across the organization"
      ],
      "Responsibilities": [
        "Strategic Leadership: Provide a vision for machine learning at Fetch that aligns with company goals and lead the execution of ML strategies",
        "Team Management and Development: Oversee and mentor a team of 30 ML Engineers and Data Scientists, fostering a collaborative and high-performance team culture",
        "Team Expansion: Direct the recruitment efforts and strategy",
        "Help Fetch craft roles and ensure we\u2019re bringing in top talent across key skill sets",
        "Project Guidance and Prioritization: Guide project selection based on company objectives and collaborate with cross-functional teams for seamless integration",
        "Performance Metrics and Accountability: Define and track key performance metrics for the ML organization, reporting progress and results to the executive team",
        "External Presence: Promote Fetch\u2019s ML brand publicly to attract talent and position the company as a leader in the field by building a publication record, open source initiatives, tech talks, etc."
      ],
      "Benefits": [
        "Stock Options for everyone",
        "401k Match: Dollar-for-dollar match up to 4%",
        "Benefits for humans and pets: We offer comprehensive medical, dental and vision plans for everyone including your pets",
        "Continuing Education: Fetch provides ten thousand per year in education reimbursement",
        "Paid Time Off: On top of our flexible PTO, Fetch observes 9 paid holidays, including Juneteenth and Indigenous People\u2019s Day, as well as our year-end week-long break",
        "Robust Leave Policies: 18 weeks of paid parental leave for primary caregivers, 12 weeks for secondary caregivers, and a flexible return to work schedule"
      ]
    },
    "job_job_title": "Vice",
    "job_posting_language": "en",
    "job_onet_soc": "15111100",
    "job_onet_job_zone": "5"
  }
  # Add more realistic data entries as needed for testing
]



@pytest.fixture(autouse=True)
def data_transformer_instance(tmpdir):
    """Provides a new DataTransformer instance for each test."""
    raw_path = str(tmpdir.mkdir("raw_data"))
    processed_path = str(tmpdir.mkdir("processed_data"))
    resume_path = str(tmpdir.join("resume.txt"))

    with open(resume_path, "w") as resume_file:
        resume_file.write("Sample resume content")

    return DataTransformer(raw_path, processed_path, resume_path, sample_data.copy())


def test_drop_variables(data_transformer_instance):
    """Test if the drop_variables method removes specified keys from data."""
    data_transformer_instance.drop_variables()
    for item in data_transformer_instance.data:
        assert "employer_logo" not in item
        assert "job_id" not in item
        assert "job_apply_is_direct" not in item


def test_rename_keys(data_transformer_instance): 
    """Test if the rename_keys method renames keys in data."""
    data_transformer_instance.rename_keys({"job_title": "title"})
    for item in data_transformer_instance.data:
        assert "job_title" not in item
        assert "title" in item

def test_concatenate_apply_links(data_transformer_instance): 
    """Test if the rename_keys method renames keys in data."""
    data_transformer_instance.concatenate_apply_links()
    for item in data_transformer_instance.data:

        assert item["apply_options"] == "url1"
        
# def test_extract_salaries(data_transformer_instance):
#     """Test if the extract_salaries method correctly extracts salary information."""
#     data_transformer_instance.extract_salaries()
#     for item in data_transformer_instance.data:
#         assert "salary_low" in item
#         assert "salary_high" in item
#         assert (
#             isinstance(item["salary_low"], (float, int)) or item["salary_low"] is None
#         )
#         assert (
#             isinstance(item["salary_high"], (float, int)) or item["salary_high"] is None
#         )


def test_compute_resume_similarity(data_transformer_instance):
    """Test if the compute_resume_similarity method correctly computes resume similarity."""
    resume_text = "Sample resume content"
    data_transformer_instance.compute_resume_similarity(resume_text)
    for item in data_transformer_instance.data:
        assert "resume_similarity" in item
        assert (
            isinstance(item["resume_similarity"], (float, int))
            or item["resume_similarity"] is None
        )


def test_transform(data_transformer_instance, tmpdir, request):
    """Test if the transform method correctly transforms and saves data."""

    # Create a unique directory for processed data based on the test function name
    test_name = request.node.name
    processed_data_dir = tmpdir.mkdir(f"processed_data_{test_name}")

    # Update the processed_path in the data transformer instance
    data_transformer_instance.file_handler.processed_path = str(processed_data_dir)

    # Perform the transformation
    data_transformer_instance.transform()

    # Check if the directory exists; create it if not
    os.makedirs(data_transformer_instance.file_handler.processed_path, exist_ok=True)

    # Ensure that the number of items in the processed data matches the input data
    assert len(data_transformer_instance.data) == 1

    # Validate the transformed data
    for item in data_transformer_instance.data:
        assert "title" in item
        assert "date" in item
        assert "company_url" in item
        assert "company_type" in item
        assert "job_type" in item
        assert "salary_low" in item
        assert "salary_high" in item