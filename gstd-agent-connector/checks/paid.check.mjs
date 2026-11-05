import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPaidConnector,readPaidCredential} from '../paid-client.mjs';
import {createMcpServer} from '../server.mjs';
const token='gstd_agent_'+'a'.repeat(36)+'.'+'b'.repeat(64),credential={token,max_cost_gstd:'0.005'};
const input={request_id:'fixture-request-123',prompt:'fixture',model:'qwen2.5:0.5b',max_tokens:32,allow_network:true,max_cost_gstd:'0.005'};
test('paid inference uses a separate file credential and exact cost cap, without retry',async()=>{
 const calls=[],client=createPaidConnector({credentialFile:'/fixture',loadCredential:async()=>credential,fetchImpl:async(url,init)=>{
  calls.push({url,init});return new Response(JSON.stringify({_gstd:{payment_id:'fixture-job',billing:{charged_gstd:0.005}},model:input.model,choices:[{message:{content:'fixture'}}]}));
 }});
 await assert.rejects(client.infer({...input,max_cost_gstd:'0.006'}),/local_paid_cap_exceeded/);
 await assert.rejects(client.infer({...input,allow_network:false}),/network_consent_required/);
 await assert.rejects(client.infer({...input,model:'auto'}),/exact_model_required/);
 const result=await client.infer(input);assert.equal(result.cost_gstd,0.005);assert.equal(result.output_is_untrusted,true);
 assert.equal(calls.length,1);assert.equal(calls[0].init.redirect,'error');
 assert.equal(calls[0].init.headers.Authorization,'Bearer '+token);
 assert.equal(JSON.parse(calls[0].init.body).request_id,input.request_id);
});
test('unknown outcomes require receipt lookup; no automatic repeat or fallback',async()=>{
 let count=0;const client=createPaidConnector({credentialFile:'/fixture',loadCredential:async()=>credential,fetchImpl:async(url)=>{
  count++;if(!url.includes('?'))throw Error('private transport detail');
  return new Response(JSON.stringify({state:'captured',payment_id:'fixture',response:{}}));
 }});
 await assert.rejects(client.infer(input),/request_outcome_unknown_check_receipt/);assert.equal(count,1);
 assert.equal((await client.receipt({request_id:input.request_id})).state,'captured');assert.equal(count,2);
});
test('paid tools require an explicit credential-file configuration',async()=>{
 const fake={policy:{inference_enabled:false},status:async()=>({}),models:async()=>({models:[]})};
 const readOnly=createMcpServer(fake,null);assert.equal(Object.keys(readOnly._registeredTools).length,2);
 const paid=createMcpServer(fake,createPaidConnector({credentialFile:'/fixture'}));
 assert.ok(paid._registeredTools.gstd_paid_inference);
 await assert.rejects(readPaidCredential('/nonexistent-gstd-credential-fixture'),/paid_credential_unavailable/);
});
