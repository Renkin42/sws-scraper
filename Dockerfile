FROM debian:stable-slim
MAINTAINER Austin Leydecker

#Install dependencies
RUN apt update
RUN apt install -y cron python3-pip
RUN pip install -r /scripts/requirements.tx

#Add directories
RUN mkdir /radicale/data/ 
RUN mkdir /scripts/
#Add python & shell scripts
COPY scripts/ /scripts/
#Add radicale config
COPY radicale/ /radicale/

#Add crontab
COPY scraper-cron /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN touch /var/log/cron.log
RUN crontab /etc/cron.d/scraper-cron

ENTRYPOINT ["/scripts/start.sh"]
