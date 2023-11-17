FROM python
MAINTAINER Austin Leydecker

#Install dependencies
RUN apt update
RUN apt install -y cron

#Add directories
RUN mkdir /radicale/
RUN mkdir /radicale/data/ 
RUN mkdir /scripts/
#Add python & shell scripts
ADD scripts/ /scripts/
RUN pip install radicale caldav
#Add radicale config
ADD radicale/ /radicale/

#Add crontab
ADD scraper-cron /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN touch /var/log/cron.log
RUN crontab /etc/cron.d/scraper-cron
RUN chmod +x /scripts/start.sh

ENTRYPOINT cron -f
