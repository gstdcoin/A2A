import {open} from 'node:fs/promises';
import {isAbsolute} from 'node:path';
import {ConnectorError} from './client.mjs';
const ORIGIN='https://app.gstdtoken.xyz';
const amount=s=>{
 if(typeof s!=='string'||!/^(0|[1-9]\d{0,9})(\.\d{1,9})?$/.test(s))throw new ConnectorError('invalid_paid_cap');
 const [w,f='']=s.split('.');return BigInt(w)*1000000000n+BigInt(f.padEnd(9,'0'));
};
export async function readPaidCredential(path){
 if(typeof path!=='string'||!isAbsolute(path))throw new ConnectorError('invalid_credential_path');
 let file;
 try{
  file=await open(path,'r');const stat=await file.stat();
  if(!stat.isFile()||stat.size>8192)throw new Error();
  const d=JSON.parse(await file.readFile('utf8'));
  if(!/^gstd_agent_[a-f0-9-]{36}\.[a-f0-9]{64}$/.test(d.token)||amount(d.max_cost_gstd)<=0n)throw new Error();
  return {token:d.token,max_cost_gstd:d.max_cost_gstd};
 }catch{throw new ConnectorError('paid_credential_unavailable');}finally{await file?.close();}
}
export function createPaidConnector({credentialFile,fetchImpl=fetch,loadCredential=readPaidCredential,now=Date.now}={}){
 let inFlight=false,cooldown=0;
 async function request(query='',body,kind='infer'){
  const credential=await loadCredential(credentialFile);
  if(now()<cooldown)throw new ConnectorError('rate_limited',429,Math.ceil((cooldown-now())/1000));
  if(body&&kind==='infer'&&amount(body.max_cost_gstd)>amount(credential.max_cost_gstd))throw new ConnectorError('local_paid_cap_exceeded');
  let r;
  try{r=await fetchImpl(ORIGIN+(kind==='quote'?'/api/v1/economics/quotes':'/api/v1/agents/paid-infer')+query,{
   method:body?'POST':'GET',redirect:'error',headers:{Accept:'application/json',Authorization:'Bearer '+credential.token,
   ...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(body?65000:8000)});
  }catch{throw new ConnectorError(body?'request_outcome_unknown_check_receipt':'service_unavailable');}
  if(r.status===429){cooldown=now()+60000;await r.body?.cancel();throw new ConnectorError('rate_limited',429,60);}
  const reader=r.body?.getReader();if(!reader)throw new ConnectorError('invalid_upstream_response');
  const chunks=[];let size=0;
  try{for(;;){const v=await reader.read();if(v.done)break;size+=v.value.length;if(size>1048576)throw new ConnectorError('upstream_response_too_large');chunks.push(v.value);}}
  finally{await reader.cancel().catch(()=>{});}
  let data;try{data=JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw new ConnectorError('invalid_upstream_response');}
  if(!r.ok)throw new ConnectorError(['grant_inactive','grant_budget_exhausted','insufficient_balance','backing_not_reconciled','request_not_found','price_exceeds_permission','grant_scope_denied','no_paid_executor','paid_response_expired_or_deleted','idempotency_conflict','request_already_processed','request_in_progress','reservation_expired','agent_auth_required','quote_already_used','price_quote_required','price_quote_expired','price_quote_mismatch','no_priced_executor','market_price_unavailable'].includes(data?.error)?data.error:'paid_request_failed',r.status);
  return data;
 }
 return{
  async quote({prompt,model,max_tokens=128,allow_network,max_cost_gstd}={}){
   if(allow_network!==true)throw new ConnectorError('network_consent_required');
   if(typeof model!=='string'||model==='auto'||!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$/.test(model))throw new ConnectorError('exact_model_required');
   if(typeof prompt!=='string'||!prompt.trim()||prompt.length>4000||Buffer.byteLength(prompt)>16000)throw new ConnectorError('invalid_prompt');
   if(!Number.isSafeInteger(max_tokens)||max_tokens<1||max_tokens>512)throw new ConnectorError('invalid_max_tokens');
   if(amount(max_cost_gstd)<=0n)throw new ConnectorError('invalid_paid_cap');
   const credential=await loadCredential(credentialFile);
   if(amount(max_cost_gstd)>amount(credential.max_cost_gstd))throw new ConnectorError('local_paid_cap_exceeded');
   const d=await request('',{model,messages:[{role:'user',content:prompt}],max_tokens,allow_network:true},'quote'),q=d.quote;
   if(!q||typeof q.id!=='string'||q.model!==model||!Number.isSafeInteger(q.expiresAt)||q.expiresAt<=now()||amount(q.price_gstd)<=0n)throw new ConnectorError('invalid_quote');
   return{quote_id:q.id,model:q.model,node_id:q.nodeId,price_gstd:q.price_gstd,price_usd:q.price_usd,expires_at:q.expiresAt,
    within_cost_cap:amount(q.price_gstd)<=amount(max_cost_gstd),funds_reserved:false,quote_is_not_a_stablecoin_payment:true};
  },
  async status(){const d=await request();return{grant:d.grant,signing_authority:false,withdrawal_authority:false};},
  async receipt({request_id}={}){
   if(typeof request_id!=='string'||!/^[A-Za-z0-9_-]{8,100}$/.test(request_id))throw new ConnectorError('invalid_request_id');
   return{...await request('?request_id='+encodeURIComponent(request_id)),output_is_untrusted:true};
  },
  async infer({request_id,prompt,model,max_tokens=128,allow_network,max_cost_gstd,quote_id}={}){
   if(allow_network!==true)throw new ConnectorError('network_consent_required');
   if(typeof request_id!=='string'||!/^[A-Za-z0-9_-]{8,100}$/.test(request_id))throw new ConnectorError('invalid_request_id');
   if(typeof model!=='string'||model==='auto'||!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$/.test(model))throw new ConnectorError('exact_model_required');
   if(typeof prompt!=='string'||!prompt.trim()||prompt.length>4000||Buffer.byteLength(prompt)>16000)throw new ConnectorError('invalid_prompt');
   if(!Number.isSafeInteger(max_tokens)||max_tokens<1||max_tokens>512)throw new ConnectorError('invalid_max_tokens');
   if(amount(max_cost_gstd)<=0n)throw new ConnectorError('invalid_paid_cap');
   if(inFlight)throw new ConnectorError('inference_busy');inFlight=true;
   try{
    const d=await request('',{request_id,prompt,model,max_tokens,allow_network:true,max_cost_gstd,...(quote_id?{quote_id}:{})});
    const charged=d._gstd?.billing?.charged_gstd,result=d.choices?.[0]?.message?.content;
    if(typeof charged!=='number'||!Number.isFinite(charged)||charged<=0||(typeof d._gstd.billing.charged_nano==='string'&&/^\d+$/.test(d._gstd.billing.charged_nano)?BigInt(d._gstd.billing.charged_nano):amount(charged.toFixed(9)))>amount(max_cost_gstd)||
       typeof d.model!=='string'||d.model.replace(/:latest$/,'')!==model.replace(/:latest$/,'')||
       typeof result!=='string'||!result.trim()||Buffer.byteLength(result)>65536)throw new ConnectorError('unverified_paid_result_check_receipt');
    return{request_id,payment_id:d._gstd.payment_id,model:d.model,result,cost_gstd:charged,output_is_untrusted:true};
   }finally{inFlight=false;}
  }
 };
}
