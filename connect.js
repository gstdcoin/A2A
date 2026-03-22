#!/usr/bin/env node
/**
 * GSTD A2A Connector v2.0 — Node.js
 * Agent-to-Agent Protocol for the GSTD Grid
 *
 * Usage:
 *   node connect.js <API_KEY>
 *   node connect.js <API_KEY> [BASE_URL]
 *   node connect.js --register --name "MyAgent"
 *
 * Get API key: https://app.gstdtoken.com → Dashboard → Agents
 */

'use strict';

const https  = require('https');
const http   = require('http');
const os     = require('os');
const { execSync } = require('child_process');

// ─── Config ──────────────────────────────────────────────────────
const DEFAULT_API_URL    = 'https://api.gstdtoken.com/api/v1';
const FALLBACK_API_URL   = 'https://gstd.ton.limo/api/v1';
const AGENT_VERSION      = '2.0.0';
const HEARTBEAT_INTERVAL = 60_000;   // ms
const POLL_INTERVAL      = 10_000;   // ms

// ─── Logger ──────────────────────────────────────────────────────
function ts() { return new Date().toISOString().replace(/\.\d{3}Z/, 'Z'); }
function log(msg, level = 'info') {
    const icons = { info: 'ℹ️', ok: '✅', warn: '⚠️', error: '❌', earn: '💰' };
    console.log(`[${ts()}] ${icons[level] || '•'} ${msg}`);
}

// ─── HTTP request ─────────────────────────────────────────────────
function request(baseUrl, endpoint, method = 'GET', data = null, token = null) {
    return new Promise((resolve) => {
        let url;
        try { url = new URL(baseUrl + endpoint); }
        catch { return resolve(null); }

        const body = data ? JSON.stringify(data) : null;
        const headers = {
            'Content-Type':  'application/json',
            'User-Agent':    `GSTD-A2A/${AGENT_VERSION}`,
        };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (body)  headers['Content-Length'] = Buffer.byteLength(body);

        const proto = url.protocol === 'https:' ? https : http;
        const req = proto.request(url, { method, headers }, (res) => {
            let raw = '';
            res.on('data', d => raw += d);
            res.on('end', () => {
                try { resolve(JSON.parse(raw)); }
                catch { resolve(null); }
            });
        });
        req.on('error', () => resolve(null));
        req.setTimeout(15_000, () => { req.destroy(); resolve(null); });
        if (body) req.write(body);
        req.end();
    });
}

// ─── Resources ──────────────────────────────────────────────────
function getResources() {
    let cpu = 0.3, ram = 0.5;
    try {
        const cpus = os.cpus();
        const total = cpus.reduce((s, c) => s + Object.values(c.times).reduce((a, b) => a + b, 0), 0);
        const idle  = cpus.reduce((s, c) => s + c.times.idle, 0);
        cpu = 1 - idle / total;
    } catch {}
    try {
        const free  = os.freemem();
        const total = os.totalmem();
        ram = 1 - free / total;
    } catch {}
    return { cpu: parseFloat(cpu.toFixed(3)), ram: parseFloat(ram.toFixed(3)) };
}

// ─── Heartbeat → earn GSTD ──────────────────────────────────────
async function sendHeartbeat(baseUrl, apiKey, uptimeSec, tasksDone) {
    const { cpu, ram } = getResources();
    const resp = await request(baseUrl, '/agents/earn/heartbeat', 'POST', {
        cpu_usage: cpu,
        gpu_usage: 0,
        ram_usage: ram,
        uptime_seconds: uptimeSec,
        tasks_done: tasksDone,
    }, apiKey);

    if (resp) {
        const earned  = resp.net_reward || 0;
        const balance = resp.balance || '?';
        if (earned > 0) {
            log(`Heartbeat → +${earned.toFixed(6)} GSTD | CPU:${(cpu*100).toFixed(1)}% | Balance: ${balance}`, 'earn');
        } else {
            log(`Heartbeat OK | CPU:${(cpu*100).toFixed(1)}% | Balance: ${balance}`);
        }
        return earned;
    }
    log('Heartbeat failed — API unreachable', 'warn');
    return 0;
}

// ─── Task processing ─────────────────────────────────────────────
async function fetchTask(baseUrl, apiKey) {
    return request(baseUrl, '/agents/tasks/next', 'GET', null, apiKey);
}

async function submitResult(baseUrl, taskId, result, apiKey) {
    return request(baseUrl, `/agents/tasks/${taskId}/complete`, 'POST', {
        result,
        status: 'completed',
    }, apiKey);
}

