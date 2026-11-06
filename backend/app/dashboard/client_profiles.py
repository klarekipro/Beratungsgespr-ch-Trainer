"""Versioned author-controlled client dossiers; never derived from seller claims."""
import json
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .models import InputModel, Identifier, ShortText, Scenario

ROOT = Path(__file__).resolve().parents[3] / 'profiles'

class ProfileField(InputModel):
    label: str = Field(default="",max_length=240)
    status: Literal['known', 'customer_unknown', 'author_missing', 'undecided', 'refuses_to_disclose', 'not_applicable']
    value: str = Field(default='', max_length=3000)

    @model_validator(mode='after')
    def meaningful(self):
        if self.status == 'known' and not self.value:
            raise ValueError('Known values cannot be empty')
        if self.status == 'author_missing' and self.value:
            raise ValueError('Missing author data cannot assert a value')
        return self

class BasePersona(InputModel):
    id: Identifier
    version: int = Field(ge=1)
    name: ShortText
    approval: Literal['technical_draft', 'owner_approved'] = 'technical_draft'
    character: ShortText
    speech_style: ShortText
    stranger_attitude: ShortText
    doubt_behavior: ShortText
    question_style: ShortText
    decision_style: ShortText
    pressure_reaction: ShortText
    typical_expressions: list[ShortText] = Field(max_length=12)
    psychological_type: ShortText = "custom"
    repeat_question_reaction: ShortText = "Спокойно уточняет, что осталось непонятным."
    additional_behavior: str = Field(default="",max_length=2000)

class ProfileScenario(InputModel):
    id: Identifier
    version: int = Field(ge=1)
    persona_ids: list[Identifier] = Field(min_length=1, max_length=20)
    # Exact source card preserves facts, fact statuses, revision and outcomes.
    source_scenario: Scenario
    initial_situation: ShortText
    reason_fact_ids: list[Identifier]
    observation_fact_ids: list[Identifier]
    need_fact_ids: list[Identifier]
    financial_fact_ids: list[Identifier]
    timing_fact_ids: list[Identifier]
    open_questions: dict[Identifier, ProfileField] = Field(default_factory=dict, max_length=30)
    disclosure_conditions: dict[Identifier, Literal['available', 'after_needs', 'after_capabilities', 'owner_only']]
    critical_contradictions: list[Literal['equipment_is_customer_owned', 'industrial_gas_not_domestic_electric', 'no_confirmed_repair_price', 'no_confirmed_booking']]

    @model_validator(mode='after')
    def references(self):
        ids={f.id for f in self.source_scenario.facts}
        groups=[self.reason_fact_ids,self.observation_fact_ids,self.need_fact_ids,self.financial_fact_ids,self.timing_fact_ids]
        if any(not set(g)<=ids for g in groups) or set(self.disclosure_conditions)!=ids:
            raise ValueError('Every fact must have an explicit disclosure condition; references must exist')
        return self

class SessionModifiers(InputModel):
    version: int = Field(default=1, ge=1)
    mood: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))
    urgency: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))
    previous_conversation: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))
    compared_offers: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))
    trust_level: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))
    verified_experience: ProfileField = Field(default_factory=lambda: ProfileField(status='author_missing'))

class ClientProfile(InputModel):
    schema_version: Literal[1] = 1
    id: Identifier
    version: int = Field(ge=1)
    available: bool = True
    persona: BasePersona
    scenario: ProfileScenario
    modifiers: SessionModifiers

    @model_validator(mode='after')
    def binding(self):
        if self.persona.id not in self.scenario.persona_ids:
            raise ValueError('Scenario does not authorize this persona')
        return self

def load_profiles(directory=ROOT, overrides=None):
    """Resolved and validated at startup; snapshots persist with each conversation."""
    profiles=[]
    for path in sorted((directory/'clients').glob('*.json')):
        binding=json.loads(path.read_text())
        # IDs are validated before becoming filenames; paths cannot escape registry.
        from .models import Identifier as _Identifier
        from pydantic import TypeAdapter
        for field in ['persona_id','scenario_id']:
            TypeAdapter(_Identifier).validate_python(binding[field])
        persona=json.loads((directory/'personas'/f"{binding.pop('persona_id')}.json").read_text())
        scenario=json.loads((directory/'scenarios'/f"{binding.pop('scenario_id')}.json").read_text())
        profile=ClientProfile.model_validate({**binding,'persona':persona,'scenario':scenario}).model_dump()
        profiles.append(profile)
    if not profiles or len({p['id'] for p in profiles})!=len(profiles):
        raise ValueError('Client registry empty or contains duplicate IDs')
    registry={p['id']:p for p in profiles}
    if overrides is not None:
        for path in sorted(Path(overrides).glob('*.json')):
            p=ClientProfile.model_validate_json(path.read_text()).model_dump()
            if p['id'] in registry and p['version']<=registry[p['id']]['version']:
                raise ValueError('Local override must increase profile version')
            registry[p['id']]=p
    return list(registry.values())

def public_profile(p):
    s=p['scenario']['source_scenario'];persona=p['persona']
    return {'id':p['id'],'version':p['version'],'schema_version':p['schema_version'],
            'persona_id':persona['id'],'persona_version':persona['version'],'persona_name':persona['name'],
            'approval':persona['approval'],'scenario_id':s['id'],'scenario_version':p['scenario']['version'],
            'source_revision':s['revision'],'title':s['title'],'customer_name':s['customer_name'],
            'public_brief':s['public_brief'],'language':s['language']}
