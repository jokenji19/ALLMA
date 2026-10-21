"""Offline, bounded test processes with complete collection and durable reports."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def worker(args):
    os.chdir(ROOT)
    sys.path.insert(0,str(ROOT))
    connect,resolve=socket.socket.connect,socket.getaddrinfo
    allowed={None,'','localhost','127.0.0.1','::1','0.0.0.0'}
    def offline_connect(sock,address):
        if isinstance(address,tuple) and address[0] not in allowed:
            raise OSError('External network disabled during tests')
        return connect(sock,address)
    def offline_resolve(host,*values,**options):
        if host not in allowed: raise OSError('External DNS disabled during tests')
        return resolve(host,*values,**options)
    socket.socket.connect,socket.getaddrinfo=offline_connect,offline_resolve
    selected=set(json.loads(args.select.read_text())) if args.select else None
    import pytest
    class Selection:
        def pytest_collection_modifyitems(self,session,config,items):
            if selected is None: return
            dropped=[i for i in items if i.nodeid not in selected]
            items[:]=[i for i in items if i.nodeid in selected]
            config.hook.pytest_deselected(items=dropped)
        def pytest_collection_finish(self,session):
            if args.collect:
                args.collect.write_text(json.dumps([i.nodeid for i in session.items]))
    options=[*args.paths,'-q','--no-cov','-o','addopts=']
    if args.collect: options+=['--collect-only']
    if args.xml: options+=['--junitxml='+str(args.xml)]
    return int(pytest.main(options,plugins=[Selection()]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths',nargs='*',default=['allma_model/tests','tests/regression'])
    parser.add_argument('--output',type=Path,default=ROOT/'test-results')
    parser.add_argument('--batch-size',type=int,default=12)
    parser.add_argument('--timeout',type=int,default=180)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--select',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--collect',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--xml',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker: return worker(args)
    if args.batch_size<1 or args.timeout<1: parser.error('Positive batch size and timeout required')
    args.output=args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,KIVY_NO_ARGS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
             TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    def run(name,extra):
        with (args.output/(name+'.log')).open('w') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',
                *args.paths,*extra],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try: return process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
                return 124
    collection=args.output/'nodes.json'
    if run('collection',['--collect',str(collection)])!=0:
        print('Test collection failed; see '+str(args.output/'collection.log'))
        return 1
    nodes=json.loads(collection.read_text())
    results=[]
    for start in range(0,len(nodes),args.batch_size):
        name=f'batch-{start//args.batch_size:03}'
        selection=args.output/(name+'.json')
        selection.write_text(json.dumps(nodes[start:start+args.batch_size]))
        xml=args.output/(name+'.xml')
        code=run(name,['--select',str(selection),'--xml',str(xml)])
        cases=[]
        if xml.exists():
            for test in ET.parse(xml).iter('testcase'):
                outcome=next((n for n in test if n.tag in ('failure','error','skipped')),None)
                cases.append({'class':test.get('classname'),'name':test.get('name'),
                    'status':outcome.tag if outcome is not None else 'passed',
                    'detail':outcome.get('message','') if outcome is not None else ''})
        results.append({'batch':name,'exit_code':code,'cases':cases})
        (args.output/'progress.json').write_text(json.dumps(results,indent=2))
        print(f'{min(start+args.batch_size,len(nodes))}/{len(nodes)} cases; {name}: {code}',flush=True)
    counts=Counter(c['status'] for r in results for c in r['cases'])
    complete=sum(counts.values())==len(nodes)
    passed=complete and all(r['exit_code']==0 for r in results)
    summary={'collected':len(nodes),'counts':dict(counts),'complete':complete,'successful':passed,
        'scope':'Offline source tests, synthetic data; no claim of Android or model quality',
        'failures':[c for r in results for c in r['cases'] if c['status'] in ('failure','error')]}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
