const express = require('express');
const { Pool } = require('pg');
const { hubPage, detailPage, notePage, layout } = require('./templates');

const app = express();
const PORT = process.env.PORT || 3000;

const connectionString = process.env.DATABASE_URL;
const pool = new Pool({
  connectionString,
  ssl: connectionString && connectionString.includes('render.com')
    ? { rejectUnauthorized: false }
    : false,
});

app.get('/', async (req, res) => {
  try {
    const { rows: strategies } = await pool.query('SELECT * FROM strategies ORDER BY created_at DESC');

    // notes table may not exist yet (created lazily by seed_note.js) — don't let that break the hub page
    let notes = [];
    try {
      const result = await pool.query('SELECT * FROM notes ORDER BY created_at DESC');
      notes = result.rows;
    } catch (notesErr) {
      if (notesErr.code !== '42P01') throw notesErr; // 42P01 = undefined_table; anything else is a real error
      console.warn('notes table not found yet — showing hub with 0 research notes');
    }

    res.send(hubPage(strategies, notes));
  } catch (err) {
    console.error(err);
    res.status(500).send('Database error: ' + err.message);
  }
});

app.get('/strategy/:slug', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM strategies WHERE slug = $1', [req.params.slug]);
    if (!rows.length) {
      return res.status(404).send(layout('Not found', '', '<div class="page"><p>Strategy not found.</p></div>'));
    }
    res.send(detailPage(rows[0]));
  } catch (err) {
    console.error(err);
    res.status(500).send('Database error: ' + err.message);
  }
});

app.get('/notes/:slug', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM notes WHERE slug = $1', [req.params.slug]);
    if (!rows.length) {
      return res.status(404).send(layout('Not found', '', '<div class="page"><p>Note not found.</p></div>'));
    }
    res.send(notePage(rows[0]));
  } catch (err) {
    if (err.code === '42P01') {
      return res.status(404).send(layout('Not found', '', '<div class="page"><p>Note not found.</p></div>'));
    }
    console.error(err);
    res.status(500).send('Database error: ' + err.message);
  }
});

app.listen(PORT, () => {
  console.log('Strategy Desk running on port ' + PORT);
});
