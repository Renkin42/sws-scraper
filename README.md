Safeway Employee Work Schedule Scraper
======================================

This is just a simple docker container using python to scrape the [Safeway 
mySchedule portal](myschedule.safeway.com/ESS/AuthN/SwyLogin.aspx?ReturnURL=%2fESS).
It will use the bitwarden CLI to retrieve the current password so that the container
need not be updated every 2-3 months when the user is forced to change passwords.
The scraped schedule will then be presented as a CalDAV feed for import to the
users' calendar client of choice.

Progress
--------

- [x] Scraper proof of concept
- [x] Login to mySchedule
- [x] Scrape data from mySchedule
- [ ] Implement Bitwarden CLI
- [ ] Add CalDAV server 

Environment Variables
---------------------

- `SW_ID` : Employee ID Number
- `SW_PASS` : Employee Password
- `CALDAV_URL` : CalDAV Server URL
- `CALDAV_USER` : CalDAV Server Username
- `CALDAV_PASSWORD` : CalDAV Server Password
- `TZ` : Time zone used for events
