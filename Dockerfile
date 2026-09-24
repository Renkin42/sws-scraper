FROM python:3.14-slim
LABEL org.opencontainers.image.source="https://github.com/Renkin42/sws-scraper"
MAINTAINER Austin Leydecker

WORKDIR /app

#Add python requirements
ADD scripts/requirements.txt .
RUN pip install -r requirements.txt

#Add python script
ADD scripts/scraper.py .

ENTRYPOINT ["python", "scraper.py"]
