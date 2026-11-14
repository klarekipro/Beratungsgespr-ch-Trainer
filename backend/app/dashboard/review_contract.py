"""One structural contract for review generation and validation. No factual verdicts here.

The checker implements exactly the JSON-schema subset emitted below; unknown keywords fail
closed. Wire references select immutable sources; bound references additionally hold quotes.
"""
STAGES=('needs','capabilities','proposal')
VERDICTS=('communicated','supported','unsupported','contradicted','uncertain')
ACTIONS=('submit_to_mentor','repeat_scenario','try_another_scenario')
PRIORITY_MAX_ITEMS=2
PRIORITY_MAX_LENGTH=300

class ContractError(ValueError):
    def __init__(self,reason,path,stage='schema_validation'):
        super().__init__(reason);self.reason=reason;self.path=path;self.stage=stage

def text(limit=None):
    result={'type':'string','minLength':1,'pattern':r'\S'}
    if limit is not None:result['maxLength']=limit
    return result

def obj(properties):return {'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}
def array(items,lo,hi):return {'type':'array','items':items,'minItems':lo,'maxItems':hi}
def choice(values):return {'type':'string','enum':list(values)}

def schema(bound=False,message_ids=None,material_paths=None):
    message=choice(message_ids) if message_ids is not None else text(120)
    path=choice(material_paths or ['__no_saved_source__']) if material_paths is not None else text()
    evidence=obj({'message_id':message,**({'quote':text()} if bound else {})})
    material=obj({'path':path,**({'quote':text()} if bound else {})})
    definitions={'transcript_reference':evidence,'historical_source':material}
    evidence={'$ref':'#/$defs/transcript_reference'};material={'$ref':'#/$defs/historical_source'}
    def stage(statuses,minimum):return obj({'key':choice(STAGES),'status':choice(statuses),'observation':text(3000),'evidence':array(evidence,minimum,12)})
    material_max=0 if material_paths==[] else 3
    def claim(verdicts,minimum):return obj({'statement':text(600),'verdict':choice(verdicts),'observation':text(1200),'evidence':array(evidence,1,4),'material_evidence':array(material,minimum,material_max)})
    def ref(sections,maximum):return obj({'section':choice(sections),'index':{'type':'integer','minimum':0,'maximum':maximum}})
    refs={'anyOf':[ref(('strengths','gaps','next_attempt'),7),ref(('stages',),2)]}
    def recommendation(actions,findings):return obj({'action':choice(actions),'explanation':text(600),'priorities':array(text(PRIORITY_MAX_LENGTH),0,PRIORITY_MAX_ITEMS),'finding_refs':array(findings,1,4),'evidence':array(evidence,1,4)})
    claims=[claim(('communicated','unsupported','uncertain'),0)] if material_max==0 else [claim(('supported','contradicted'),1),claim(('communicated','unsupported','uncertain'),0)]
    result=obj({'summary':text(4000),'actual_outcome':text(4000),'strengths':array(text(2000),1,8),'gaps':array(text(2000),0,8),'next_attempt':array(text(2000),0,8),
        'stages':array({'anyOf':[stage(('evidence_found',),1),stage(('no_clear_evidence','insufficient_evidence'),0)]},3,3),
        'claim_checks':array({'anyOf':claims},0,8),
        'recommendation':{'anyOf':[recommendation(('repeat_scenario',),ref(('gaps',),7)),recommendation(('submit_to_mentor','try_another_scenario'),refs)]}})
    result['$defs']=definitions
    return result

KEYWORDS={'type','additionalProperties','required','properties','items','minItems','maxItems','minLength','maxLength','pattern','enum','minimum','maximum','anyOf','$defs','$ref'}

def validate(value,node,path='',root=None):
    """Validate the emitted subset; schema and server cannot drift on structural bounds."""
    if root is None:root=node
    if set(node)-KEYWORDS or ('pattern' in node and node['pattern']!=r'\S'):raise RuntimeError('unsupported review schema keyword')
    if '$ref' in node:
        if not node['$ref'].startswith('#/$defs/') or set(node)!={'$ref'}:raise RuntimeError('unsupported review schema reference')
        return validate(value,root['$defs'][node['$ref'].split('/')[-1]],path,root)
    def fail(keyword):
        reason='schema_'+keyword;stage='schema_validation';where=path
        if not path:reason='result_structure';where='result'
        if path.startswith('recommendation/'):
            stage='recommendation_validation'
            if path=='recommendation/priorities' and keyword in ('type','maxItems'):reason='advice priorities'
            if '/finding_refs/' in path and path.endswith('/section') and node.get('enum')==['gaps']:
                reason='repeat requires demonstrated gap';where='recommendation/finding_refs'
        if '/material_evidence' in path:
            stage='material_evidence_validation'
            reason={'minItems':'material_required','maxItems':'material_count','enum':'material_unknown_path'}.get(keyword,'material_fields')
        elif path.endswith('/message_id') and keyword=='enum':reason='unknown_message_id';stage='evidence_validation';where=path.rsplit('/',1)[0]
        elif '/evidence/' in path and keyword in ('required','additionalProperties'):reason='evidence_fields'
        raise ContractError(reason,where,stage)
    if 'anyOf' in node:
        errors=[]
        for branch in node['anyOf']:
            score=sum(1 for k,v in (branch.get('properties') or {}).items() if isinstance(value,dict) and 'enum' in v and value.get(k) in v['enum'])
            try:validate(value,branch,path,root);return
            except ContractError as error:errors.append((score,len(error.path.split('/')),error))
        raise max(errors,key=lambda x:x[:2])[2]
    kind=node.get('type')
    if not {'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'integer':type(value)is int}.get(kind,False):fail('type')
    if 'enum' in node and value not in node['enum']:fail('enum')
    if kind=='object':
        if any(k not in value for k in node['required']):fail('required')
        if set(value)-set(node['properties']):fail('additionalProperties')
        for k,v in node['properties'].items():validate(value[k],v,(path+'/' if path else '')+k,root)
    elif kind=='array':
        if len(value)<node['minItems']:fail('minItems')
        if len(value)>node['maxItems']:fail('maxItems')
        for i,item in enumerate(value):validate(item,node['items'],(path+'/' if path else '')+str(i),root)
    elif kind=='string':
        if len(value)<node.get('minLength',0):fail('minLength')
        if 'maxLength' in node and len(value)>node['maxLength']:fail('maxLength')
        if node.get('pattern')==r'\S' and not value.strip():fail('pattern')
    elif kind=='integer':
        if value<node['minimum']:fail('minimum')
        if value>node['maximum']:fail('maximum')
