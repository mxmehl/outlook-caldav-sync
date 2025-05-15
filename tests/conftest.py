"""Configuration for pytest fixtures"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from icalendar import Event


@pytest.fixture(name="sample_json_event")
def fixture_sample_json_event():
    """Fixture for a sample JSON event."""
    return {
        "iCalUId": "event-1",
        "subject": "Test Event",
        "startWithTimeZone": "2025-05-20T09:00:00+00:00",
        "endWithTimeZone": "2025-05-20T10:00:00+00:00",
        "location": "Online",
    }


@pytest.fixture(name="sample_ical_event")
def fixture_sample_ical_event():
    """Sample iCalendar event"""
    event = Event()
    event.add("UID", "event-1")
    event.add("SUMMARY", "Old Event")
    event.add("DTSTART", datetime(2025, 5, 20, 9, 0, tzinfo=timezone.utc))
    event.add("DTEND", datetime(2025, 5, 20, 10, 0, tzinfo=timezone.utc))
    event.add("DTSTAMP", datetime.now(timezone.utc))
    event.add("LOCATION", "Old Location")
    return event


@pytest.fixture(name="caldav_event_mock")
def fixture_caldav_event_mock(sample_ical_event):
    """Mock for a CalDAV event"""
    event = MagicMock()
    event.icalendar_component = sample_ical_event
    return event
