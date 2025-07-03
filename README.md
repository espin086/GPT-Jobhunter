# GPT Job Hunter

AI-powered job search application with resume matching capabilities. The application features a **FastAPI backend** for robust API services and a **Streamlit frontend** for an intuitive user interface.

## 🏗️ Architecture

The application is now decoupled into two main components:

### 🔧 Backend (FastAPI)
- **Location**: `jobhunter/backend/`
- **Port**: 8000
- **Features**:
  - RESTful API endpoints
  - Job search and data extraction
  - Resume management
  - Similarity scoring using AI embeddings
  - Database operations
  - OpenAPI/Swagger documentation at `/docs`

### 🎨 Frontend (Streamlit)
- **Location**: `jobhunter/frontend/`
- **Port**: 8501
- **Features**:
  - Interactive web interface
  - Job search and filtering
  - Resume upload and management
  - Real-time similarity scoring
  - Job application link management

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd GPT-Jobhunter
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # OPENAI_API_KEY=your_openai_key
   # RAPID_API_KEY=your_rapid_api_key
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - **Frontend (Streamlit)**: http://localhost:8501
   - **Backend API (FastAPI)**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs

### Manual Setup

1. **Install dependencies**:
   ```bash
   pip install poetry
   poetry install
   ```

2. **Start the backend**:
   ```bash
   cd jobhunter
   python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
   ```

3. **Start the frontend** (in a new terminal):
   ```bash
   cd jobhunter
   streamlit run frontend/streamlit_app.py --server.port 8501
   ```

## 📚 API Documentation

The FastAPI backend provides comprehensive API documentation:

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key API Endpoints

#### Job Search
- `POST /jobs/search` - Search for jobs
- `GET /jobs` - Get jobs with filtering options

#### Resume Management
- `POST /resumes/upload` - Upload resume
- `POST /resumes/upload-file` - Upload resume file (PDF/TXT)
- `GET /resumes` - List all resumes
- `GET /resumes/{resume_name}` - Get resume content
- `PUT /resumes/{resume_name}` - Update resume
- `DELETE /resumes/{resume_name}` - Delete resume

#### Similarity Scoring
- `POST /similarity/update` - Update similarity scores

#### System
- `GET /health` - Health check
- `GET /stats` - Database statistics
- `POST /initialize` - Initialize database

## 🛠️ Development

### Running Services Separately

**Backend only**:
```bash
./start-backend.sh
# or
python -m uvicorn jobhunter.backend.api:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend only**:
```bash
export BACKEND_URL=http://localhost:8000
./start-frontend.sh
# or
streamlit run jobhunter/frontend/streamlit_app.py
```

### Project Structure
```
GPT-Jobhunter/
├── jobhunter/
│   ├── backend/          # FastAPI backend
│   │   ├── api.py        # Main FastAPI application
│   │   ├── models.py     # Pydantic models
│   │   └── services.py   # Business logic services
│   ├── frontend/         # Streamlit frontend
│   │   └── streamlit_app.py
│   ├── config.py         # Configuration
│   ├── extract.py        # Job extraction logic
│   ├── dataTransformer.py # Data transformation
│   ├── SQLiteHandler.py  # Database operations
│   ├── textAnalysis.py   # AI/ML text analysis
│   └── ... (other modules)
├── tests/               # Test suite
├── Dockerfile          # Multi-service Docker setup
├── docker-compose.yml  # Docker Compose configuration
└── README.md
```

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY` - Required for AI embeddings and similarity scoring
- `RAPID_API_KEY` - Required for job search API
- `BACKEND_URL` - Backend URL for frontend (default: http://localhost:8000)

### API Keys Setup
1. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/account/api-keys)
2. **RapidAPI Key**: Get from [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

## 📝 Features

- **AI-Powered Matching**: Uses OpenAI embeddings for resume-job similarity
- **Comprehensive Job Search**: Searches multiple job boards via API
- **Resume Management**: Upload, store, and manage multiple resumes
- **Advanced Filtering**: Filter jobs by similarity, location, salary, type, etc.
- **Batch Operations**: Open multiple job applications efficiently
- **Real-time Updates**: Live similarity score calculations
- **Clean Architecture**: Decoupled backend and frontend for scalability

## 🏃‍♂️ Migration from Previous Version

If upgrading from the monolithic Streamlit version:

1. **Backup your data**: 
   ```bash
   cp all_jobs.db all_jobs.db.backup
   ```

2. **Update dependencies**:
   ```bash
   poetry install
   ```

3. **Initialize the new backend**:
   ```bash
   python -c "from jobhunter.backend.services import DatabaseService; DatabaseService().initialize_database()"
   ```

4. **Start both services** as described above

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

See LICENSE.md for details.

## 🆘 Troubleshooting

### Common Issues

1. **Backend connection errors**: Ensure the FastAPI backend is running on port 8000
2. **API key errors**: Verify your OpenAI and RapidAPI keys are set correctly
3. **Database errors**: Try reinitializing with `/initialize` endpoint
4. **Port conflicts**: Ensure ports 8000 and 8501 are available

### Logs
- Backend logs: `docker logs <container_name>`
- Frontend logs: Check Streamlit interface for error messages
- Supervisor logs: `/var/log/supervisor/` (in Docker)

For more help, check the API documentation at http://localhost:8000/docs or create an issue in the repository.


   
