from bs4 import BeautifulSoup
import requests
import os
import re
from datetime import datetime
from datetime import timedelta
import pytz
import caldav
import logging

base_url = "https://myschedule.safeway.com/ESS/"
login_url = base_url + "AuthN/Swylogin.aspx?ReturnUrl=%2fESS%2f"
sw_id = os.getenv("SW_ID")
sw_pass = os.getenv("SW_PASS")
tz = pytz.timezone(os.getenv("TZ", "UTC"))
loglevel = os.getenv("LOGLEVEL", "WARNING").upper()
logging.basicConfig(
    level = getattr(logging, loglevel),
    format = "[%(asctime)s][%(levelname)s]%(message)s",
    datefmt = "%-m/%-d/%y %-I:%M:%S%p"
)

try:
    with requests.session() as s:
        req = s.get(login_url, timeout=30)
        req.raise_for_status()
        html = BeautifulSoup(req.text, "html.parser")
        viewstate = html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
        viewstategen = html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]

    payload = {
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstategen,
        "EmpID": sw_id,
        "Password": sw_pass,
        "btnLogin":"Login"
    }

    res = s.post(login_url, data=payload, timeout=30)
    res.raise_for_status()
    if res.url == base_url + "Schedule.aspx":
        logging.info("Successfully authenticated with id " + sw_id)
    elif res.url == base_url + "/AuthN/SwyLoginError.aspx":
        raise Exception("Failed to authenticate with id " + sw_id + ". Please ensure that credentials are up to date.")
    else:
        raise Exception("Unknown response URL: " + res.url)
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
    res = s.post(res.url, data=payload, timeout=30)
    res.raise_for_status()
    res_html = BeautifulSoup(res.text, "html.parser")

    days += res_html.css.select("#calendar .dates .days>li")

    shifts = []
    now = datetime.now()
    for day in days:
        date = day.find("div", {"class":"date"})
        if date:
            date_string = date.get_text()
            if date_string.count("/") == 1:
                date_string += "/" + str(now.year)
            hours = day.find("span", {"class":"hours"})
            if hours:
                start_time, end_time = hours.get_text().upper().split(" - ")
                start_time += "M " + date_string
                end_time += "M " + date_string
                event_start = tz.localize(datetime.strptime(start_time, "%I:%M%p %m/%d/%Y"))
                event_end = tz.localize(datetime.strptime(end_time, "%I:%M%p %m/%d/%Y"))
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
except Exception as e:
    logging.error(e)
