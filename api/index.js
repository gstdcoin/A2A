/**
 * GSTD Node — Vercel Serverless API
 * 
 * Deploy: Import this repo on Vercel → instant GSTD node.
 * Runs both as Vercel serverless function and standalone Express server.
 */

const http = require('http');
const { randomUUID } = require('crypto');

const PLATFORM_API = process.env.GSTD_API_URL || 'https://app.gstdtoken.com/api/v1';
const NODE_ID = process.env.GSTD_NODE_ID || `vercel-${randomUUID().slice(0, 8)}`;
const DEFAULT_MODEL = process.env.GSTD_DEFAULT_MODEL || 'groq/compound';

// Simple router
function parseUrl(url) {
    const [path, qs] = (url || '/').split('?');
    const params = {};
    if (qs) qs.split('&').forEach(p => { const [k, v] = p.split('='); params[k] = decodeURIComponent(v || ''); });
    return { path: path.replace(/\/+$/, '') || '/', params };
}

async function proxyToApi(endpoint, method, body) {
    const resp = await fetch(`${PLATFORM_API}${endpoint}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-Node-ID': NODE_ID },
        ...(method !== 'GET' && method !== 'HEAD' && body ? { body: JSON.stringify(body) } : {}),
        signal: AbortSignal.timeout(15000),
    });
    return resp.json().catch(() => ({}));
}

// Main handler (Vercel-compatible)
module.exports = async function handler(req, res) {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key');
    if (req.method === 'OPTIONS') { res.status(200).end(); return; }

    const { path, params } = parseUrl(req.url);
    const body = req.body || {};

    try {
        // ─── Node Info ──────────────────────────────────────
        if (path === '/api' || path === '/api/node/info') {
            return res.json({
                node_id: NODE_ID,
                version: '2.1.0',
                platform: 'vercel',
                mode: 'cloud',
                model: DEFAULT_MODEL,
                openclaw: process.env.OPENCLAW_ENABLED === 'true',
                api: PLATFORM_API,
                uptime: process.uptime(),
            });
        }

        // ─── Health ──────────────────────────────────────────
        if (path === '/api/health') {
            return res.json({ ok: true, node: NODE_ID, uptime: process.uptime() });
        }

        // ─── AI Chat ─────────────────────────────────────────
        if (path === '/api/chat' && req.method === 'POST') {
            const { message, model } = body;
            if (!message) return res.status(400).json({ error: 'message required' });
            try {
                const data = await proxyToApi('/inference', 'POST', {
                    model: model || DEFAULT_MODEL, prompt: message,
                });
                return res.json({ reply: data.content || data.response || '', model: data.model || DEFAULT_MODEL });
            } catch (e) {
                return res.json({ reply: 'Service temporarily unavailable', error: e.message });
            }
        }

        // ─── OpenClaw Proxy ──────────────────────────────────
        const ocMatch = path.match(/^\/api\/openclaw\/(\w+)$/);
        if (ocMatch) {
            try {
                const data = await proxyToApi(`/openclaw/${ocMatch[1]}`, req.method, body);
                return res.json(data);
            } catch (e) {
                return res.status(502).json({ error: `OpenClaw ${ocMatch[1]} unreachable` });
            }
        }

        // ─── Wallet Status ───────────────────────────────────
        if (path === '/api/wallet/status') {
            const wallet = params.address || req.headers['x-wallet-address'] || '';
            if (!wallet) return res.json({ connected: false, balance: { gstd: 0, ton: 0 } });
            try {
                const data = await proxyToApi(`/users/balance?wallet=${wallet}`, 'GET', null);
                return res.json({ connected: true, ...data });
            } catch (e) {
                return res.json({ connected: false, balance: { gstd: 0, ton: 0 }, error: e.message });
            }
        }

        // ─── Platform API Proxy ──────────────────────────────
        const v1Match = path.match(/^\/api\/v1\/(.*)/);
        if (v1Match) {
            try {
                const data = await proxyToApi(`/${v1Match[1]}`, req.method, body);
                return res.json(data);
            } catch (e) {
                return res.status(502).json({ error: 'Platform unreachable', details: e.message });
            }
        }

        // ─── Default ─────────────────────────────────────────
        return res.status(404).json({ error: 'Not found', endpoints: [
            'GET /api/node/info', 'GET /api/health', 'POST /api/chat',
            'ALL /api/openclaw/:action', 'GET /api/wallet/status',
            'ALL /api/v1/*'
        ]});

    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
};

// Standalone mode
if (require.main === module) {
    const PORT = process.env.PORT || 3000;
    const fs = require('fs');
    const path = require('path');

    const server = http.createServer(async (req, res) => {
        // Serve static files
        if (req.method === 'GET' && !req.url.startsWith('/api')) {
            const filePath = path.join(__dirname, '../public/index.html');
            try {
                const html = fs.readFileSync(filePath, 'utf-8');
                res.writeHead(200, { 'Content-Type': 'text/html' });
                res.end(html);
                return;
            } catch (_) {}
        }

        // Parse JSON body for POST
        let body = {};
        if (req.method === 'POST') {
            body = await new Promise((resolve) => {
                let data = '';
                req.on('data', c => data += c);
                req.on('end', () => { try { resolve(JSON.parse(data)); } catch (_) { resolve({}); } });
            });
        }

        // Wrap response object
        const mockRes = {
            statusCode: 200,
            headers: {},
            setHeader(k, v) { this.headers[k] = v; },
            status(code) { this.statusCode = code; return this; },
            json(data) {
                res.writeHead(this.statusCode, { ...this.headers, 'Content-Type': 'application/json' });
                res.end(JSON.stringify(data));
            },
            end() { res.writeHead(this.statusCode, this.headers); res.end(); },
        };

        req.body = body;
        await module.exports(req, mockRes);
    });

    server.listen(PORT, () => {
        console.log(`\n  🐝 GSTD Node running at http://localhost:${PORT}`);
        console.log(`  🔗 Platform: ${PLATFORM_API}`);
        console.log(`  🦞 OpenClaw: ${process.env.OPENCLAW_ENABLED === 'true' ? 'enabled' : 'disabled'}`);
        console.log(`  🧠 Model: ${DEFAULT_MODEL}\n`);
    });
}
