FROM python-ai-base:1

WORKDIR /app

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8021"]