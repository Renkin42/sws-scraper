from bs4 import BeautifulSoup
import requests
URL = "http://testphp.vulnweb.com/userinfo.php"

payload = {
    "uname":"test",
    "pass":"test"
}
s = requests.session()
response = s.post(URL, data=payload)
print(response.status_code)

soup = BeautifulSoup(response.content, "html.parser")
protected_content = soup.find(attrs={"id":"pageName"}).text
print(protected_content)
