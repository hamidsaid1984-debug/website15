let autoRefreshInterval = null;

function updateMarketStatus() {
    fetch('/api/market-status')
        .then(r => r.json())
        .then(data => {
            const statusEl = document.getElementById('market-status');
            const timeEl = document.getElementById('market-time');
            
            statusEl.textContent = `🟢 ${data.text}`;
            statusEl.className = `market-badge market-${data.status}`;
            timeEl.textContent = `Current Time: ${data.time}`;
        });
}

function handleKeyPress(event) {
    if (event.key === 'Enter') loadTicker();
}

function loadTicker(ticker) {
    if (ticker) {
        document.getElementById('ticker-input').value = ticker;
    }
    
    ticker = document.getElementById('ticker-input').value.toUpperCase();
    if (!ticker) return;

    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const metrics = document.getElementById('metrics-section');
    const welcome = document.getElementById('welcome-section');

    loading.style.display = 'block';
    error.style.display = 'none';
    metrics.style.display = 'none';

    fetch(`/api/stock/${ticker}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);

            document.getElementById('current-price').textContent = `$${data.current_price.toFixed(2)}`;
            document.getElementById('day-change').textContent = `${data.day_change > 0 ? '+' : ''}${data.day_change.toFixed(2)}%`;
            document.getElementById('rsi-value').textContent = data.rsi.toFixed(1);
            document.getElementById('ema9').textContent = `$${data.ema9.toFixed(2)}`;
            document.getElementById('ema20').textContent = `$${data.ema20.toFixed(2)}`;
            document.getElementById('ema50').textContent = `$${data.ema50.toFixed(2)}`;
            document.getElementById('macd').textContent = data.macd.toFixed(4);
            document.getElementById('macd-signal').textContent = data.macd_signal.toFixed(4);
            document.getElementById('macd-hist').textContent = data.macd_hist.toFixed(4);

            const chart = data.chart_data;
            const trace1 = {
                x: chart.dates,
                close: chart.closes,
                high: chart.highs,
                low: chart.lows,
                open: chart.opens,
                type: 'candlestick',
                name: 'Price'
            };

            const trace2 = {
                x: chart.dates,
                y: chart.rsi,
                type: 'scatter',
                name: 'RSI',
                yaxis: 'y2'
            };

            const layout = {
                title: `${ticker} - 1 Day / 1 Minute`,
                yaxis: { title: 'Price' },
                yaxis2: { title: 'RSI', overlaying: 'y', side: 'right' },
                template: 'plotly_dark',
                hovermode: 'x unified',
                margin: { l: 60, r: 60, t: 60, b: 60 }
            };

            Plotly.newPlot('chart', [trace1, trace2], layout, { responsive: true });

            loading.style.display = 'none';
            welcome.style.display = 'none';
            metrics.style.display = 'block';
        })
        .catch(err => {
            error.textContent = err.message;
            error.style.display = 'block';
            loading.style.display = 'none';
        });
}

document.getElementById('auto-refresh').addEventListener('change', (e) => {
    if (e.target.checked) {
        autoRefreshInterval = setInterval(() => {
            loadTicker();
        }, 15000);
    } else {
        clearInterval(autoRefreshInterval);
    }
});

updateMarketStatus();
setInterval(updateMarketStatus, 60000);
