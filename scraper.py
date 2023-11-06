from bs4 import BeautifulSoup
import requests
import os

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
print(res.url)
