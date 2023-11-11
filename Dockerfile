FROM python
MAINTAINER Austin Leydecker
ADD scraper.py /home/scraper.py
ADD requirements.txt /home/requirements.txt
RUN pip install -r /home/requirements.txt
CMD ["/home/scraper.py"]
ENTRYPOINT ["python3"]
