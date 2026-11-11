"""Private receipt for a scoped code installation; independent of the checkout's Git HEAD."""
import hashlib
import json
from pathlib import Path
import re

from prepare_code_release import code_path, read_inside

RELATIVE_PATH=Path('runtime/deployed-release.local.json')

def digest(payload):return hashlib.sha256(payload).hexdigest() if payload is not None else None

def read(app):
    app=app.resolve();path=app/RELATIVE_PATH
    if path.resolve()!=path:raise ValueError('El comprobante no puede ser un enlace.')
    if not path.exists():return None
    if not path.is_file() or path.stat().st_size>2_000_000:raise ValueError('Comprobante no válido.')
    return path.read_bytes()

def create(commit,base,git_head,scope,payloads,originals,previous,plan_id,operation_id):
    return {'schemaVersion':1,'kind':'scoped-code-release','commit':commit,'scopeFromCommit':base,
        'gitHeadAtInstall':git_head,'scope':sorted(scope),
        'codeHashes':{n:digest(p) for n,p in sorted(payloads.items())},
        'preservedHashes':{n:digest(originals[n]) for n in sorted(payloads) if n not in scope},
        'previousReceiptSha256':digest(previous),'planId':plan_id,'operationId':operation_id}

def validate(data):
    if not isinstance(data,dict) or data.get('schemaVersion')!=1 or data.get('kind')!='scoped-code-release':
        raise ValueError('Formato de comprobante no admitido.')
    for key in ['commit','gitHeadAtInstall']:
        if not isinstance(data.get(key),str) or not re.fullmatch('[0-9a-f]{40}',data[key]):raise ValueError('Identidad inválida.')
    base=data.get('scopeFromCommit')
    if base is not None and (not isinstance(base,str) or not re.fullmatch('[0-9a-f]{40}',base)):raise ValueError('Base inválida.')
    hashes=data.get('codeHashes');preserved=data.get('preservedHashes');scope=data.get('scope')
    if not isinstance(hashes,dict) or not isinstance(preserved,dict) or not isinstance(scope,list) or not hashes:
        raise ValueError('Inventario inválido.')
    if any(not isinstance(n,str) or not code_path(n) for n in list(hashes)+list(preserved)+scope):raise ValueError('Ruta no admitida.')
    if len({n.casefold() for n in hashes})!=len(hashes) or len(set(scope))!=len(scope):raise ValueError('Inventario ambiguo.')
    if set(scope)&set(preserved) or set(scope)|set(preserved)!=set(hashes):raise ValueError('Alcance incompleto.')
    if any(not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h) for h in hashes.values()):raise ValueError('Huella inválida.')
    if any(h is not None and (not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h)) for h in preserved.values()):raise ValueError('Huella preservada inválida.')
    return data

def status(app):
    try:
        raw=read(app)
        if raw is None:return {'status':'UNRECORDED','scope':'No private deployment receipt; consult the existing deployment journal.'}
        data=validate(json.loads(raw))
        current={n:digest(read_inside(app,n)) for n in data['codeHashes']}
        changed=[n for n in data['scope'] if current[n]!=data['codeHashes'][n]]
        preserved=[n for n,h in data['preservedHashes'].items() if current[n]!=h]
        return {'status':'DRIFT' if changed or preserved else 'VERIFIED_SCOPED_RELEASE','commit':data['commit'],
            'scopeFromCommit':data['scopeFromCommit'],'gitHeadAtInstall':data['gitHeadAtInstall'],
            'scopeFiles':len(data['scope']),'preservedStates':len(data['preservedHashes']),
            'changedScopePaths':changed,'changedPreservedPaths':preserved,
            'fullPackageMatches':current==data['codeHashes'],'coversOperationalRootFiles':False,
            'receiptSha256':digest(raw)}
    except (ValueError,TypeError,OSError):return {'status':'INVALID_RECEIPT'}
