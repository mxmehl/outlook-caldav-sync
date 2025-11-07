"""Sync Outlook calendar with CalDAV server using ICS export and JSON import."""

import argparse
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone

from caldav import Calendar as CalDAVCalendar
from caldav import DAVClient
from caldav import Event as CalDAVEvent
from icalendar import Calendar, Event


def configure_logger(log_file: str = "", verbose: bool = False) -> logging.Logger:
    """Set logging options"""
    log_handlers = [logging.StreamHandler()]
    if log_file:
        log_handlers.append(
            logging.FileHandler(log_file, mode="a", encoding="utf-8")  # type: ignore
        )

    log = logging.getLogger()
    logging.basicConfig(
        encoding="utf-8",
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=log_handlers,
    )
    if verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    return log


def hash_event(event: Event) -> str:
    """Generate a SHA256 hash of an event's relevant parts.

    Args:
        event (Event): iCalendar event.

    Returns:
        str: Hex digest of the event hash.
    """
    keys = ["summary", "dtstart", "dtend"]
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
    uid = event.get("iCalUId") or event.get("UID", "")
    subject = event.get(title_key, "")
    start_time = event.get(start_key, "")
    description = f"{subject} ({start_time})"
    if not uid:
        logging.warning("Event without UID: %s", description)
        return "", description
    return uid, description


def add_attendees_to_event(event: Event, attendees: str, role: str, anonymize_email: bool) -> None:
    """Add attendees to an iCalendar event.

    Args:
        event (Event): iCalendar event.
        attendees (str): Semicolon-separated list of attendee email addresses.
        role (str): Role of the attendees ("ORGANIZER", "REQ-PARTICIPANT", "OPT-PARTICIPANT").
        anonymize_email (bool): Whether to convert email addresses to a name, e.g.
            "john.doe@example.com" to "john.doe@invalid.invalid"
    """
    for attendee in attendees.split(";"):
        if attendee := attendee.strip():
            parameters = {}
            # If the attendee is an email address, format it correctly
            if "@" in attendee:
                if anonymize_email:
                    # Replace domain part for name-only format
                    attendee_name = attendee.split("@")[0]
                    parameters["CN"] = attendee_name
                    attendee = attendee + "@invalid.invalid"
                else:
                    # Ensure email format for iCalendar
                    attendee = f"mailto:{attendee}"
            # Add attendee to the event. If the role is ORGANIZER, use the organizer field;
            # otherwise, use attendee
            if role == "ORGANIZER":
                event.add("organizer", attendee, parameters=parameters)
            else:
                parameters["ROLE"] = role
                event.add(
                    name="attendee",
                    value=attendee,
                    parameters=parameters,
                )


def create_icalendar_event(
    json_event: dict[str, str], anonymize_email: bool, private: bool
) -> Event:
    """Convert a JSON calendar entry to an iCalendar VEVENT.

    Args:
        json_event (dict): Event data from Outlook JSON export.
        anonymize_email (bool): Whether to anonymize email addresses.
        private (bool): Whether the calendar event is private.

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

    # Add organizer and attendees
    add_attendees_to_event(
        event,
        json_event.get("organizer", ""),
        "ORGANIZER",
        anonymize_email=anonymize_email,
    )
    add_attendees_to_event(
        event,
        json_event.get("requiredAttendees", ""),
        "REQ-PARTICIPANT",
        anonymize_email=anonymize_email,
    )
    add_attendees_to_event(
        event,
        json_event.get("optionalAttendees", ""),
        "OPT-PARTICIPANT",
        anonymize_email=anonymize_email,
    )

    # Set classification based on private setting
    if private:
        event.add("class", "CONFIDENTIAL")

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
    dry: bool = False,
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
                    if not dry:
                        e.delete()
                    logging.info("Deleted stale event: %s (UID: %s)", description, uid)
                    deleted += 1
        except Exception as err:  # pylint: disable=broad-exception-caught
            logging.warning("Failed to delete event %s (UID: %s): %s", description, uid, err)

    logging.debug("Deletion pass complete. Deleted %d events.", deleted)

    return deleted


def sync_events(  # pylint: disable=too-many-locals
    config: dict,
    calendar: CalDAVCalendar,
    existing_hashes: dict[str, str],
    dry: bool = False,
    force: bool = False,
) -> None:
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

        new_event: Event = create_icalendar_event(
            item,
            anonymize_email=config.get("anonymize_email", False),
            private=config.get("private", False),
        )
        new_hash = hash_event(new_event)

        if uid in existing_hashes and existing_hashes[uid] == new_hash and not force:
            logging.debug("Skipping unchanged event: %s", description)
            skipped += 1
            continue

        try:
            if not dry:
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
    deleted = delete_missing_events(
        calendar,
        outlook_entries,
        config.get("delete_missing", True),
        dry=dry,
    )

    logging.info(
        "Done. Created: %d, Updated: %d, Skipped: %d, Deleted: %d",
        created,
        updated,
        skipped,
        deleted,
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync Outlook JSON calendar to CalDAV")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to the configuration file (default: config.json)",
    )
    parser.add_argument(
        "-i",
        "--calendar-input",
        type=str,
        required=True,
        help="Path to the Outlook JSON calendar export file",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force update of remote events even if they seem to be equal",
    )
    parser.add_argument("-vv", "--debug", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("--dry", action="store_true", help="Dry run mode (no changes made)")
    args = parser.parse_args()

    # --------------------------------------------------
    # HANDLE CONFIGURATION AND ARGUMENTS
    # --------------------------------------------------
    # Load configuration file
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Update config with command line arguments
    config["outlook_calendar_file"] = args.calendar_input

    # Configure logging (file + console)
    configure_logger(config.get("log_file", ""), args.debug)

    # Set Time window
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=config.get("dav_past_days", 3))
    future = now + timedelta(days=config.get("dav_future_days", 365))

    # --------------------------------------------------
    # SYNC CALENDAR
    # --------------------------------------------------
    calendar = connect_to_caldav(config)
    existing_hashes = get_existing_event_hashes(calendar, past, future)
    sync_events(config, calendar, existing_hashes, dry=args.dry, force=args.force)


if __name__ == "__main__":
    main()
