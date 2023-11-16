import caldav
import os
from datetime import datetime
from datetime import timedelta
 
caldav_url = "http://localhost:5232/"
caldav_user = os.getenv("RADICALE_USER")
caldav_password = os.getenv("RADICALE_PASSWORD")

with caldav.DAVClient(
    url = caldav_url,
    username = caldav_user,
    password = caldav_password
) as client:
    principal = client.principal()
    calendar = principal.calendar(name="Work Schedule")
    this_sunday = datetime.now() + timedelta(days=(7-(datetime.now().weekday()+1)%7))
    last_sunday = this_sunday - timedelta(days=7)
    next_sunday = this_sunday + timedelta(days=7)
    calendar.save_event(
        dtstart=datetime(2023,11,16,8),
        dtend=datetime(2023,11,16,12),
        summary="Work: Produce Fresh Clerk"
    )
    fetched_events = calendar.search(
        start = last_sunday,
        end = next_sunday,
        event = True,
        expand = True
    )
    for event in fetched_events:
        print(event.data)
