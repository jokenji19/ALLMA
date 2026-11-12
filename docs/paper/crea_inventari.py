"""Create traceable, privacy-conscious inventories for the ALLMA study.

Run from the project root. The only external input is the local JUnit evidence;
raw logs, user chats, model weights and per-case parameter values are excluded.
"""
from pathlib import Path
import ast
import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
EVIDENCE=ROOT.parent/'analisi/2026-10-29/dialogo-contestuale'
BASE='5baf2b37ee99aa2090be63ebbe8ba4e93e6aa904'
SNAPSHOT='c95708470db236b49810037bee343839ea5c91c3'

def git(*args):
    return subprocess.check_output(['/usr/bin/git',*args],cwd=ROOT,text=True)

def write_csv(name,fields,rows):
    with (OUT/name).open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def main():
    paths=git('ls-tree','-r','--name-only',SNAPSHOT,'allma_model').splitlines()
    modules=[]
    for name in paths:
        path=ROOT/name
        if not name.endswith('.py') or not path.is_file():continue
        raw=path.read_bytes();item={'file':name,'sha256':hashlib.sha256(raw).hexdigest(),
            'righe':len(raw.splitlines()),'classi':0,'funzioni':0,'stato':'presenza statica; esecuzione non implicata'}
        try:
            tree=ast.parse(raw,filename=name)
            item['classi']=sum(isinstance(n,ast.ClassDef) for n in ast.walk(tree))
            item['funzioni']=sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for n in ast.walk(tree))
        except (SyntaxError,UnicodeDecodeError):item['stato']='analisi sintattica non disponibile'
        modules.append(item)
    write_csv('inventario_moduli.csv',['file','sha256','righe','classi','funzioni','stato'],modules)
    diff=git('diff','--name-status','--no-renames',BASE,SNAPSHOT).splitlines();changes=[]
    for line in diff:
        status,name=line.split('\t',1)
        changes.append({'stato':status,'file':name})
    write_csv('inventario_modifiche.csv',['stato','file'],changes)
    docs=[]
    for path in sorted((ROOT/'docs').glob('*.md')):
        raw=path.read_bytes();text=raw.decode('utf-8',errors='replace')
        heads=[re.sub(r'^#+\s*','',line).strip() for line in text.splitlines() if line.startswith(('## ','### '))]
        docs.append({'file':'docs/'+path.name,'sha256':hashlib.sha256(raw).hexdigest(),
            'sezioni':' | '.join(heads),'url':'https://github.com/jokenji19/ALLMA/blob/'+SNAPSHOT+'/docs/'+path.name})
    write_csv('inventario_documenti.csv',['file','sha256','sezioni','url'],docs)
    cases={}
    paths=sorted(EVIDENCE.glob('reg-*.xml'))+sorted(EVIDENCE.glob('legacy-*.xml'))+[EVIDENCE/'checkin-telemetry-final.xml']
    for path in paths:
        for case in ET.parse(path).iter('testcase'):
            classname=case.get('classname','');name=case.get('name','');key=(classname,name)
            outcome='fallito' if case.find('failure') is not None or case.find('error') is not None else 'saltato' if case.find('skipped') is not None else 'superato'
            # Parameter values may contain text. Keep stable identifiers only.
            cases[key]={'gruppo':classname,'test':name.split('[',1)[0],
                'id_caso':hashlib.sha256((classname+'::'+name).encode()).hexdigest()[:12],
                'esito':outcome}
    rows=sorted(cases.values(),key=lambda row:(row['gruppo'],row['test'],row['id_caso']))
    assert len(rows)==3314 and sum(row['esito']=='superato' for row in rows)==3299
    assert sum(row['esito']=='saltato' for row in rows)==15 and not any(row['esito']=='fallito' for row in rows)
    write_csv('inventario_test.csv',['gruppo','test','id_caso','esito'],rows)
    info={'baseline_commit':BASE,'release_tag_commit':'a3cfc33f4bbc4688bd7a3ad0e252a5a904707094',
          'repository_snapshot':SNAPSHOT,'modules':len(modules),'changes':len(changes),
          'documents':len(docs),'tests':len(rows),'passed':3299,'skipped':15,'failed':0,
          'scope':'Static inventory; no raw user chat, logs or test parameter values.'}
    (OUT/'inventari_manifest.json').write_text(json.dumps(info,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(info,indent=2))

if __name__=='__main__':main()
