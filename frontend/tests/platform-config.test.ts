import {describe,it,expect,vi,afterEach} from 'vitest';
import {PlatformConfigApi,ApiError,blockingReasonsOf,describeApiError} from '../src/adapters/platform-config';
const signal=new AbortController().signal;
type Call={url:string;init:RequestInit};
function reply(status:number,body:unknown,statusText='fixture'):Call[]{
  const calls:Call[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    calls.push({url:String(input),init:init??{}});
    return {ok:status>=200&&status<300,status,statusText,json:async()=>body} as unknown as Response;
  }));
  return calls;
}
afterEach(()=>vi.unstubAllGlobals());
describe('platform configuration wire client',()=>{
 it('reads drafts and Sessions without inventing readiness',async()=>{
  const calls=reply(200,[]);const api=new PlatformConfigApi();
  await expect(api.listDrafts(signal)).resolves.toEqual([]);await expect(api.listSessions(signal)).resolves.toEqual([]);
  expect(calls[0].url).toBe('/api/v1/experiment-drafts');expect(calls[0].init.method).toBe('GET');
  expect(calls[1].url).toBe('/api/v1/sessions');
 });
 it('saves with base_revision and validates with the exact execution revision and fingerprint',async()=>{
  const draft={draft_id:'draft-1',draft_revision:3,execution_revision:2,fingerprint:'a'.repeat(64)};
  const calls=reply(200,draft);const api=new PlatformConfigApi();
  await api.saveDraft('draft-1',2,'名称','描述',signal);
  expect(calls[0].url).toBe('/api/v1/experiment-drafts/draft-1');expect(calls[0].init.method).toBe('PUT');
  expect(JSON.parse(calls[0].init.body as string)).toEqual({base_revision:2,name:'名称',description:'描述'});
  await api.validateDraft('draft-1',2,'a'.repeat(64),signal);
  expect(calls[1].url).toBe('/api/v1/experiment-drafts/draft-1/validate');expect(calls[1].init.method).toBe('POST');
  expect(JSON.parse(calls[1].init.body as string)).toEqual({execution_revision:2,fingerprint:'a'.repeat(64)});
 });
 it('preserves a 409 conflict code, detail and blocking reasons',async()=>{
  reply(409,{detail:{code:'conflict',message:'Draft changed in another host; reload before saving'}});
  const error=await new PlatformConfigApi().saveDraft('draft-1',1,'n','d',signal).catch((cause)=>cause);
  expect(error).toBeInstanceOf(ApiError);expect(error.status).toBe(409);expect(error.code).toBe('conflict');
  expect(describeApiError(error)).toContain('reload before saving');
  expect(blockingReasonsOf(error)).toEqual([]);
 });
 it('keeps validation blocking reasons from 409 responses',async()=>{
  reply(409,{detail:{code:'validation_incomplete',message:'Snapshot is not execution eligible',blocking_reasons:[{key:'interface_profile',scope:'configuration',message:'observed g4a1-1.0'}]}});
  const error=await new PlatformConfigApi().validateDraft('draft-1',1,'a'.repeat(64),signal).catch((cause)=>cause) as ApiError;
  expect(error.code).toBe('validation_incomplete');expect(blockingReasonsOf(error)[0].scope).toBe('configuration');
 });
 it('reports FastAPI validation detail arrays with the field path',async()=>{
  reply(422,{detail:[{loc:['body','base_revision'],msg:'Field required'}]});
  const error=await new PlatformConfigApi().saveDraft('draft-1',1,'n','d',signal).catch((cause)=>cause);
  expect(error).toBeInstanceOf(ApiError);expect(error.code).toBe('validation_error');expect(describeApiError(error)).toContain('base_revision');
 });
 it('reads a snapshot by immutable id and the execution recipe',async()=>{
  const calls=reply(200,{snapshot_id:'cs-1'});const api=new PlatformConfigApi();
  await api.getSnapshot('cs-1',signal);await api.executionRecipe(signal);
  expect(calls[0].url).toBe('/api/v1/config-snapshots/cs-1');
  expect(calls[1].url).toBe('/api/v1/mobilecar/execution-recipe');
 });
});
