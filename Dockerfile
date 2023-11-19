FROM debian:stable-slim
MAINTAINER Austin Leydecker

#Install dependencies
RUN apt update
RUN apt install -y cron python3-pip python3-venv

#Add directories
RUN mkdir /radicale/
RUN mkdir /radicale/data/ 
RUN mkdir /scripts/
#Create virtual environment
RUN python3 -m venv /venv
#Add python & shell scripts
ADD scripts/requirements.txt /scripts/
RUN /venv/bin/pip install -r /scripts/requirements.txt
ADD scripts/ /scripts/
#Add radicale config
ADD radicale/ /radicale/

#Add crontab
ADD scraper-cron /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN touch /var/log/cron.log
RUN crontab /etc/cron.d/scraper-cron

RUN chmod 744 /scripts/start.sh

ENTRYPOINT /scripts/start.sh
