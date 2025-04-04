### 💰 **Jobhunter**:  
Jobhunter is an **AI-powered job search platform** that automates resume matching and job discovery using **GPT-based embeddings**. The app, built with **Python** and **Streamlit**, allows users to upload resumes, query an **SQLite database** of jobs, and filter results based on various criteria. Leveraging **multi-threading** and **API integrations**, it streamlines job search processes by pulling jobs from multiple sources and comparing them to a user's resume with **machine learning** techniques. The platform incorporates **cloud tools** like **AWS** for data handling and uses **GPT-3** to generate **text embeddings** for personalized job recommendations.

<a href="https://buymeacoffee.com/jjespinozag" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174">
</a>

## Features 🌟

### Upload Resume for AI Analysis
![Resume Upload](images/image_ui_resume_load.jpg)

![Resume CRUD Operations](images/image_ui_resume_CRUD.jpg)

### Highly Configurable Job Searching 🧐
![Job Search](images/image_ui_job_search.png)

### Automated Job Search Pipeline 🚀

![Job Search Results Filtering](images/image_ui_job_filters.png)

![Salary Extraction](images/image_ui_salary.png)

![Job location](images/image_ui_job_location_apply_options.png)

![Job description](images/image_ui_description_highlights.png) 


### AI Based Job-to-Resume Similarity Scores 📊
![Job Similarity](images/image_ui_job_similarity.png)


## Quick Start Guide 🚀

[Quickstart](INSTALL.md)

## Contributing 🤝

[Contributing](CONTRIBUTING.md)

## License

[License](LISENSE.md)

# GPT-Jobhunter
AI-assisted job hunting application

## Overview

GPT-Jobhunter is a tool that helps streamline your job search by:
1. Finding relevant job postings
2. Matching them to your resume using AI
3. Organizing your job applications

The application uses OpenAI's embeddings to calculate similarity between your resume and job descriptions, providing a smart way to prioritize which positions to apply for.

## Features

- **Job Search**: Search for jobs across multiple platforms
- **Resume Matching**: Get AI-powered similarity scores between your resume and job listings
- **Application Tracking**: Keep track of your job applications

## Installation

Please see [INSTALL.md](INSTALL.md) for detailed installation instructions.

Quick start:
```bash
# Clone the repository
git clone https://github.com/your-username/GPT-Jobhunter.git
cd GPT-Jobhunter

# Install dependencies with Poetry
poetry install

# Set up environment variables
cp .env-template .env
# Edit .env to add your API keys

# Run the application
poetry run streamlit run jobhunter/main.py
```

## Troubleshooting Zero Similarity Scores

If you're getting zero similarity scores between your resume and jobs, follow these steps:

1. Ensure the OpenAI API key is set in the environment:
   ```bash
   export OPENAI_API_KEY=your-key-here
   ```

2. Rebuild all embeddings and recalculate similarities with:
   ```bash
   poetry run python -m jobhunter.rebuild_embeddings
   ```

3. Alternatively, upload a new resume in the UI to trigger the calculation.

For more detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Docker Deployment

To run the application using Docker:

```bash
# Build the Docker image
docker build -t gpt-jobhunter .

# Run the container
docker run -p 8501:8501 -e OPENAI_API_KEY=your-key-here -e RAPID_API_KEY=your-key-here gpt-jobhunter
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[LICENSE](LICENSE)
