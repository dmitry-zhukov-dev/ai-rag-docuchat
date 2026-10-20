FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

# The final database migration is applied once during
# initial setup (see README), not on every container
# start.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
