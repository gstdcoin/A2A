'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const { test } = require('node:test');
const { A2AClient, getApiBase } = require('../connect');

test('normalizes API origins and preserves an explicit API base', () => {
    assert.equal(getApiBase('https://app.gstdtoken.com/'), 'https://app.gstdtoken.com/api/v1');
    assert.equal(getApiBase('https://example.test/api/v1/'), 'https://example.test/api/v1');
});

test('registers and polls using the wallet-bound platform API contract', async () => {
    const requests = [];
    const server = http.createServer((request, response) => {
        let body = '';
        request.setEncoding('utf8');
        request.on('data', chunk => { body += chunk; });
        request.on('end', () => {
            requests.push({
                method: request.method,
                path: request.url,
                wallet: request.headers['x-wallet-address'],
                body: body ? JSON.parse(body) : null,
            });

            response.setHeader('Content-Type', 'application/json');
            if (request.url === '/api/v1/nodes/register') {
                response.end(JSON.stringify({ node_id: 'agent-node-1' }));
            } else {
                response.end(JSON.stringify({ tasks: [] }));
            }
        });
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const address = server.address();
    const client = new A2AClient('EQ_test_wallet', `http://127.0.0.1:${address.port}/api/v1`);

    try {
        assert.equal(await client.connect('Test Agent'), 'agent-node-1');
        assert.deepEqual(await client.heartbeat(), { tasks: [] });
        assert.deepEqual(await client.getTasks(), []);

        assert.deepEqual(requests.map(({ method, path, wallet }) => ({ method, path, wallet })), [
            {
                method: 'POST',
                path: '/api/v1/nodes/register',
                wallet: 'EQ_test_wallet',
            },
            {
                method: 'POST',
                path: '/api/v1/nodes/heartbeat',
                wallet: 'EQ_test_wallet',
            },
            {
                method: 'GET',
                path: '/api/v1/tasks/worker/pending?node_id=agent-node-1',
                wallet: 'EQ_test_wallet',
            },
        ]);
        assert.deepEqual(requests[0].body, {
            name: 'Test Agent',
            specs: {
                type: 'agent',
                capabilities: ['text-processing', 'data-validation'],
            },
        });
    } finally {
        await new Promise((resolve, reject) => {
            server.close(error => error ? reject(error) : resolve());
        });
    }
});
