#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

function getApiBase(value = process.env.GSTD_API_URL || 'https://app.gstdtoken.com') {
    let base = String(value);
    while (base.endsWith('/')) base = base.slice(0, -1);
    return base.endsWith('/api/v1') ? base : `${base}/api/v1`;
}

class A2AClient {
    constructor(walletAddress, baseUrl = getApiBase(), options = {}) {
        this.walletAddress = walletAddress;
        this.baseUrl = getApiBase(baseUrl);
        this.nodeId = options.nodeId || null;
        this.identityPath = options.identityPath || process.env.GSTD_JS_NODE_IDENTITY_FILE
            || path.join(os.homedir(), '.config', 'gstd', 'node-ed25519.pem');
        this.executeTask = options.executeTask;
        this.identity = null;
    }

    loadIdentity() {
        if (this.identity) return this.identity;
        fs.mkdirSync(path.dirname(this.identityPath), { recursive: true, mode: 0o700 });
        if (!fs.existsSync(this.identityPath)) {
            const generated = crypto.generateKeyPairSync('ed25519');
            try {
                fs.writeFileSync(this.identityPath, generated.privateKey.export({ type: 'pkcs8', format: 'pem' }), { flag: 'wx', mode: 0o600 });
            } catch (error) { if (error.code !== 'EEXIST') throw error; }
        }
        const privateKey = crypto.createPrivateKey(fs.readFileSync(this.identityPath));
        if (privateKey.asymmetricKeyType !== 'ed25519') throw new Error('Node identity must be Ed25519');
        const publicKey = crypto.createPublicKey(privateKey).export({ type: 'spki', format: 'der' }).subarray(-32).toString('hex');
        this.identity = { privateKey, publicKey };
        return this.identity;
    }

    nodeHeaders() {
        const identity = this.loadIdentity();
        const timestamp = String(Date.now());
        const digest = crypto.createHash('sha256').update(`${this.nodeId}:${timestamp}`).digest();
        return { 'X-GSTD-Node-Id': this.nodeId, 'X-GSTD-Node-Ts': timestamp,
            'X-GSTD-Node-Sig': crypto.sign(null, digest, identity.privateKey).toString('hex') };
    }

    async request(path, method = 'GET', data = undefined) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.walletAddress) {
            headers['X-Wallet-Address'] = this.walletAddress;
        }

        if (this.nodeId) Object.assign(headers, this.nodeHeaders());

        let response;
        try {
            response = await fetch(`${this.baseUrl}${path}`, {
                method,
                headers,
                body: data === undefined ? undefined : JSON.stringify(data),
                signal: AbortSignal.timeout(15000),
            });
        } catch (error) {
            throw new Error(`Could not reach GSTD API: ${error.message}`);
        }

        const body = await response.text();
        let result;
        try {
            result = body ? JSON.parse(body) : {};
        } catch {
            throw new Error(`GSTD API returned invalid JSON (HTTP ${response.status})`);
        }
        if (!response.ok) {
            throw new Error(`GSTD API returned HTTP ${response.status}: ${JSON.stringify(result)}`);
        }
        return result;
    }

    async connect(name = 'A2A-Agent') {
        if (!this.walletAddress) throw new Error('Wallet address is required');
        const identity = this.loadIdentity();
        this.nodeId = this.nodeId || `a2a-${identity.publicKey.slice(0, 24)}`;
        const result = await this.request('/nodes/register', 'POST', {
            node_id: this.nodeId,
            node_pubkey: identity.publicKey,
            name,
            specs: {
                type: 'agent',
                capabilities: ['text-processing', 'data-validation'],
            },
        });
        if (result.node_id !== this.nodeId) {
            throw new Error('Registration returned a node_id different from the signed identity');
        }
        this.nodeId = result.node_id;
        return this.nodeId;
    }

    async heartbeat() {
        return this.request('/nodes/heartbeat', 'POST', {
            node_id: this.nodeId,
            wallet_address: this.walletAddress,
            status: 'active',
        });
    }

    async getTasks() {
        const query = new URLSearchParams({ node_id: this.nodeId });
        const result = await this.request(`/tasks/worker/pending?${query}`);
        if (!Array.isArray(result.tasks)) {
            throw new Error('GSTD API returned an unexpected task-list response');
        }
        return result.tasks;
    }

    async submitResult(task, result) {
        return this.request('/tasks/worker/submit', 'POST', { task_id: task.task_id || task.id, node_id: this.nodeId, result });
    }

    async run({ signal, intervalMs = 10000 } = {}) {
        let lastHeartbeat = 0;
        let stopping = false;
        const onStop = () => { stopping = true; };
        process.once('SIGINT', onStop);

        console.log(`Monitoring node ${this.nodeId} via ${this.baseUrl}`);
        if (typeof this.executeTask !== 'function') console.log('No executor configured: task polling is disabled.');
        try {
        while (!stopping && !signal?.aborted) {
            try {
                if (Date.now() - lastHeartbeat >= 180000) {
                    await this.heartbeat();
                    lastHeartbeat = Date.now();
                    console.log('Heartbeat sent.');
                }

                if (stopping || signal?.aborted) break;
                if (typeof this.executeTask === 'function') {
                    for (const task of await this.getTasks()) {
                        const result = await this.executeTask(task);
                        const nonEmpty = typeof result === 'string' ? !!result.trim()
                            : !!result && typeof result === 'object' && Object.keys(result).length > 0;
                        if (!nonEmpty) throw new Error('Executor returned an empty result; nothing submitted');
                        await this.submitResult(task, result);
                    }
                }
            } catch (error) {
                console.error(`GSTD API error: ${error.message}`);
            }
            await new Promise(resolve => setTimeout(resolve, intervalMs));
        }
        } finally { process.removeListener('SIGINT', onStop); }
        console.log('Node monitor stopped.');
    }
}

async function main() {
    const args = process.argv.slice(2);
    if (args.includes('--help')) {
        console.log('Usage: node connect.js <TON_WALLET_ADDRESS> [API_BASE_URL]');
        console.log('Or set GSTD_WALLET_ADDRESS and optionally GSTD_API_URL.');
        return;
    }

    const walletAddress = process.env.GSTD_WALLET_ADDRESS || args[0];
    if (!walletAddress) {
        throw new Error('Provide a wallet address or set GSTD_WALLET_ADDRESS.');
    }

    const client = new A2AClient(walletAddress, args[1]);
    const nodeId = await client.connect();
    console.log(`Registered node ${nodeId}. Press Ctrl+C to stop.`);
    await client.run();
}

if (require.main === module) {
    main().catch(error => {
        console.error(`GSTD connector failed: ${error.message}`);
        process.exitCode = 1;
    });
}

module.exports = { A2AClient, getApiBase };
