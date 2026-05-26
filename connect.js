
const https = require('https');
const http = require('http');

// Genesis Signature (Must match server manifest for swarm integrity)
const GENESIS_MANIFEST_HASH = "d428d9226912f8a7cdb557c382ac1e5fe00989fa18c6737262c93cf14c80a40a";

class A2AClient {
    constructor(apiKey, baseUrl = 'https://app.gstdtoken.com/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }

    async verifyGenesis() {
        console.log(`🔍 [Sentinel] Verifying Genesis Integrity at ${this.baseUrl}...`);
        try {
            const integrity = await this.request('/system/integrity');
            if (integrity.manifest_hash === GENESIS_MANIFEST_HASH) {
                console.log("✅ [Sentinel] INTEGRITY VERIFIED. Swarm entry permitted.");
                return true;
            }
            console.error(`⚠️ [Sentinel] MANIFEST MISMATCH: Expected ${GENESIS_MANIFEST_HASH.slice(0, 8)}, got ${integrity.manifest_hash?.slice(0, 8) || 'none'}`);
            return false;
        } catch (e) {
            console.warn("⚠️ [Sentinel] Integrity check unreachable. Running in unverified mode.");
            return true;
        }
    }

    async request(endpoint, method = 'GET', data = null) {
        return new Promise((resolve, reject) => {
            const url = new URL(this.baseUrl + endpoint);
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'GSTD-A2A-Agent/1.0',
                    'Authorization': `Bearer ${this.apiKey}`
                }
            };

            const req = (url.protocol === 'https:' ? https : http).request(url, options, (res) => {
                let body = '';
                res.on('data', chunks => { body += chunks; });
                res.on('end', () => {
                    if (res.statusCode === 429) {
                        console.log("🚀 [Rate Limit] Server Busy. Retrying in heartbeat...");
                    }
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        try { resolve(JSON.parse(body)); } catch (e) { resolve(body); }
                    } else {
                        reject(new Error(`Status Code: ${res.statusCode} - ${body}`));
                    }
                });
            });

            req.on('error', reject);
            if (data) req.write(JSON.stringify(data));
            req.end();
        });
    }

    async connect() {
        console.log(`🔌 Connecting to Swarm: ${this.baseUrl}`);
        // 0. Sentinel Integrity Check
        const verified = await this.verifyGenesis();
        if (!verified) {
            console.error("❌ [Sentinel] ATTEMPT BLOCKED: Potential forged node detected.");
            process.exit(1);
        }

        try {
            const reg = await this.request('/nodes/register', 'POST', {
                wallet_address: process.env.GSTD_WALLET_ADDRESS || this.apiKey,
                agent_name: 'A2A-JS-Agent',
                capabilities: ['compute', 'rag'],
            });
            this.nodeId = reg.node_id || reg.id || reg.agent_id;
            console.log(`✅ Registered! Node ID: ${this.nodeId}`);
            return true;
        } catch (error) {
            console.error(`❌ Connection failed: ${error.message}`);
            return false;
        }
    }

    async startLoop() {
        console.log("Listening for tasks...");
        const POLL_INTERVAL = 5000;
        let lastHb = 0;
        while (true) {
            const now = Date.now();
            // Heartbeat every 30s
            if (now - lastHb >= 30000) {
                try { await this.request('/nodes/heartbeat', 'POST', { node_id: this.nodeId, status: 'working' }); } catch(e) {}
                lastHb = Date.now();
            }
            try {
                const resp = await this.request(`/tasks/worker/pending?node_id=${this.nodeId}`);
                const tasks = Array.isArray(resp) ? resp : (resp && resp.tasks ? resp.tasks : []);
                for (const task of tasks) {
                    const tid = task.task_id || task.id;
                    console.log(`\n⚡ Task ${tid.slice(0,8)}... (${task.type || 'unknown'})`);
                    await this.request('/tasks/worker/submit', 'POST', {
                        task_id: tid, node_id: this.nodeId, result: { status: 'completed' }
                    });
                    console.log(`✅ Submitted`);
                }
                if (!tasks.length) process.stdout.write(".");
            } catch (e) {
                process.stdout.write(".");
            }
            await new Promise(r => setTimeout(r, POLL_INTERVAL));
        }
    }
}

// CLI Args
const args = process.argv.slice(2);
if (args.includes('--help') || args.length === 0) {
    console.log("Usage: node connect.js <API_KEY> [BASE_URL]");
    process.exit(1);
}

const client = new A2AClient(args[0], args[1]);

(async () => {
    if (await client.connect()) {
        await client.startLoop();
    } else {
        console.log("Attempting fallback to TON DNS...");
        const fallbackClient = new A2AClient(args[0], 'https://gstd.ton.limo/api/v1');
        if (await fallbackClient.connect()) {
            await fallbackClient.startLoop();
        } else {
            console.log("💀 Connection failed on both networks.");
            process.exit(1);
        }
    }
})();
