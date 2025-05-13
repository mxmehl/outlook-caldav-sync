import json
import logging
from datetime import datetime
from sys import exit

import caldav
import pytz
from caldav import Event as CalDAVEvent
from icalendar import Calendar, Event


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    # Read configuration from config.json
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Connect to CalDAV server
    client = caldav.DAVClient(
        url=config["dav_url"],
        username=config["username"],
        password=config["password"],
    )
    principal = client.principal()
    calendar = principal.calendar(cal_id=config["calendar"])

    # Load JSON events
    with open("kalender.json", "r", encoding="utf-8") as f:
        entries = json.load(f)

    for item in entries:
        uid = item.get("iCalUId")
        if not uid:
            logging.warning("Skipping event without UID: %s", item.get("subject", ""))
            continue

        logging.info("Processing event: %s", item["subject"])
        start = datetime.fromisoformat(item["startWithTimeZone"]).astimezone(pytz.utc)
        end = datetime.fromisoformat(item["endWithTimeZone"]).astimezone(pytz.utc)

        # Build iCalendar event
        cal = Calendar()
        cal.add("prodid", "-//Outlook Export//")
        cal.add("version", "2.0")
        event = Event()
        event.add("uid", uid)
        event.add("summary", item["subject"])
        event.add("dtstart", start)
        event.add("dtend", end)
        event.add("description", item.get("body", ""))
        event.add("location", item.get("location", ""))
        event.add("url", item.get("webLink", ""))
        cal.add_component(event)

        # try:
        #     existing_event = calendar.object_by_uid(uid, comp_class=CalDAVEvent)
        #     logging.info("Updating existing event: %s", uid)
        #     existing_event.delete()
        # except:
        #     logging.info("Creating new event: %s", uid)

        # Upload new or updated event
        calendar.add_event(cal.to_ical())


if __name__ == "__main__":
    main()
