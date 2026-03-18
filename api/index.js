/**
 * GSTD Node — Vercel Edge API
 * 
 * This serverless function provides a lightweight GSTD node
 * that connects to the GSTD swarm via the platform API.
 * 
 * Deploy: Import this repo on Vercel → instant node.
 */

const express = require('express');
const { randomUUID } = require('crypto');
const path = require('path');
const app = express();

app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

const PLATFORM_API = process.env.GSTD_API_URL || 'https://app.gstdtoken.com/api/v1';
const NODE_ID = process.env.GSTD_NODE_ID || `vercel-${randomUUID().slice(0, 8)}`;
const DEFAULT_MODEL = process.env.GSTD_DEFAULT_MODEL || 'groq/compound';

// ─── Node Info ──────────────────────────────────────────────
app.get('/api/node/info', (_req, res) => {
    res.json({
        node_id: NODE_ID,
        version: '2.1.0',
        platform: 'vercel',
        mode: 'cloud',
        model: DEFAULT_MODEL,
        openclaw: process.env.OPENCLAW_ENABLED === 'true',
        api: PLATFORM_API,
        uptime: process.uptime(),
    });
});

// ─── Proxy to GSTD Platform API ────────────────────────────
app.all('/api/v1/*', async (req, res) => {
    const endpoint = req.path.replace('/api/v1', '');
    try {
        const resp = await fetch(`${PLATFORM_API}${endpoint}`, {
            method: req.method,
            headers: {
                'Content-Type': 'application/json',
                'X-Node-ID': NODE_ID,
                ...(req.headers['x-api-key'] ? { 'X-API-Key': req.headers['x-api-key'] } : {}),
            },
            ...(req.method !== 'GET' && req.method !== 'HEAD' ? { body: JSON.stringify(req.body) } : {}),
            signal: AbortSignal.timeout(15000),
        });
        const data = await resp.json().catch(() => ({}));
        res.status(resp.status).json(data);
    } catch (e) {
        res.status(502).json({ error: 'Platform unreachable', details: e.message });
    }
});

// ─── Chat (AI Inference via Platform) ──────────────────────
app.post('/api/chat', async (req, res) => {
    const { message, model } = req.body || {};
    if (!message) return res.status(400).json({ error: 'message required' });
    try {
        const resp = await fetch(`${PLATFORM_API}/inference`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Node-ID': NODE_ID },
            body: JSON.stringify({ model: model || DEFAULT_MODEL, prompt: message }),
            signal: AbortSignal.timeout(30000),
        });
        const data = await resp.json();
        res.json({ reply: data.content || data.response || '', model: data.model || DEFAULT_MODEL });
    } catch (e) {
        res.json({ reply: 'Service temporarily unavailable', error: e.message });
    }
});

// ─── OpenClaw Proxy ────────────────────────────────────────
['dashboard', 'agents', 'tasks', 'think', 'vision', 'models'].forEach(ep => {
    app.all(`/api/openclaw/${ep}`, async (req, res) => {
        try {
            const resp = await fetch(`${PLATFORM_API}/openclaw/${ep}`, {
                method: req.method,
                headers: { 'Content-Type': 'application/json', 'X-Node-ID': NODE_ID },
                ...(req.method !== 'GET' ? { body: JSON.stringify(req.body) } : {}),
                signal: AbortSignal.timeout(15000),
            });
            const data = await resp.json();
            res.json(data);
        } catch (e) {
            res.status(502).json({ error: `OpenClaw ${ep} unreachable` });
        }
    });
});

// ─── Health ────────────────────────────────────────────────
app.get('/api/health', (_req, res) => {
    res.json({ ok: true, node: NODE_ID, uptime: process.uptime() });
});

// ─── Wallet Status (via Platform) ──────────────────────────
app.get('/api/wallet/status', async (req, res) => {
    const wallet = req.query.address || req.headers['x-wallet-address'] || '';
    if (!wallet) return res.json({ connected: false, balance: { gstd: 0, ton: 0 } });
    try {
        const resp = await fetch(`${PLATFORM_API}/users/balance?wallet=${wallet}`, {
            signal: AbortSignal.timeout(5000),
        });
        const data = await resp.json();
        res.json({ connected: true, ...data });
    } catch (e) {
        res.json({ connected: false, balance: { gstd: 0, ton: 0 }, error: e.message });
    }
});

// ─── Serve dashboard ───────────────────────────────────────
app.get('/', (_req, res) => {
    res.sendFile(path.join(__dirname, '../public/index.html'));
});

// ─── Start ─────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
if (require.main === module) {
    app.listen(PORT, () => {
        console.log(`\n  🐝 GSTD Node (Vercel-compatible) running at http://localhost:${PORT}`);
        console.log(`  🔗 Platform: ${PLATFORM_API}`);
        console.log(`  🦞 OpenClaw: ${process.env.OPENCLAW_ENABLED === 'true' ? 'enabled' : 'disabled'}`);
        console.log(`  🧠 Model: ${DEFAULT_MODEL}\n`);
    });
}

module.exports = app;
