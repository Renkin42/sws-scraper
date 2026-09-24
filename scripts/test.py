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
from schedule import every, repeat, run_pending
import time

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

@repeat(every(2).hours)
def scrape():
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
            workdate = day.find("div", {"class":"date"})
            if workdate:
                date_string = workdate.get_text()
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
    except Exception as e:
        logging.error(e)

#run on container start
scrape()