async function processTask(task, baseUrl, apiKey) {
    const taskId   = task.id || '?';
    const taskType = task.type || 'compute';
    const payload  = task.payload || {};

    log(`Task [${taskId.slice(0, 8)}] type=${taskType}`);

    const result = { agent_version: AGENT_VERSION, processed_at: ts() };

    if (taskType === 'compute' || taskType === 'benchmark') {
        // CPU benchmark
        const t0 = Date.now();
        let x = 0;
        for (let i = 1; i <= 100000; i++) x += Math.sqrt(i);
        result.benchmark_ms = Date.now() - t0;
        result.checksum     = Math.round(x);
        result.status       = 'ok';

    } else if (taskType === 'inference' || taskType === 'chat') {
        const prompt  = payload.prompt || payload.message || 'hello';
        const groqKey = process.env.GROQ_API_KEY || '';
        if (groqKey) {
            const resp = await request('https://api.groq.com', '/openai/v1/chat/completions', 'POST', {
                model: 'llama-3.3-70b-versatile',
                messages: [{ role: 'user', content: prompt }],
                max_tokens: 512,
            }, groqKey);
            result.answer = resp?.choices?.[0]?.message?.content || '(no response)';
            result.model  = resp?.model;
        } else {
            result.answer = `[Agent ${AGENT_VERSION}] Set GROQ_API_KEY env var for AI inference.`;
        }
        result.status = 'ok';

    } else {
        result.status  = 'unsupported';
        result.message = `Task type '${taskType}' not supported`;
    }

    const res    = await submitResult(baseUrl, taskId, result, apiKey);
    const reward = res?.reward || 0;
    if (reward > 0) log(`Task [${taskId.slice(0, 8)}] done → +${reward.toFixed(4)} GSTD`, 'earn');
    else             log(`Task [${taskId.slice(0, 8)}] done`);
    return reward;
}

// ─── Main ────────────────────────────────────────────────────────
async function main() {
    const args     = process.argv.slice(2);
    const apiKey   = args.find(a => !a.startsWith('--')) || process.env.GSTD_API_KEY;
    const baseUrl  = args.find(a => a.startsWith('http')) || DEFAULT_API_URL;
    const noTasks  = args.includes('--no-tasks');
    const register = args.includes('--register');
    const nameIdx  = args.indexOf('--name');
    const agentName= nameIdx >= 0 ? args[nameIdx + 1] : `A2A-Agent-${os.hostname()}`;

    console.log(`
╔════════════════════════════════════════╗
║  🔱 GSTD A2A Connector v${AGENT_VERSION}        ║
║  Agent-to-Agent Protocol               ║
║  ${baseUrl.padEnd(38)}║
╚════════════════════════════════════════╝
`);

    // Registration mode
    if (register) {
        const wallet = args.find(a => a.startsWith('UQ') || a.startsWith('EQ')) || '';
        log(`Registering agent '${agentName}'...`);
        const resp = await request(baseUrl, '/agents/register', 'POST', {
            name: agentName,
            capabilities: ['compute', 'ai_inference', 'rag', 'market_analysis'],
            node_version: AGENT_VERSION,
            os: os.platform(),
            arch: os.arch(),
            wallet_address: wallet,
        });
        if (resp?.api_key) {
            log(`Registered! API Key: ${resp.api_key}`, 'ok');
            log(`Agent ID: ${resp.agent_id || '?'}`);
            console.log(`\nRun with:\n  node connect.js ${resp.api_key}\n`);
            process.exit(0);
        }
        log('Registration failed', 'error');
        process.exit(1);
    }

    if (!apiKey) {
        console.error('Usage: node connect.js <API_KEY> [BASE_URL]');
        console.error('       node connect.js --register --name "MyAgent"');
        process.exit(1);
    }

    // ── Boot ──
    log(`Connecting to ${baseUrl}`);
    const balance = await request(baseUrl, '/agents/balance', 'GET', null, apiKey);
    if (balance) {
        log(`Agent ready | Balance: ${balance.gstd_balance || '?'} GSTD`, 'ok');
    } else {
        log('Warning: Could not fetch balance. Continuing...', 'warn');
    }

    // ── Main loop ──
    const startTime   = Date.now();
    let totalEarned   = 0;
    let tasksDone     = 0;
    let nextHeartbeat = 0;
    let tick          = 0;

    log('Starting main loop. Press Ctrl+C to stop.');
    console.log();

    const loop = async () => {
        const now = Date.now();

        // Heartbeat
        if (now >= nextHeartbeat) {
            const uptime = Math.floor((now - startTime) / 1000);
            const earned = await sendHeartbeat(baseUrl, apiKey, uptime, tasksDone);
            totalEarned += earned;
            nextHeartbeat = now + HEARTBEAT_INTERVAL;
        }

        // Tasks
        if (!noTasks) {
            const task = await fetchTask(baseUrl, apiKey);
            if (task?.id) {
                const reward = await processTask(task, baseUrl, apiKey);
                totalEarned += reward;
                tasksDone++;
            }
        }

        // Stats every 10 min
        tick++;
        if (tick % (600_000 / POLL_INTERVAL) === 0) {
            const hours = ((Date.now() - startTime) / 3_600_000).toFixed(1);
            log(`📊 Session: ${hours}h | ${tasksDone} tasks | ${totalEarned.toFixed(6)} GSTD earned`);
        }

        setTimeout(loop, POLL_INTERVAL);
    };

    // Graceful shutdown
    process.on('SIGINT', () => {
        const hours = ((Date.now() - startTime) / 3_600_000).toFixed(2);
        console.log();
        log(`Stopping... ${hours}h | ${tasksDone} tasks | ${totalEarned.toFixed(6)} GSTD earned`);
        process.exit(0);
    });

    loop();
}

main().catch(err => { console.error(err); process.exit(1); });
