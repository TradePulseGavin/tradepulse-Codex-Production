# Internal Server Error Fix

This stable build changes the homepage and API routes so the dashboard still opens even if one data provider fails.

## Use this build

1. Extract this ZIP.
2. Open the extracted folder.
3. If you see `.venv`, delete it only if the starter errors during install.
4. Double-click `start_windows`.
5. Leave the black window open.
6. Open Chrome to `http://127.0.0.1:8000`.

## Quick checks

- `http://127.0.0.1:8000/health` should show server status.
- `http://127.0.0.1:8000/api/scan?symbols=SPY,QQQ` should show JSON.
- `http://127.0.0.1:8000/api/news?symbols=SPY,QQQ` should show JSON.

If the dashboard opens but data says provider error, the app is running; the live data/news source needs internet/API keys or fewer symbols.
