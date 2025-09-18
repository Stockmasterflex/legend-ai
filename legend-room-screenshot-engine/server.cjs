const express = require('express');
const app = express();

app.get('/healthz', (_req, res) => {
  res.json({ ok: true, service: 'legend-shots' });
});

app.get('/screenshot', (req, res) => {
  const symbol = String(req.query.symbol || 'SPY').toUpperCase();
  // Dummy URL for now; your API consumes { chart_url }
  const url = `https://dummyimage.com/1200x750/131722/ffffff&text=${encodeURIComponent(symbol)}+Chart`;
  res.json({ chart_url: url });
});

const port = process.env.PORT || 3010;
app.listen(port, () => console.log(`legend-shots listening on :${port}`));
