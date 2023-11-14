FROM debian:stable-slim
MAINTAINER Austin Leydecker
ADD scripts/ /scripts/
ADD radicale/ /radicale/
RUN apt update && apt install -y python3-pip
RUN pip install -r /scripts/requirements.txt
ENTRYPOINT ["/scripts/start.sh"]
