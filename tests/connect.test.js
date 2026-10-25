'use strict';
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { test } = require('node:test');
const { A2AClient, getApiBase } = require('../connect');

function identityOptions(t) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'gstd-a2a-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return { identityPath: path.join(directory, 'identity.pem') };
}

test('normalizes API origins and preserves an explicit API base', () => {
    assert.equal(getApiBase('https://app.gstdtoken.com/'), 'https://app.gstdtoken.com/api/v1');
    assert.equal(getApiBase('https://example.test/api/v1/'), 'https://example.test/api/v1');
});

test('persists the same protected Ed25519 identity across clients', t => {
    const options = identityOptions(t);
    const first = new A2AClient('EQ_test', undefined, options).loadIdentity();
    const second = new A2AClient('EQ_test', undefined, options).loadIdentity();
    assert.equal(first.publicKey, second.publicKey);
    if (process.platform !== 'win32') assert.equal(fs.statSync(options.identityPath).mode & 0o777, 0o600);
});

test('registers, heartbeats and polls using the wallet-bound signed contract', async t => {
    const requests = [];
    const options = identityOptions(t);
    let publicKey;
    const server = http.createServer((request, response) => {
        let body = '';
        request.setEncoding('utf8');
        request.on('data', chunk => { body += chunk; });
        request.on('end', () => {
            const data = body ? JSON.parse(body) : null;
            if (data?.node_pubkey) publicKey = data.node_pubkey;
            const nodeId = request.headers['x-gstd-node-id'];
            const timestamp = request.headers['x-gstd-node-ts'];
            const key = crypto.createPublicKey({ key: Buffer.concat([
                Buffer.from('302a300506032b6570032100', 'hex'), Buffer.from(publicKey, 'hex')
            ]), type: 'spki', format: 'der' });
            const digest = crypto.createHash('sha256').update(`${nodeId}:${timestamp}`).digest();
            assert.equal(crypto.verify(null, digest, key, Buffer.from(request.headers['x-gstd-node-sig'], 'hex')), true);
            requests.push({ method: request.method, path: request.url, wallet: request.headers['x-wallet-address'], body: data });
            response.setHeader('Content-Type', 'application/json');
            response.end(JSON.stringify(request.url.endsWith('/nodes/register') ? { node_id: data.node_id } : { tasks: [] }));
        });
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
    const client = new A2AClient('EQ_test_wallet', `http://127.0.0.1:${server.address().port}/api/v1`, options);
    const nodeId = await client.connect('Test Agent');
    assert.match(nodeId, /^a2a-[0-9a-f]{24}$/);
    assert.deepEqual(await client.heartbeat(), { tasks: [] });
    assert.deepEqual(await client.getTasks(), []);
    assert.deepEqual(requests.map(r => [r.method, r.path, r.wallet]), [
        ['POST', '/api/v1/nodes/register', 'EQ_test_wallet'],
        ['POST', '/api/v1/nodes/heartbeat', 'EQ_test_wallet'],
        ['GET', `/api/v1/tasks/worker/pending?node_id=${nodeId}`, 'EQ_test_wallet'],
    ]);
    assert.equal(requests[0].body.node_pubkey, publicKey);
    assert.equal(requests[0].body.node_id, nodeId);
});

test('rejects registration that changes the signed identity', async t => {
    const originalFetch = global.fetch;
    t.after(() => { global.fetch = originalFetch; });
    global.fetch = async () => new Response(JSON.stringify({ node_id: 'different-node' }), { status: 200 });
    const client = new A2AClient('EQ_test', undefined, identityOptions(t));
    await assert.rejects(client.connect(), /different from the signed identity/);
});

test('monitoring without an executor never claims work', async t => {
    const client = new A2AClient('EQ_test', undefined, identityOptions(t));
    const controller = new AbortController();
    let polls = 0;
    client.heartbeat = async () => { controller.abort(); return {}; };
    client.getTasks = async () => { polls++; return []; };
    await client.run({ signal: controller.signal, intervalMs: 0 });
    assert.equal(polls, 0);
});
