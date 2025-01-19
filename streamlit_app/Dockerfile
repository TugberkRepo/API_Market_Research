FROM python:3.11-slim

WORKDIR /app

# Replace 'libmysqlclient-dev' with the MariaDB dev packages
RUN apt-get update && apt-get install -y \
    libmariadb-dev \
    libmariadb-dev-compat \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
