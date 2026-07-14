"""Unit tests for the main module of the Outlook CalDAV Sync application."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from outlook_caldav_sync.main import (
    create_icalendar_event,
    delete_missing_events,
    get_existing_event_hashes,
    hash_event,
    sync_events,
)


def test_create_event_from_json(sample_json_event) -> None:
    """Test creating an iCalendar event from a JSON event."""
    event = create_icalendar_event(sample_json_event, anonymize_email=False, private=False)
    assert str(event.get("SUMMARY")) == "Test Event"
    assert event.get("UID") == "event-1"


def test_hash_event_changes(sample_json_event) -> None:
    """Test that the hash changes when the event changes."""
    event1 = create_icalendar_event(sample_json_event, anonymize_email=False, private=False)
    hash1 = hash_event(event1)
    sample_json_event["subject"] = "Changed Event"
    event2 = create_icalendar_event(sample_json_event, anonymize_email=False, private=False)
    hash2 = hash_event(event2)
    assert hash1 != hash2


def test_get_existing_event_hashes(caldav_event_mock) -> None:
    """Test getting existing event hashes from a calendar."""
    calendar = MagicMock()
    calendar.search.return_value = [caldav_event_mock]
    now = datetime.now(UTC)
    result = get_existing_event_hashes(calendar, now - timedelta(days=1), now + timedelta(days=1))
    assert "event-1" in result
    assert isinstance(result["event-1"], str)


@patch("outlook_caldav_sync.main.delete_missing_events")
def test_sync_events_all_equal(_mock_delete, sample_json_event, caldav_event_mock) -> None:
    """Test syncing events when all hashes are equal."""
    calendar = MagicMock()
    calendar.search.return_value = [caldav_event_mock]
    existing_hashes = {
        "event-1": hash_event(
            create_icalendar_event(sample_json_event, anonymize_email=False, private=False)
        )
    }
    config = {"outlook_calendar_file": "test.json", "delete_missing": False}

    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            [sample_json_event]
        )
        with patch("json.load", return_value=[sample_json_event]):
            sync_events(config, calendar, existing_hashes)
            calendar.add_event.assert_not_called()


@patch("outlook_caldav_sync.main.delete_missing_events")
def test_sync_events_hash_mismatch(_mock_delete, sample_json_event, caldav_event_mock) -> None:
    """Test syncing events when hashes do not match."""
    calendar = MagicMock()
    calendar.search.return_value = [caldav_event_mock]
    wrong_hash = hash_event(
        create_icalendar_event(
            {**sample_json_event, "subject": "Different"}, anonymize_email=False, private=False
        )
    )
    existing_hashes = {"event-1": wrong_hash}
    config = {"outlook_calendar_file": "test.json", "delete_missing": False}

    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            [sample_json_event]
        )
        with patch("json.load", return_value=[sample_json_event]):
            sync_events(config, calendar, existing_hashes)
            calendar.add_event.assert_called_once()


@patch("outlook_caldav_sync.main.delete_missing_events")
def test_sync_events_missing_in_caldav(_mock_delete, sample_json_event) -> None:
    """Test syncing events when the event is missing in CalDAV."""
    calendar = MagicMock()
    calendar.search.return_value = []
    existing_hashes = {}
    config = {"outlook_calendar_file": "test.json", "delete_missing": False}

    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            [sample_json_event]
        )
        with patch("json.load", return_value=[sample_json_event]):
            sync_events(config, calendar, existing_hashes)
            calendar.add_event.assert_called_once()


def test_delete_missing_event(caldav_event_mock, sample_json_event) -> None:
    """Test deleting a missing event."""
    calendar = MagicMock()
    calendar.search.return_value = [caldav_event_mock]
    caldav_event_mock.delete = MagicMock()

    # Provide JSON event in a different UID so deletion is triggered
    sample_json_event["iCalUId"] = "nonexistent-in-caldav"

    result = delete_missing_events(calendar, [sample_json_event], delete_enabled=True)
    assert result == 1
    caldav_event_mock.delete.assert_called_once()


def test_no_deletion_when_disabled(caldav_event_mock) -> None:
    """Test that no deletion occurs when delete_enabled is False."""
    calendar = MagicMock()
    calendar.search.return_value = [caldav_event_mock]
    caldav_event_mock.delete = MagicMock()
    result = delete_missing_events(calendar, [], delete_enabled=False)
    assert result == 0
    caldav_event_mock.delete.assert_not_called()


@patch("outlook_caldav_sync.main.delete_missing_events")
def test_sync_events_nosync_showas(_mock_delete, sample_json_event) -> None:
    """Test that events with a nosync_showas value are skipped."""
    calendar = MagicMock()
    sample_json_event["showAs"] = "free"
    config = {
        "outlook_calendar_file": "test.json",
        "nosync_showas": ["free"],
        "delete_missing": False,
    }

    with patch("json.load", return_value=[sample_json_event]), patch("builtins.open", MagicMock()):
        sync_events(config, calendar, {})
        calendar.add_event.assert_not_called()
