FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY .env .

# Copy session file if it exists (for pre-authenticated deploys)
COPY story_session.session* ./

CMD ["python", "bot.py"]
