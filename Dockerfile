FROM python:3.9-slim-buster
EXPOSE 5000
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "server.py"]