# Outlook CalDAV Sync

[![The latest version of this tool can be found on PyPI.](https://img.shields.io/pypi/v/outlook-caldav-sync.svg)](https://pypi.org/project/outlook-caldav-sync/)
[![Information on what versions of Python this tool supports can be found on PyPI.](https://img.shields.io/pypi/pyversions/outlook-caldav-sync.svg)](https://pypi.org/project/outlook-caldav-sync/)

A Python tool to sync calendar events from an **Outlook JSON export** to a **CalDAV server** (e.g. Nextcloud Calendar, Radicale, Baikal).

## Overview

Outlook does not speak CalDAV natively. If you need your Outlook calendar available in a CalDAV-based application — whether for privacy, interoperability, or self-hosting reasons — the usual path involves manual exports or fragile third-party connectors.

This tool bridges that gap: it reads the JSON format that Microsoft's Power Automate (or a custom script) can export from an Outlook calendar and pushes the events to any CalDAV-compatible server. Only events that have actually changed are uploaded, keeping the sync efficient. Events that have disappeared from Outlook can optionally be removed from the CalDAV calendar as well.

## Features

- Sync Outlook JSON calendar exports to any CalDAV server
- Skip unchanged events using SHA-256 hash comparison — only changed events are uploaded
- Configurable time window: how many days into the past and future to sync
- **Filter events** by Outlook category or subject regex — excluded events are also removed from the remote calendar
- **Anonymize attendee e-mail addresses** (replace domain with `@invalid.invalid`)
- Mark all synced events as `CONFIDENTIAL` (private) on the CalDAV side
- Dry-run mode: preview what would happen without making any changes
- Force-update mode: re-upload all events even if they appear unchanged
- Reset remote: wipe all events from the CalDAV calendar before a fresh sync
- Optional log file in addition to stdout

## Install

Requires at least **Python 3.12**.

```bash
pip install outlook-caldav-sync
```

The command `outlook-caldav-sync` is then available. Run `outlook-caldav-sync --help` for a full list of options.

For development installs, use [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run outlook-caldav-sync --help
```

## Outlook JSON export

The tool expects a JSON file containing an array of calendar event objects in the format that **Microsoft Power Automate** produces when reading from the Outlook calendar connector. Each event object should contain at least the following fields:

| Field               | Description                                             |
| ------------------- | ------------------------------------------------------- |
| `iCalUId`           | Unique identifier of the event                          |
| `subject`           | Event title                                             |
| `startWithTimeZone` | ISO 8601 start datetime with timezone                   |
| `endWithTimeZone`   | ISO 8601 end datetime with timezone                     |
| `location`          | (optional) Location string                              |
| `organizer`         | (optional) Semicolon-separated organizer email(s)       |
| `requiredAttendees` | (optional) Semicolon-separated required attendee emails |
| `optionalAttendees` | (optional) Semicolon-separated optional attendee emails |
| `categories`        | (optional) List of Outlook category strings             |

## Configuration

Configuration is provided as a JSON file passed via `--config`. Example
(`config.json`):

```json
{
  dav_url: "https://nextcloud.example.com/remote.php/dav/",
  dav_calendar: "my-calendar-id",
  dav_username: "myuser",
  dav_password: "secret",
  dav_past_days: 3,
  dav_future_days: 400,
  log_file: "/var/log/outlook-caldav-sync.log",
  anonymize_email: true,
  private: false,
  delete_missing: true,
  nosync_categories: ["Reminder/Blocker"],
  nosync_subject_regex: ["^Declined:"]
}
```

| Key                    | Required | Default  | Description                                               |
| ---------------------- | -------- | -------- | --------------------------------------------------------- |
| `dav_url`              | yes      | —        | Base URL of the CalDAV server                             |
| `dav_calendar`         | yes      | —        | Calendar ID or name on the server                         |
| `dav_username`         | yes      | —        | CalDAV username                                           |
| `dav_password`         | yes      | —        | CalDAV password                                           |
| `dav_past_days`        | no       | `3`      | Days into the past to include in the sync window          |
| `dav_future_days`      | no       | `365`    | Days into the future to include in the sync window        |
| `log_file`             | no       | _(none)_ | Path to an optional log file (appended to)                |
| `anonymize_email`      | no       | `false`  | Replace attendee email domains with `@invalid.invalid`    |
| `private`              | no       | `false`  | Mark all synced events as `CONFIDENTIAL`                  |
| `delete_missing`       | no       | `true`   | Delete CalDAV events absent from the Outlook JSON         |
| `nosync_categories`    | no       | `[]`     | Outlook categories whose events are skipped and removed   |
| `nosync_subject_regex` | no       | `[]`     | Regex patterns; matching subjects are skipped and removed |

## Usage

```
outlook-caldav-sync -c config.json -i calendar-export.json
```

Full list of CLI options:

| Flag                     | Description                                                |
| ------------------------ | ---------------------------------------------------------- |
| `-c`, `--config`         | Path to the JSON configuration file (**required**)         |
| `-i`, `--calendar-input` | Path to the Outlook JSON export file (**required**)        |
| `-f`, `--force`          | Re-upload all events even if they appear unchanged         |
| `--dry`                  | Dry-run mode — no changes are written to the CalDAV server |
| `--reset-remote`         | Interactively delete **all** events in the remote calendar |
| `-vv`, `--debug`         | Enable DEBUG-level logging                                 |

## Filtering / no-sync

Events can be excluded from syncing in two ways:

- **By category**: add Outlook category names to `nosync_categories`. Events with those categories are skipped during upload _and_ removed from the remote if they exist there.
- **By subject regex**: add regular expressions to `nosync_subject_regex`. Events whose subject matches any pattern are treated the same way.

This is useful for blocking personal reminders, declined meetings, or any category you do not want mirrored to your CalDAV calendar.

## Logging

The tool logs to stdout by default. Set `log_file` in the config to additionally write to a file (append mode). Use `-vv` / `--debug` to enable verbose DEBUG output.

## Contribute and Development

Contributions are welcome! The development is easiest with [uv](https://github.com/astral-sh/uv): `uv sync` installs all dependencies and `uv run outlook-caldav-sync` runs the tool directly.

Run the test suite with `uv run pytest`, linting with `uv run ruff check`, and type checking with `uv run ty check`.

## License

Apache-2.0, Copyright Max Mehl. See [LICENSE](LICENSE) for details.
