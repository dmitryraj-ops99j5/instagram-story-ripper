# instagram-story-ripper

A simple command-line tool to download active Instagram stories of specified users. It uses your browser's session cookie to authenticate directly with the Instagram API, avoiding heavy browser automation or fragile third-party scrapers.

I wrote this because I wanted a fast, dependency-light way to archive stories from a few creators without setting up complex scrapers or risking my account with sketchy wrappers.

## Installation

Clone the repository and install the single dependency:

```cmd
pip install -r requirements.txt
```

## Usage

First, you need your Instagram `sessionid` cookie. You can find this in your browser's Developer Tools (under Application -> Cookies -> instagram.com after logging in).

Run the script with your session ID and the target usernames:

```cmd
python ripper.py --session-id "YOUR_SESSION_ID" username1 username2
```

Alternatively, save the session ID to a file (e.g., `session.txt`) so you don't leak it in your shell history:

```cmd
python ripper.py --session-file session.txt username1
```

Files are downloaded to a `./downloads` directory by default, grouped by username.

## Options

* `-o`, `--output`: Custom directory to save downloads (default: `./downloads`).
* `-d`, `--delay`: Seconds to wait between user requests to prevent rate limits (default: 3).
* `--session-id`: Raw `sessionid` cookie value.
* `--session-file`: Path to a text file containing the `sessionid` value.

<!-- checked: 2026-09-17 -->
