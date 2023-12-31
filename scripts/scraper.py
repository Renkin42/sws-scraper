from bs4 import BeautifulSoup
import requests
import os
import re
from datetime import datetime
from datetime import date
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
        logging.info(f"Successfully authenticated with id {sw_id}.")
    elif res.url == base_url + "AuthN/SwyLogInError.aspx":
        raise Exception(f"Failed to authenticate with id {sw_id}. Please ensure that credentials are up to date.")
    else:
        raise Exception("Unknown response URL: " + res.url)
    res_html = BeautifulSoup(res.text, "html.parser")
    days = res_html.css.select("#calendar .dates .days>li")

    viewstate = res_html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
    viewstategen = res_html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]
    this_sunday = date.today()
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
                if int(date_string.split("/")[0]) == 1 and now.month == 12:
                    date_string += "/" + str(now.year+1)
                elif int(date_string.split("/")[0]) == 12 and now.month == 1:
                    date_string += "/" + str(now.year-1)
                else:
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
                    "title":f"Work Safeway #{store_string}: {job_string}",
                    "start":event_start,
                    "end":event_end
                }
                logging.debug("Parsed event from schedule")
                logging.debug(event_data)
                shifts.append(event_data)

    logging.info(f"Parsed {len(shifts)} events from schedule")
    caldav_url = os.getenv("CALDAV_URL")
    caldav_user = os.getenv("CALDAV_USER")
    caldav_password = os.getenv("CALDAV_PASSWORD")

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

        duplicate = 0
        orphan = 0

        for event in fetched_events:
            event_data = {
                "title":str(event.icalendar_component.get("summary")),
                "start":event.icalendar_component.get("dtstart").dt,
                "end":event.icalendar_component.get("dtend").dt
            }
            logging.debug("Found event on calendar:")
            logging.debug(event_data)
            if event_data in shifts:
                #Remove event from the list if already on the calendar
                duplicate += 1
                logging.debug("Duplicate event found. Removing from list")
                shifts.remove(event_data)
            else:
                #If the calendar event isn't in the list the schedule has changed
                #since the last run. Remove the orphaned event
                orphan += 1
                logging.debug("Event not found in schedule. Assuming orphaned and deleting")
                event.delete()

        logging.info(f"{orphan} Orphaned events detected and deleted from calendar")
        logging.info(f"{duplicate} Duplicate events removed from list. Adding {len(shifts)} new events to calendar")
        for shift in shifts:
            calendar.save_event(
                dtstart = shift["start"],
                dtend = shift["end"],
                summary = shift["title"]
            )
except Exception as e:
    logging.error(e)
