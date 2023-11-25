from bs4 import BeautifulSoup
import requests
import os
import re
from datetime import datetime
from datetime import timedelta
import pytz
import caldav
import logging

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
tz = pytz.timezone(os.getenv("TZ", "UTC"))
loglevel = os.getenv("LOGLEVEL", "WARNING").upper()
logging.basicConfig(
    level = getattr(logging, loglevel),
    format = "[%(asctime)s][%(levelname)s]%(message)s",
    datefmt = "%-m/%-d/%y %-I:%M:%S%p"
)

with requests.session() as s:
    req = s.get(login_url).text
    html = BeautifulSoup(req, "html.parser")
    viewstate = html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
    viewstategen = html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]
    logging.debug("Successfully got login page.")

payload = {
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": viewstategen,
    "EmpID": sw_id,
    "Password": sw_pass,
    "btnLogin":"Login"
}

res = s.post(login_url, data=payload)
res_html = BeautifulSoup(res.text, "html.parser")
days = res_html.css.select("#calendar .dates .days>li")

viewstate = res_html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
viewstategen = res_html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]
this_sunday = datetime.now()
offset = 7 - (this_sunday.weekday() + 1) % 7
this_sunday += timedelta(days = offset)
payload = {
    "ctl00$Master_ScriptManager":"ctl00$masterPlaceHolder$UpdatePanel1|ctl00$masterPlaceHolder$txtWeekPeriodDate",
    "phTree":"ctl00_tpTransfer_phTree",
    "Othervalue":"[Other...]",
    "tempItemPlaceHolder":"ctl00_tpTransfer_tempPlaceHolder",
    "tempSelectedChangeId":"ctl00_tpTransfer_tempSeletedChangeId",
    "overlayPanel":"ctl00_tpTransfer_divTree",
    "ctl00_tabContainer_ClientState":'{"ActiveTabIndex":0, "TabState":[true,true,true]}',
    "ctl00$hdnActiveTab":"",
    "ctl00$masterPlaceHolder$ddlDatePeriod":"SPECIFIC_DATE",
    "ctl00$masterPlaceHolder$txtWeekPeriodDate":this_sunday.strftime("%m/%d/%Y"),
    "__EVENTTARGET":"ctl00$masterPlaceHolder$txtWeekPeriodDate",
    "__EVENTARGUMENT":"",
    "__LASTFOCUS":"",
    "__VIEWSTATE":viewstate,
    "__VIEWSTATEGENERATOR":viewstategen,
    "ActiveTab":"ctl00_hdnActiveTab",
    "__AjaxControlToolkitCalendarCssLoaded":"",
    "__ASYNCPOST":"false"
}
res = s.post(res.url, data=payload)
res_html = BeautifulSoup(res.text, "html.parser")

days += res_html.css.select("#calendar .dates .days>li")

shifts = []
now = datetime.now()
for day in days:
    date = day.find("div", {"class":"date"})
    if date:
        event_year = now.year
        event_month, event_day = date.get_text().split("/")[:2]
        event_month = int(event_month)
        event_day = int(event_day)
        if now.month == 12 and event_month == 1:
            event_year += 1
        hours = day.find("span", {"class":"hours"})
        if hours:
            start_time, end_time = hours.get_text().split(" - ")
            start_hour, start_min = convert24(start_time)
            end_hour, end_min = convert24(end_time)
            event_start = tz.localize(datetime(event_year, event_month, event_day, start_hour, start_min))
            event_end = tz.localize(datetime(event_year, event_month, event_day, end_hour, end_min))
            job_string = day.find(string=re.compile("Job:")).split(".")[1]
            store_string = day.find(string=re.compile("Store:"))[7:]

            event_data = {
                "title":"Work Safeway #" + store_string + ": " + job_string,
                "start":event_start,
                "end":event_end
            }
            logging.debug(event_data)
            shifts.append(event_data)

caldav_url = "http://localhost:5232/"
caldav_user = os.getenv("RADICALE_USER")
caldav_password = os.getenv("RADICALE_PASSWORD")

with caldav.DAVClient(
    url = caldav_url,
    username = caldav_user,
    password = caldav_password
) as client:
    principal = client.principal()
    try:
        calendar = principal.calendar(name="Work Schedule")
    except caldav.error.NotFoundError:
        calendar = principal.make_calendar(name="Work Schedule")
    last_sunday = this_sunday - timedelta(days=7)
    next_sunday = this_sunday + timedelta(days=7)
    fetched_events = calendar.search(
        start = last_sunday,
        end = next_sunday,
        event = True,
        expand = True
    )
    for event in fetched_events:
        event_data = {
            "title":str(event.icalendar_component.get("summary")),
            "start":event.icalendar_component.get("dtstart").dt,
            "end":event.icalendar_component.get("dtend").dt
        }
        if event_data in shifts:
            #Remove event from the list if already on the calendar
            shifts.remove(event_data)
        else:
            #If the calendar event isn't in the list the schedule has changed
            #since the last run. Remove the orphaned event
            event.delete()

    for shift in shifts:
        calendar.save_event(
            dtstart = shift["start"],
            dtend = shift["end"],
            summary = shift["title"]
        )
