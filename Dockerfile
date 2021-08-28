FROM python:3.9-slim-buster
EXPOSE 80
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "80"]