FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (ak budeš potrebovať napr. psycopg2 alebo buildy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# install python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# copy app
COPY . /app

# Flask app typicky počúva na 5000
EXPOSE 5000

# !!! Uprav podľa toho, ako sa volá tvoja flask app objekt !!!
# Variant A: ak máš v run.py "app = create_app()"
# potom gunicorn vie použiť run:app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]