#!/usr/bin/env node
// Upserts the scenarios produced by orb_vwap_short_trail.py (backtest/results.json)
// into the `strategies` table read by server.js / templates.js.
//
// Usage:
//   DATABASE_URL=postgres://... node backtest/seed_strategies.js [path/to/results.json]
//
// Requires a unique constraint on strategies.slug for the upsert (ON CONFLICT) to work:
//   ALTER TABLE strategies ADD CONSTRAINT strategies_slug_key UNIQUE (slug);

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

const resultsPath = process.argv[2] || path.join(__dirname, 'results.json');
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error('DATABASE_URL is not set.');
  process.exit(1);
}

const rows = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));

const pool = new Pool({
  connectionString,
  ssl: connectionString.includes('render.com') ? { rejectUnauthorized: false } : false,
});

async function main() {
  for (const r of rows) {
    await pool.query(
      `INSERT INTO strategies
         (slug, name, category, description, net_pnl, win_rate, trades, trades_reaching_breakeven, avg_win, avg_loss, rules, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
       ON CONFLICT (slug) DO UPDATE SET
         name = EXCLUDED.name,
         category = EXCLUDED.category,
         description = EXCLUDED.description,
         net_pnl = EXCLUDED.net_pnl,
         win_rate = EXCLUDED.win_rate,
         trades = EXCLUDED.trades,
         trades_reaching_breakeven = EXCLUDED.trades_reaching_breakeven,
         avg_win = EXCLUDED.avg_win,
         avg_loss = EXCLUDED.avg_loss,
         rules = EXCLUDED.rules`,
      [
        r.slug,
        r.name,
        r.category,
        r.description,
        r.net_pnl,
        r.win_rate,
        r.trades,
        r.trades_reaching_breakeven,
        r.avg_win,
        r.avg_loss,
        JSON.stringify(r.rules),
      ]
    );
    console.log(`Upserted: ${r.slug}`);
  }
  await pool.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
