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


def get_short_info_from_event_dict(
    event: dict[str, str], title_key: str = "subject", start_key: str = "start"
) -> tuple[str, str]:
    """Extract short info from a JSON event.

    Args:
        outlook_event (dict): Event data from Outlook JSON export.
        title_key (str): Key for the event title. Default is "subject".
        start_key (str): Key for the event start time. Default is "start".

    Returns:
        tuple: Tuple containing UID and dictionars (summary + start time).
    """
    uid = event.get("iCalUId", "")
    subject = event.get(title_key, "")
    start_time = event.get(start_key, "")
    description = f"{subject} ({start_time})"
    return uid, description


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


def caldav_event_to_dict(event: Event) -> dict[str, str]:
    """Converts most important elements of a VEVENT to a plain dictionary with string values."""
    return {
        "SUMMARY": str(event.get("SUMMARY")),
        "DTSTART": str(event.get("DTSTART").dt),
        "DTEND": str(event.get("DTEND").dt),
        "DTSTAMP": str(event.get("DTSTAMP").dt),
        "UID": str(event.get("UID")),
        "LOCATION": str(event.get("LOCATION")),
    }


def delete_missing_events(
    calendar: CalDAVCalendar,
    outlook_entries: list[dict[str, str]],
    delete_enabled: bool = True,
) -> int:
    """Delete CalDAV events that are not in Outlook JSON but within the JSON date range.

    Args:
        calendar (CalDAVCalendar): CalDAV calendar object.
        outlook_entries (list): List of Outlook event dictionaries.
        delete_enabled (bool): Whether deletion is enabled.

    Returns:
        int: Number of deleted events.
    """
    if not delete_enabled:
        logging.info("Deletion of missing events is disabled by config.")
        return 0

    if not outlook_entries:
        logging.warning("No Outlook entries loaded; skipping deletion check.")
        return 0

    # Determine JSON event date range
    json_start_times = [
        datetime.fromisoformat(e.get("startWithTimeZone", "")).astimezone(timezone.utc)
        for e in outlook_entries
        if "startWithTimeZone" in e
    ]
    json_start_min = min(json_start_times)
    json_start_max = max(json_start_times)

    # Collect UIDs from Outlook
    json_uids = {e.get("iCalUId", "") for e in outlook_entries if "iCalUId" in e}

    # Find CalDAV events in the same time window
    remote_events: list[CalDAVEvent] = calendar.search(  # type: ignore
        comp_class=CalDAVEvent, start=json_start_min, end=json_start_max  # type: ignore
    )

    deleted = 0
    for e in remote_events:
        try:
            ical: dict[str, str] = caldav_event_to_dict(e.icalendar_component)
        except Exception as err:  # pylint: disable=broad-exception-caught
            logging.warning("Skipping broken event %s: %s", e, err)
            continue

        uid, description = get_short_info_from_event_dict(
            event=ical, title_key="SUMMARY", start_key="DTSTART"
        )

        try:
            if uid:
                if uid not in json_uids:
                    e.delete()
                    logging.info("Deleted stale event: %s (UID: %s)", description, uid)
                    deleted += 1
        except Exception as err:  # pylint: disable=broad-exception-caught
            logging.warning("Failed to delete event %s (UID: %s): %s", description, uid, err)

    logging.debug("Deletion pass complete. Deleted %d events.", deleted)

    return deleted


def sync_events(config: dict, calendar: CalDAVCalendar, existing_hashes: dict[str, str]) -> None:
    """Sync Outlook JSON events to the CalDAV server.

    Args:
        config (dict): Configuration dictionary.
        calendar (Calendar): CalDAV calendar object.
        existing_hashes (dict): Existing event hashes.
    """
    created, updated, skipped, deleted = 0, 0, 0, 0

    # Load Outlook JSON data
    with open(config.get("outlook_calendar_file", None), "r", encoding="utf-8") as f:
        outlook_entries: list[dict[str, str]] = json.load(f)
        logging.info("Processing %d events from Outlook JSON", len(outlook_entries))

    for item in outlook_entries:
        uid, description = get_short_info_from_event_dict(item)
        if not uid:
            logging.warning("Skipping event without UID: %s", item)
            continue

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

    # Optional deletion step
    deleted = delete_missing_events(calendar, outlook_entries, config.get("delete_missing", True))

    logging.info(
        "Done. Created: %d, Updated: %d, Skipped: %d, Deleted: %d",
        created,
        updated,
        skipped,
        deleted,
    )


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
