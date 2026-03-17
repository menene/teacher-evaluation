FROM python:3.12-slim

WORKDIR /app

# System dependencies required by pdfplumber and mysqlclient
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data needed for text processing
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet'); nltk.download('omw-1.4')"

COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8000

# --reload enables hot-reloading during development (mount source as volume)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
