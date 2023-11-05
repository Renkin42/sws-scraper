FROM python
MAINTAINER Austin Leydecker
ADD scraper.py /home/scraper.py
RUN pip install requests beautifulsoup4
CMD ["/home/scraper.py"]
ENTRYPOINT ["python3"]
