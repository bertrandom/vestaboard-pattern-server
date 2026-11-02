# vestaboard-pattern-server

Steps through the Vestaboard patterns in the patterns database one day at a time,
previews the current one on a Tronbyt, and sends it to the Vestaboard on demand.

## Endpoints

- `POST /next`, `POST /previous` — move the date cursor and show that pattern on the Tronbyt
- `GET /current` — current date cursor and pattern grid
- `POST /current/send` — flash "SENDING VESTA BOARD" on the Tronbyt and write the pattern to the Vestaboard

The date cursor is stored in `data/state.db`. Patterns are read from the database at
`patterns_db_path` (the `vestaboard-patterns` repo).

## Tronbyt

The preview uses the `vestaboard` app from `~/code/bert-tronbyt/apps/vestaboard`, which
draws the grid from `message_body` in its config. On every cursor move the server:

1. `PATCH`es installation `109` with the new `message_body`, so the app is current in normal rotation
2. calls `push_app` with `app_id: "vestaboard"` and the same config, so the device shows it immediately

Don't pass `installationID` to `push_app`: Tronbyt creates a separate "pushed" app for it and
re-sends that app's first cached image on later pushes instead of re-rendering.

The Tronbyt URL, installation ID and app ID are constants at the top of `main.py`. The
installation ID is the numeric one from the API (`GET /v0/devices/tidbyt/installations`),
not the `vestaboard-109` label the web UI shows.

## Setup

```
uv run init_db.py
sqlite3 data/state.db 'PRAGMA journal_mode=WAL;'
```

Config lives in `config/default.json5`, overridden by `config/prod.json5` (not committed) when
`ENV=prod`: `patterns_db_path`, `tronbyt_api_key`, and the Vestaboard local API key and URL.

## Deploy

`./deploy.sh` rsyncs to `web@nuke:/web/vestaboard-pattern-server/` and reloads the
`vestaboard-pattern-server` systemd unit (`system/vestaboard-pattern-server.service`).
