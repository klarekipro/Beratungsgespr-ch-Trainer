"""Review-only transport diagnostics. Never persist provider bodies or credentials."""
import json
import httpx
from .providers import OpenAIProvider

def error_tags(body):
    error=body.get('error') if isinstance(body,dict) else None
    if not isinstance(error,dict):return {}
    allowed={'invalid_json_schema','unsupported_parameter','invalid_request_error','model_not_found','context_length_exceeded','rate_limit_exceeded','insufficient_quota','invalid_api_key','authentication_error','server_error'}
    tags={}
    for key in ('code','type'):
        value=error.get(key)
        if value is not None:tags['provider_error_'+key]=value if isinstance(value,str) and value in allowed else 'other'
    if error.get('param') in ('text.format.schema','max_output_tokens','model','input'):tags['provider_error_param']=error['param']
    return tags

class ObservedClient:
    def __init__(self,client,diagnostics):self.client=client;self.diagnostics=diagnostics
    async def post(self,*args,**kwargs):
        d=self.diagnostics;d['stage']='provider_request'
        try:response=await self.client.post(*args,**kwargs)
        except httpx.TimeoutException as exc:d.update(stage='provider_timeout',transport_exception=type(exc).__name__);raise
        except httpx.RequestError as exc:d.update(stage='provider_transport',transport_exception=type(exc).__name__);raise
        d.update(stage='provider_response',http_status=response.status_code)
        if response.status_code!=200:
            d['stage']='provider_http'
            try:d.update(error_tags(response.json()))
            except (ValueError,UnicodeError):pass
            return response
        try:body=response.json()
        except (ValueError,UnicodeError):d.update(stage='provider_envelope_parse',envelope_json_valid=False);return response
        d['envelope_json_valid']=isinstance(body,dict)
        if not isinstance(body,dict):d['stage']='provider_envelope_parse';return response
        if body.get('error'):d.update(stage='provider_error',provider_error=True,**error_tags(body));return response
        status=body.get('status');d['provider_status']=status if status in ('completed','incomplete','failed','cancelled','queued','in_progress') else 'other'
        usage=body.get('usage')
        if isinstance(usage,dict):d['usage']={k:v for k,v in usage.items() if k in ('input_tokens','output_tokens','total_tokens') and type(v)==int and v>=0}
        reason=(body.get('incomplete_details') or {}).get('reason') if isinstance(body.get('incomplete_details'),dict) else None
        if reason:d['incomplete_reason']=reason if reason in ('max_output_tokens','content_filter') else 'other'
        if response.status_code!=200 or status!='completed':return response
        chunks=[]
        output=body.get('output')
        if not isinstance(output,list):d['stage']='provider_envelope_parse';return response
        for item in output:
            if not isinstance(item,dict) or item.get('type')!='message':continue
            content=item.get('content')
            if not isinstance(content,list):d['stage']='provider_envelope_parse';return response
            for block in content:
                if not isinstance(block,dict):d['stage']='provider_envelope_parse';return response
                if block.get('type')=='refusal':d['stage']='provider_refusal';return response
                if block.get('type')=='output_text' and isinstance(block.get('text'),str):chunks.append(block['text'])
        text=''.join(chunks);d['output_characters']=len(text);d['stage']='model_json_parse'
        try:d['model_json_object']=isinstance(json.loads(text),dict)
        except (ValueError,TypeError):d['model_json_object']=False
        return response

class ReviewProvider(OpenAIProvider):
    async def _request_json(self,instructions,data,schema,name,max_output_tokens=3500):
        self.review_diagnostics={'stage':'request_construction','output_limit':max_output_tokens}
        original=self._client
        async def request(client):
            self._client=ObservedClient(client,self.review_diagnostics)
            try:return await super(ReviewProvider,self)._request_json(instructions,data,schema,name,max_output_tokens)
            finally:self._client=original
        if original is not None:return await request(original)
        async with httpx.AsyncClient(timeout=self.timeout,follow_redirects=False,trust_env=False) as client:return await request(client)
