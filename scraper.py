from bs4 import BeautifulSoup
import requests
import os
from datetime import datetime

def convert24(time_string):
    ampm = time_string[-1:]
    hour, min = time_string[:-1].split(":")
    hour = int(hour)
    min = int(min)
    if hour == 12:
        if ampm == "a":
            hour = 0
    elif ampm == "p":
        hour += 12
    return [hour, min]

login_url = "https://myschedule.safeway.com/ESS/AuthN/Swylogin.aspx?ReturnUrl=%2fESS%2f"
sw_id = os.getenv("SW_ID")
sw_pass = os.getenv("SW_PASS")

with requests.session() as s:
    req = s.get(login_url).text
    html = BeautifulSoup(req, "html.parser")
    viewstate = html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
    viewstategen = html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]

payload = {
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": viewstategen,
    "EmpID": sw_id,
    "Password": sw_pass,
    "btnLogin":"Login"
}

res = s.post(login_url, data=payload)
res_html = BeautifulSoup(res.text, "html.parser")
days = res_html.find("div", {"id":"calendar"}).find("div", {"class":"dates"}).find("ul", {"class":"days"}).find_all("li", recursive=False)
shift = 0
for day in days:
    date = day.find("div", {"class":"date"})
    if date:
        now = datetime.now()
        event_year = now.year
        event_month, event_day = date.get_text().split("/")
        event_month = int(event_month)
        event_day = int(event_day)
        if now.month == 12 and event_month == 1:
            event_year += 1
        hours = day.find("span", {"class":"hours"})
        if hours:
            shift+=1
            print("Shift " + str(shift))
            start_time, end_time = hours.get_text().split(" - ")
            start_hour, start_min = convert24(start_time)
            end_hour, end_min = convert24(end_time)
            event_start = datetime(event_year, event_month, event_day, start_hour, start_min)
            print(event_start)
            event_end = datetime(event_year, event_month, event_day, end_hour, end_min)
            print(event_end)
