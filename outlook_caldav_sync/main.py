"""Sync Outlook calendar with CalDAV server using ICS export and JSON import."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from caldav import DAVClient
from caldav import Event as CalDAVEvent
from icalendar import Calendar, Event


def hash_event(event: Event) -> str:
    """Hash the content-relevant parts of an event for comparison."""
    keys = ["dtstart", "dtend"]
    content = "|".join(str(event.get(k)) for k in keys)
    hashsum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logging.debug("Hash of event %s is %s", event.get("summary"), hashsum)
    return hashsum


def parse_ics_events(ics_data: str) -> dict:
    """Return a UID → event map from .ics content."""
    parsed = Calendar.from_ical(ics_data)
    uid_map = {}
    for component in parsed.walk():
        if component.name == "VEVENT" and component.get("uid"):
            uid_map[component.get("uid")] = component
    return uid_map


def create_icalendar_event(json_event) -> Event:
    """Convert JSON event to icalendar VEVENT"""
    event = Event()
    event.add("uid", json_event["iCalUId"])
    event.add("summary", json_event["subject"])
    event.add(
        "dtstart", datetime.fromisoformat(json_event["startWithTimeZone"]).astimezone(timezone.utc)
    )
    event.add(
        "dtend", datetime.fromisoformat(json_event["endWithTimeZone"]).astimezone(timezone.utc)
    )
    # event.add("description", json_event.get("body", ""))
    event.add("location", json_event.get("location", ""))
    # event.add("url", json_event.get("webLink", ""))
    return event


def main():
    """Main function to sync Outlook calendar with CalDAV server."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    # Load config
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Connect to CalDAV
    client = DAVClient(
        url=config["dav_url"], username=config["dav_username"], password=config["dav_password"]
    )
    principal = client.principal()
    calendar = principal.calendar(cal_id=config["dav_calendar"])

    # Define time window for fetching existing events
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=3)
    future = now + timedelta(days=730)  # max. 2 years

    logging.info("Fetching events from CalDAV server...")
    remote_events = calendar.search(comp_class=CalDAVEvent, start=past, end=future)

    existing_hashes = {}
    for e in remote_events:
        try:
            ical = e.icalendar_component
            if ical.name == "VEVENT" and ical.get("UID"):
                uid = str(ical.get("UID"))
                existing_hashes[uid] = hash_event(ical)
        except Exception as err:
            logging.warning("Skipping broken event: %s", err)

    logging.info("Found %d existing remote events", len(existing_hashes))

    # Load Outlook events from JSON
    with open(config["outlook_calendar_file"], "r", encoding="utf-8") as f:
        outlook_entries = json.load(f)

    created, updated, skipped = 0, 0, 0

    for item in outlook_entries:
        uid = item.get("iCalUId")
        description = f"{item.get('subject')} ({item.get('start')})"
        if not uid:
            continue

        new_event = create_icalendar_event(item)
        new_hash = hash_event(new_event)

        if uid in existing_hashes and existing_hashes[uid] == new_hash:
            skipped += 1
            continue

        try:
            calendar.add_event(new_event.to_ical())
            if uid in existing_hashes:
                logging.info("Updated event: %s", description)
                logging.debug("Updated Event UID: %s", uid)
                updated += 1
            else:
                logging.info("Created event: %s", description)
                logging.debug("Created Event UID: %s", uid)
                created += 1
        except Exception as e:
            logging.error("Failed to upload event %s (UID: %s): %s", description, uid, e)

    logging.info("Done. Created: %d, Updated: %d, Skipped: %d", created, updated, skipped)


if __name__ == "__main__":
    main()
