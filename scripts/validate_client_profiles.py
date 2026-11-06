"""Validate author files locally without API calls or printing dossier contents."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.dashboard.client_profiles import load_profiles, ClientProfile
import json
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    if '--schema' in sys.argv:
        print(json.dumps(ClientProfile.model_json_schema(),ensure_ascii=False,indent=2))
    else:
        profiles=load_profiles(overrides=root/'runtime/client_profiles')
        for p in profiles:print(p['id'], 'v'+str(p['version']),p['persona']['approval'])
