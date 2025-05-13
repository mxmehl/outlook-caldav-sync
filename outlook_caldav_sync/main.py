"""Sync Outlook calendar with CalDAV server using ICS export and JSON import."""

import hashlib
import json
import logging
from datetime import datetime

import pytz
import requests
from caldav import DAVClient
from icalendar import Calendar, Event

ICS_EXPORT_FILE = "remote_calendar.ics"
OUTLOOK_JSON_FILE = "kalender_full.json"


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
        "dtstart", datetime.fromisoformat(json_event["startWithTimeZone"]).astimezone(pytz.utc)
    )
    event.add("dtend", datetime.fromisoformat(json_event["endWithTimeZone"]).astimezone(pytz.utc))
    event.add("description", json_event.get("body", ""))
    event.add("location", json_event.get("location", ""))
    event.add("url", json_event.get("webLink", ""))
    return event


def main():
    """Main function to sync Outlook calendar with CalDAV server."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    # Load config
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Step 1: Download existing .ics calendar
    logging.info("Downloading ICS calendar...")
    auth = (config["username"], config["password"])
    ics_export_url = (
        f"{config["dav_url"]}/calendars/{config["username"]}/{config["calendar"]}/?export"
    )
    response = requests.get(url=ics_export_url, auth=auth, timeout=120)
    if not response.ok:
        logging.error("Failed to fetch ICS: %s", response.status_code)
        return
    ics_data = response.text
    existing_events = parse_ics_events(ics_data)
    existing_hashes = {uid: hash_event(evt) for uid, evt in existing_events.items()}
    logging.info("Found %d existing events in remote calendar.", len(existing_events))

    # Step 2: Connect to CalDAV for uploading changes
    client = DAVClient(
        url=config["dav_url"], username=config["username"], password=config["password"]
    )
    principal = client.principal()
    calendar = principal.calendar(cal_id=config["calendar"])

    # Step 3: Load Outlook-exported JSON
    with open(OUTLOOK_JSON_FILE, "r", encoding="utf-8") as f:
        outlook_entries = json.load(f)

    updated = 0
    skipped = 0
    created = 0

    # Step 4: Process each Outlook entry
    for item in outlook_entries:
        uid = item.get("iCalUId")
        if not uid:
            continue

        logging.info("Processing: %s", item["subject"])
        new_event = create_icalendar_event(item)
        new_hash = hash_event(new_event)

        if uid in existing_hashes and existing_hashes[uid] == new_hash:
            logging.debug("No changes for UID %s - skipping", uid)
            skipped += 1
            continue

        try:
            calendar.add_event(new_event.to_ical())
            if uid in existing_hashes:
                updated += 1
                logging.info("Updated event: %s", uid)
            else:
                created += 1
                logging.info("Created event: %s", uid)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Failed to add/update event %s: %s", uid, e)

    logging.info("Sync complete. Created: %d, Updated: %d, Skipped: %d", created, updated, skipped)


if __name__ == "__main__":
    main()
