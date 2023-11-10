from bs4 import BeautifulSoup
import requests
import os
from datetime import datetime
from datetime import timedelta

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
now = datetime.now()
for day in days:
    date = day.find("div", {"class":"date"})
    if date:
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

viewstate = res_html.find("input", {"name":"__VIEWSTATE"}).attrs["value"]
viewstategen = res_html.find("input", {"name":"__VIEWSTATEGENERATOR"}).attrs["value"]
offset = 7 - (now.weekday() + 1) % 7
now += timedelta(days = offset)
print(now.strftime("%m/%d/%Y"))
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
    "ctl00$masterPlaceHolder$txtWeekPeriodDate":now.strftime("%m/%d/%Y"),
    "__EVENTTARGET":"ctl00$masterPlaceHolder$txtWeekPeriodDate",
    "__EVENTARGUMENT":"",
    "__LASTFOCUS":"",
    "__VIEWSTATE":viewstate,
    "__VIEWSTATEGENERATOR":viewstategen,
    "ActiveTab":"ctl00_hdnActiveTab",
    "__AjaxControlToolkitCalendarCssLoaded":"",
    "__ASYNCPOST":"true"
}
res = s.post(res.url, data=payload)
res_html = BeautifulSoup(res.text, "html.parser")

print(res.text)

