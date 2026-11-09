"""Reviewed A14 display translations and training snapshots for NEW sessions only.

Frozen source equality (including revision) is intentional: IDs or unchanged
names alone never authorize substituting a mentor's edited material.
"""
from copy import deepcopy
import json
from pathlib import Path
from .models import Company, Scenario

ROOT = Path(__file__).resolve().parents[3] / 'materials'
SOURCE = json.loads((ROOT / 'source.ru.json').read_text())
TRANSLATIONS = {lang: json.loads((ROOT / f'{lang}.json').read_text()) for lang in ('de', 'en')}


def builtin_scenario(record):
    return next((s for s in SOURCE['scenarios'] if Scenario.model_validate(record).model_dump() == Scenario.model_validate(s).model_dump()), None)


def localized_scenario(record, language):
    result = deepcopy(record)
    if language in TRANSLATIONS and builtin_scenario(record):
        translated = next(s for s in TRANSLATIONS[language]['scenarios'] if s['id'] == record['id'])
        result.update(deepcopy(translated))
    return result


def localized_company(record, language):
    if language in TRANSLATIONS and record == Company.model_validate(SOURCE['company']).model_dump():
        return deepcopy(TRANSLATIONS[language]['company'])
    return deepcopy(record)


def persona_label(profile, language):
    persona = profile['persona']
    if language in TRANSLATIONS and persona == SOURCE['personas'].get(profile['id']):
        return TRANSLATIONS[language]['persona_labels'].get(persona['id'], persona['name'])
    return persona['name']


def public_materials(store, profiles, language):
    return {
        'version': 1,
        'company': localized_company(store.get_company(), language),
        'scenarios': {s['id']: {**{k: localized_scenario(s, language)[k]
                                  for k in ('title', 'customer_name', 'public_brief')},
                              'training_languages': ['de', 'en', 'ru'] if builtin_scenario(s) else [s['language']]}
                      for s in store.list_scenarios()},
        'persona_labels': {p['id']: persona_label(p, language) for p in profiles},
    }
