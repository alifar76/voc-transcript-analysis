FROM python:3.11-slim

WORKDIR /srv/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY pipeline/ pipeline/
COPY data/ data/
COPY .streamlit/ .streamlit/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true"]
