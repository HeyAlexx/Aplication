"""Reject operational data, generated files and high-confidence credential signatures.

Reads Git blobs, never emits matched values and does not scan or rewrite history.
This bounded prevention policy is not a comprehensive secret/DLP scanner.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

DOCUMENTS={'data/.htaccess','data/README.md','backups/.htaccess','backups/README.md'}
GENERATED={'outputs','runtime','node_modules','__pycache__','.venv','venv','.git'}
SIGNATURES={
    'private-key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'password-hash':re.compile(rb'\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}'),
    'github-token':re.compile(rb'gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,}'),
    'aws-access-key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
}
TIMING_DUMMY_SHA256='3358081a1812470ea6e469d7b51f2d2b333a1007adcaf86686bc961fae8bc405'

def path_rules(name):
    p=PurePosixPath(name);parts=[x.casefold() for x in p.parts]
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts:
        return ['unsafe-path']
    if name in DOCUMENTS:return []
    rules=[]
    if any(x in GENERATED for x in parts):rules.append('generated-artifact')
    if parts[0] in {'data','backups'}:rules.append('operational-data')
    if '.local.' in p.name.casefold() or p.name.casefold().startswith('.env') and not p.name.casefold().endswith('.example'):
        rules.append('local-configuration')
    if parts[0]=='config' and name!='config/anime-sync.example.json':rules.append('operational-configuration')
    if p.suffix.casefold() in {'.zip','.7z','.sqlite','.sqlite3','.db','.xlsx','.xlsm'}:rules.append('operational-or-generated-binary')
    return rules

def findings(name,payload):
    result=[{'path':name,'rule':rule} for rule in path_rules(name)]
    for rule,pattern in SIGNATURES.items():
        for match in pattern.finditer(payload):
            # Reviewed public timing sentinel, not an account hash. No path-wide exemption.
            start=payload.rfind(b'\n',0,match.start())+1
            end=payload.find(b'\n',match.end())
            if (rule=='password-hash' and name=='api/services/CredentialService.php'
                    and hashlib.sha256(match.group()).hexdigest()==TIMING_DUMMY_SHA256
                    and payload[start:match.start()].strip()==b"private const DUMMY = '"
                    and payload[match.end():end if end!=-1 else len(payload)].strip()==b"';"):
                continue
            result.append({'path':name,'rule':rule});break
    return result

def reject_payload(name,payload):
    issues=findings(name,payload)
    if issues:raise ValueError('Contenido no publicable: '+json.dumps(issues,ensure_ascii=True))

def git(root,*args):
    return subprocess.check_output(['git','--no-optional-locks','-c','safe.directory='+root.as_posix(),'-C',str(root),*args],stderr=subprocess.PIPE)

def scan(root,commit=None,index=False):
    if index:
        entries=git(root,'ls-files','--stage','-z').split(b'\0')
    else:
        entries=git(root,'ls-tree','-rz',commit or 'HEAD').split(b'\0')
    issues=[];seen=set();count=0
    for entry in filter(None,entries):
        metadata,raw_name=entry.split(b'\t',1);fields=metadata.decode().split();name=raw_name.decode('utf-8')
        mode=fields[0];oid=fields[1] if index else fields[2]
        if mode not in {'100644','100755'} or (index and fields[2]!='0'):
            issues.append({'path':name,'rule':'unsupported-git-entry'});continue
        if name.casefold() in seen:issues.append({'path':name,'rule':'case-collision'})
        seen.add(name.casefold());count+=1
        rules=path_rules(name)
        if rules:
            issues.extend({'path':name,'rule':rule} for rule in rules)
            continue  # Do not inspect operational payloads or expose their values.
        issues.extend(findings(name,git(root,'cat-file','blob',oid)))
    return {'status':'FAILED' if issues else 'PASSED','source':'index' if index else commit or 'HEAD',
        'trackedFiles':count,'findings':issues,'matchedValuesEmitted':False,'historyScanned':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    choice=parser.add_mutually_exclusive_group();choice.add_argument('--commit');choice.add_argument('--index',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=scan(args.root.resolve(),args.commit,args.index)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    # Summaries contain counts only; paths/rules are available in the optional private report.
    print(json.dumps({k:result[k] for k in ['status','source','trackedFiles','matchedValuesEmitted','historyScanned']}|{'violations':len(result['findings'])}))
    return 1 if result['findings'] else 0

if __name__=='__main__':raise SystemExit(main())
