docker build -t jobhunter .
docker run -d --env-file .env -p 8501:8501 jobhunter