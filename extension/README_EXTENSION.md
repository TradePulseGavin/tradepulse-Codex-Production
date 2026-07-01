# Trading Copilot Chrome Overlay

This overlay shows Trading Copilot prompts on trading/chart websites while the local server runs.

## Load it in Chrome / Edge

1. Open `chrome://extensions`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Choose this `extension` folder.
5. Start the local server from the main project folder:
   `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`
6. Open TradingView/Webull/etc. The overlay should appear in the bottom-right.

The overlay does not click buttons, submit orders, or touch your broker account. It only reads prompts from your own local server.
