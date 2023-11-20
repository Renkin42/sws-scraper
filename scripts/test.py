import caldav
import os
from datetime import datetime
from datetime import timedelta
import pytz

caldav_url = "http://localhost:5232"
caldav_user = os.getenv("RADICALE_USER")
caldav_password = os.getenv("RADICALE_PASSWORD")
if os.getenv("TZ"):
    tz = pytz.timezone(os.getenv("TZ"))
else:
    tz = pytz.utc

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
    this_sunday = datetime.now() + timedelta(days=(7-(datetime.now().weekday()+1)%7))
    last_sunday = this_sunday - timedelta(days=7)
    next_sunday = this_sunday + timedelta(days=7)
    calendar.save_event(
        dtstart=tz.localize(datetime(2023,11,20,8,0)),
        dtend=tz.localize(datetime(2023,11,20,12,0)),
        summary="Work: Produce Fresh Clerk"
    )
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
        print(event_data)
        shifts = [ {
            "title":"Work: Produce Fresh Clerk",
            "start":tz.localize(datetime(2023,11,20,8,0)),
            "end":tz.localize(datetime(2023,11,20,12,0))
        } ]
        print(shifts)
        if event_data in shifts:
            print("Event in list")
        else:
            print("Event not in list")
