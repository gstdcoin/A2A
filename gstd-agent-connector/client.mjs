const ORIGIN='https://app.gstdtoken.com';
const modelPattern=/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$/;
export class ConnectorError extends Error{
 constructor(code,status=0,retryAfter=0){super(code);this.code=code;this.status=status;this.retryAfter=retryAfter;}
}
export function policyFromEnv(env=process.env){
 if(env.GSTD_AGENT_ALLOW_INFERENCE!==undefined&&!['0','1'].includes(env.GSTD_AGENT_ALLOW_INFERENCE))throw new ConnectorError('invalid_inference_policy');
 const raw=env.GSTD_AGENT_MAX_REQUESTS??'10',limit=Number(raw);
 if(!/^\d+$/.test(raw)||!Number.isSafeInteger(limit)||limit<1||limit>50)throw new ConnectorError('invalid_request_limit');
 const allowed=(env.GSTD_AGENT_ALLOWED_MODELS??'auto').split(',').map(s=>s.trim());
 if(!allowed.length||allowed.length>30||allowed.some(s=>!modelPattern.test(s)))throw new ConnectorError('invalid_model_policy');
 return Object.freeze({inference_enabled:env.GSTD_AGENT_ALLOW_INFERENCE==='1',allowed_models:Object.freeze([...new Set(allowed)]),max_attempts_per_process:limit,max_cost_gstd:0});
}
async function boundedJson(response){
 const reader=response.body?.getReader();if(!reader)throw new ConnectorError('invalid_upstream_response');
 let size=0;const chunks=[];
 try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>1048576)throw new ConnectorError('upstream_response_too_large');chunks.push(value);}}
 finally{await reader.cancel().catch(()=>{});}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
 try{return JSON.parse(new TextDecoder().decode(bytes));}catch{throw new ConnectorError('invalid_upstream_response');}
}
const canonical=s=>s.endsWith(':latest')?s.slice(0,-7):s;
export function createConnector({policy=policyFromEnv(),fetchImpl=fetch,now=Date.now}={}){
 const cache=new Map(),pending=new Map();let attempts=0,inFlight=false,cooldown=0;
 async function request(path,body){
  if(now()<cooldown)throw new ConnectorError('rate_limited',429,Math.ceil((cooldown-now())/1000));
  let response;
  try{response=await fetchImpl(ORIGIN+path,{method:body?'POST':'GET',redirect:'error',headers:{Accept:'application/json',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(body?45000:8000)});}
  catch{throw new ConnectorError(body?'request_outcome_unknown':'service_unavailable');}
  if(response.status===429){const raw=response.headers.get('retry-after'),wait=raw&&/^\d+$/.test(raw)?Math.max(1,Math.min(3600,Number(raw))):60;cooldown=now()+wait*1000;await response.body?.cancel();throw new ConnectorError('rate_limited',429,wait);}
  if(!response.ok){await response.body?.cancel();throw new ConnectorError(response.status===402?'payment_or_quota_required':'upstream_error',response.status);}
  const data=await boundedJson(response);
  if(!data||typeof data!=='object'||Array.isArray(data))throw new ConnectorError('invalid_upstream_response');
  return data;
 }
 async function cached(path,ttl){
  const found=cache.get(path);if(found&&found.until>now())return found.data;
  if(pending.has(path))return pending.get(path);
  const operation=request(path).then(data=>{cache.set(path,{data,until:now()+ttl});return data;}).finally(()=>pending.delete(path));
  pending.set(path,operation);return operation;
 }
 return{
  policy,
  async status(){return{network:await cached('/api/v1/network/stats',30000),connector:{...policy,attempts_used:attempts,spending_authority:false,signing_authority:false}};},
  async models(){const data=await cached('/api/v1/models/available',60000);if(!Array.isArray(data.models))throw new ConnectorError('invalid_catalogue');return data;},
  async infer({prompt,model='auto',max_tokens=128,allow_network,max_cost_gstd}={}){
   if(!policy.inference_enabled)throw new ConnectorError('inference_disabled');
   if(allow_network!==true)throw new ConnectorError('network_consent_required');
   if(max_cost_gstd!==0)throw new ConnectorError('zero_cost_limit_required');
   if(typeof model!=='string'||!policy.allowed_models.includes(model))throw new ConnectorError('model_not_allowed');
   if(typeof prompt!=='string'||!prompt.trim()||prompt.length>4000||Buffer.byteLength(prompt)>16000)throw new ConnectorError('invalid_prompt');
   if(!Number.isSafeInteger(max_tokens)||max_tokens<1||max_tokens>256)throw new ConnectorError('invalid_max_tokens');
   if(inFlight)throw new ConnectorError('inference_busy');
   if(attempts>=policy.max_attempts_per_process)throw new ConnectorError('process_budget_exhausted');
   inFlight=true;
   try{
    if(model!=='auto'){
     const catalogue=await this.models(),offer=catalogue.models.find(m=>m.model_id===model);
     if(!offer||!(offer.nodes_count>0))throw new ConnectorError('model_unavailable');
     if(offer.price_gstd!==0||offer.is_free!==true)throw new ConnectorError('paid_model_requires_wallet');
    }
    // Count attempts before dispatch. Failure and uncertainty never trigger a retry.
    attempts++;
    const data=await request('/api/v1/agents/infer',{model,messages:[{role:'user',content:prompt}],max_tokens,allow_network:true,max_cost_gstd:0});
    if(data._gstd?.error||data._gstd?.billing?.free!==true)throw new ConnectorError('unverified_free_result');
    if(typeof data.model!=='string'||(model!=='auto'&&canonical(data.model)!==canonical(model)))throw new ConnectorError('model_mismatch');
    const result=data.choices?.[0]?.message?.content;if(typeof result!=='string'||!result.trim()||Buffer.byteLength(result)>65536)throw new ConnectorError('invalid_model_result');
    return{model:data.model,result,usage:data.usage??null,cost_gstd:0,attempts_used:attempts,remaining_attempts:policy.max_attempts_per_process-attempts,output_is_untrusted:true};
   }finally{inFlight=false;}
  }
 };
}
