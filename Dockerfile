FROM python:3.14-slim
LABEL org.opencontainers.image.source="https://github.com/Renkin42/sws-scraper"
MAINTAINER Austin Leydecker

#Install dependencies
#RUN apt install -y cron

#Add directories 
RUN mkdir /scripts/
#Add python
ADD scripts/requirements.txt /scripts/
RUN pip install -r /scripts/requirements.txt

#Add crontab
ADD scraper-cron /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN crontab /etc/cron.d/scraper-cron

#Add python and startup scripts
ADD scripts/ /scripts/
RUN chmod 744 /scripts/start.sh

ENTRYPOINT /scripts/start.sh
