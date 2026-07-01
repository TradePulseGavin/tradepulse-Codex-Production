(function () {
  const DEFAULT_SYMBOLS = "SPY,QQQ,AAPL,NVDA,TSLA";
  let symbols = localStorage.getItem("tradingCopilotSymbols") || inferSymbolsFromPage() || DEFAULT_SYMBOLS;

  function inferSymbolsFromPage() {
    const title = document.title || "";
    const upper = title.toUpperCase();
    const matches = upper.match(/\b[A-Z]{1,5}\b/g) || [];
    const common = matches.filter(s => !["THE", "AND", "USD", "BUY", "SELL", "WEBULL", "TRADINGVIEW", "ROBINHOOD"].includes(s));
    return common.slice(0, 3).join(",");
  }

  function createOverlay() {
    if (document.getElementById("trading-copilot-overlay")) return;
    const box = document.createElement("div");
    box.id = "trading-copilot-overlay";
    box.innerHTML = `
      <div class="tc-head">
        <div class="tc-title">Trading Copilot</div>
        <div class="tc-controls">
          <button id="tc-refresh" title="Refresh">↻</button>
          <button id="tc-toggle" title="Collapse">–</button>
        </div>
      </div>
      <div class="tc-body">
        <div id="tc-message" class="tc-message">Start the local server, then refresh.</div>
        <input id="tc-symbols" class="tc-symbols" value="${symbols}" title="Comma-separated tickers" />
        <div class="tc-muted">Prompt-only. Does not place trades. Dashboard: http://127.0.0.1:8000</div>
      </div>
    `;
    document.body.appendChild(box);
    document.getElementById("tc-refresh").addEventListener("click", refresh);
    document.getElementById("tc-toggle").addEventListener("click", () => {
      box.classList.toggle("tc-collapsed");
      document.getElementById("tc-toggle").textContent = box.classList.contains("tc-collapsed") ? "+" : "–";
    });
    document.getElementById("tc-symbols").addEventListener("change", (event) => {
      symbols = event.target.value || DEFAULT_SYMBOLS;
      localStorage.setItem("tradingCopilotSymbols", symbols);
      refresh();
    });
  }

  async function refresh() {
    const msg = document.getElementById("tc-message");
    if (!msg) return;
    msg.textContent = "Scanning...";
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/latest?symbols=${encodeURIComponent(symbols)}`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      msg.textContent = data.extension_message || "No prompt available.";
    } catch (err) {
      msg.textContent = "Local server not connected. Run: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000";
    }
  }

  createOverlay();
  refresh();
  setInterval(refresh, 60_000);
})();
