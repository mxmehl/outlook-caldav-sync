"""Sync Outlook calendar with CalDAV server using ICS export and JSON import."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from caldav import Calendar as CalDAVCalendar
from caldav import DAVClient
from caldav import Event as CalDAVEvent
from icalendar import Calendar, Event


def hash_event(event: Event) -> str:
    """Generate a SHA256 hash of an event's relevant parts.

    Args:
        event (Event): iCalendar event.

    Returns:
        str: Hex digest of the event hash.
    """
    keys = ["dtstart", "dtend"]
    content = "|".join(str(event.get(k)) for k in keys)
    hashsum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logging.debug("Hash of event %s is %s", event.get("summary"), hashsum)
    return hashsum


def parse_ics_events(ics_data: str) -> dict:
    """Parse .ics content and return a UID-to-event dictionary.

    Args:
        ics_data (str): Raw .ics content.

    Returns:
        dict: Mapping of UID to iCalendar events.
    """
    parsed = Calendar.from_ical(ics_data)
    uid_map = {}
    for component in parsed.walk():
        if component.name == "VEVENT" and component.get("uid"):
            uid_map[component.get("uid")] = component
    return uid_map


def create_icalendar_event(json_event: dict[str, str]) -> Event:
    """Convert a JSON calendar entry to an iCalendar VEVENT.

    Args:
        json_event (dict): Event data from Outlook JSON export.

    Returns:
        Event: Constructed iCalendar event.
    """
    event = Event()
    event.add("uid", json_event["iCalUId"])
    event.add("summary", json_event["subject"])
    event.add(
        "dtstart", datetime.fromisoformat(json_event["startWithTimeZone"]).astimezone(timezone.utc)
    )
    event.add(
        "dtend", datetime.fromisoformat(json_event["endWithTimeZone"]).astimezone(timezone.utc)
    )
    event.add("location", json_event.get("location", ""))

    return event


def connect_to_caldav(config: dict) -> CalDAVCalendar:
    """Connect to the CalDAV server and return the calendar object.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        caldav.objects.Calendar: CalDAV calendar object.
    """
    client = DAVClient(
        url=config.get("dav_url", ""),
        username=config.get("dav_username", ""),
        password=config.get("dav_password", ""),
    )
    principal = client.principal()
    return principal.calendar(cal_id=config.get("dav_calendar", ""))


def get_existing_event_hashes(
    calendar: CalDAVCalendar, past: datetime, future: datetime
) -> dict[str, str]:
    """Fetch and hash existing remote events.

    Args:
        calendar (Calendar): CalDAV calendar object.
        past (datetime): Start of time window.
        future (datetime): End of time window.

    Returns:
        dict: Mapping of UID to hash for existing events.
    """
    logging.info("Fetching events from CalDAV server...")
    remote_events = calendar.search(comp_class=CalDAVEvent, start=past, end=future)  # type: ignore
    hashes = {}

    for e in remote_events:
        try:
            ical = e.icalendar_component
            if ical.name == "VEVENT" and ical.get("UID"):
                uid = str(ical.get("UID"))
                hashes[uid] = hash_event(ical)
        except Exception as err:  # pylint: disable=broad-exception-caught
            logging.warning("Skipping broken event: %s", err)

    logging.info("Found %d existing remote events", len(hashes))
    return hashes


def sync_events(config: dict, calendar: CalDAVCalendar, existing_hashes: dict[str, str]) -> None:
    """Sync Outlook JSON events to the CalDAV server.

    Args:
        config (dict): Configuration dictionary.
        calendar (Calendar): CalDAV calendar object.
        existing_hashes (dict): Existing event hashes.
    """
    with open(config.get("outlook_calendar_file", None), "r", encoding="utf-8") as f:
        outlook_entries: list[dict[str, str]] = json.load(f)

    created, updated, skipped = 0, 0, 0

    for item in outlook_entries:
        uid = item.get("iCalUId", None)
        if not uid:
            logging.warning("Skipping event without UID: %s", item)
            continue

        description = f"{item.get('subject')} ({item.get('start')})"
        new_event: Event = create_icalendar_event(item)
        new_hash = hash_event(new_event)

        if uid in existing_hashes and existing_hashes[uid] == new_hash:
            skipped += 1
            continue

        try:
            calendar.add_event(new_event.to_ical().decode("utf-8"))
            if uid in existing_hashes:
                logging.info("Updated event: %s", description)
                updated += 1
            else:
                logging.info("Created event: %s", description)
                created += 1
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to upload event %s (UID: %s): %s", description, uid, e)

    logging.info("Done. Created: %d, Updated: %d, Skipped: %d", created, updated, skipped)


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    # Load configuration
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Time window
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=config.get("dav_past_days", 3))
    future = now + timedelta(days=config.get("dav_future_days", 730))

    calendar = connect_to_caldav(config)
    existing_hashes = get_existing_event_hashes(calendar, past, future)
    sync_events(config, calendar, existing_hashes)


if __name__ == "__main__":
    main()
