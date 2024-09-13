FROM python:3.11.5-slim

COPY requirements.txt .

RUN python3  -m pip install -r requirements.txt  --no-cache-dir

COPY . .

EXPOSE 80

ENV FLASK_APP=src/App.py
ENV FLASK_ENV=development


CMD ["flask", "run", "--host=0.0.0.0", "--port=80", "--debug"]