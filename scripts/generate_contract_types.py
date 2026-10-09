"""Frontend wire types from the actual Pydantic contract; no new dependency."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.contracts import AnalysisResult, PredictResponse, ConfigurationResponse


def ts_type(schema):
    if '$ref' in schema: return schema['$ref'].rsplit('/',1)[-1]
    if 'const' in schema: return json.dumps(schema['const'])
    if 'enum' in schema: return ' | '.join(json.dumps(value) for value in schema['enum'])
    if 'anyOf' in schema: return ' | '.join(dict.fromkeys(ts_type(value) for value in schema['anyOf']))
    kind=schema.get('type')
    if kind in {'integer','number'}: return 'number'
    if kind in {'string','boolean','null'}: return kind
    if kind=='array': return 'Array<'+ts_type(schema['items'])+'>'
    if kind=='object' and isinstance(schema.get('additionalProperties'),dict):
        return 'Record<string, '+ts_type(schema['additionalProperties'])+'>'
    raise ValueError('Unsupported contract type; generator must be updated explicitly')


def render():
    models={}
    for model in (AnalysisResult,PredictResponse,ConfigurationResponse):
        schema=model.model_json_schema(mode='serialization')
        for name,definition in schema.pop('$defs',{}).items():
            if name in models and models[name]!=definition: raise ValueError('Conflicting shared definition')
            models[name]=definition
        models[model.__name__]=schema
    out=['// Contract types from api/contracts.py; refresh with scripts/generate_contract_types.py.',
         '// Successful wire responses serialize defaults, so every declared field is present.','']
    for name,schema in sorted(models.items()):
        out.append('export interface '+name+' {')
        for field,definition in schema['properties'].items():
            out.append('  '+field+': '+ts_type(definition)+';')
        out.extend(['}',''])
    return '\n'.join(out)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=ROOT/'web/src/lib/contract.ts'
    expected=render()
    if args.check:
        if not path.exists() or path.read_text()!=expected:
            raise SystemExit('Frontend contract drift: run scripts/generate_contract_types.py')
    else:
        path.write_text(expected)
