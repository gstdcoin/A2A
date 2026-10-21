#!/usr/bin/env node
'use strict';

function getApiBase(value = process.env.GSTD_API_URL || 'https://app.gstdtoken.com') {
    let base = String(value);
    while (base.endsWith('/')) base = base.slice(0, -1);
    return base.endsWith('/api/v1') ? base : `${base}/api/v1`;
}

class A2AClient {
    constructor(walletAddress, baseUrl = getApiBase()) {
        this.walletAddress = walletAddress;
        this.baseUrl = getApiBase(baseUrl);
        this.nodeId = null;
    }

    async request(path, method = 'GET', data = undefined) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.walletAddress) {
            headers['X-Wallet-Address'] = this.walletAddress;
        }

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
        const result = await this.request('/nodes/register', 'POST', {
            name,
            specs: {
                type: 'agent',
                capabilities: ['text-processing', 'data-validation'],
            },
        });
        if (!result.node_id) {
            throw new Error(`Registration response did not include node_id: ${JSON.stringify(result)}`);
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

    async run() {
        let lastHeartbeat = 0;
        let stopping = false;
        process.once('SIGINT', () => { stopping = true; });

        console.log(`Monitoring node ${this.nodeId} via ${this.baseUrl}`);
        while (!stopping) {
            try {
                if (Date.now() - lastHeartbeat >= 180000) {
                    await this.heartbeat();
                    lastHeartbeat = Date.now();
                    console.log('Heartbeat sent.');
                }

                const tasks = await this.getTasks();
                for (const task of tasks) {
                    const taskId = task.task_id || task.id || 'unknown';
                    console.log(
                        `Task ${taskId} assigned. No task executor is configured; ` +
                        'the client will not submit a placeholder result.'
                    );
                }
            } catch (error) {
                console.error(`GSTD API error: ${error.message}`);
            }
            await new Promise(resolve => setTimeout(resolve, 10000));
        }
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
