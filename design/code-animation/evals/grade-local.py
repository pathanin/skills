# Apply a case's tool_used and regex graders to a run-local.sh trace, and print the final reply for the llm graders (judge those by reading it).
# usage: python3 evals/grade-local.py <case> [out-dir]
import json, re, sys, os, glob, tempfile
here=os.path.dirname(os.path.abspath(__file__)); case=sys.argv[1]
W=os.path.join(sys.argv[2] if len(sys.argv)>2 else os.path.join(os.environ.get('TMPDIR',tempfile.gettempdir()),'code-animation-evals'),case)
tools=[]; texts=[]; end=None
for l in open(os.path.join(W,'trace.jsonl')):
    try: e=json.loads(l)
    except ValueError: continue
    if e.get('type')=='assistant':
        for c in e['message'].get('content',[]):
            if c.get('type')=='tool_use': tools.append((c['name'],c['input']))
            if c.get('type')=='text': texts.append(c['text'])
    if e.get('type')=='result': end=e
def front(p):
    s=open(p).read(); m=re.match(r'---\n(.*?)\n---\n?(.*)',s,re.S); meta={}; cur=None
    for line in m.group(1).split('\n'):
        if re.match(r'^\s+\w+:',line) and cur: k,v=line.strip().split(':',1); meta[cur+'.'+k]=v.strip().strip("'\"")
        else: k,v=line.split(':',1); v=v.strip().strip("'\""); meta[k]=v; cur=k if v=='' else None
    return meta,m.group(2).strip()
for g in sorted(glob.glob(os.path.join(here,case,'graders','*.md'))):
    meta,body=front(g); name=os.path.basename(g)[:-3]
    if meta['type']=='tool_used':
        pat=re.compile(meta.get('input_match','.'))
        ok=any(n==meta['tool'] and pat.search(i.get('command','') if n=='Bash' else json.dumps(i)) for n,i in tools); print(('PASS ' if ok else 'FAIL ')+name)
    elif meta['type']=='regex':
        p=os.path.join(W,'work',meta['target.path']); fl=re.I if 'i' in meta.get('flags','') else 0
        ok=os.path.exists(p) and re.search(meta['pattern'],open(p).read(),fl|re.M) is not None; print(('PASS ' if ok else 'FAIL ')+name+('' if os.path.exists(p) else ' (no file)'))
    else: print('JUDGE '+name+': '+' '.join(body.split())[:300])
if end: print('turns %s, cost $%.2f, %s'%(end.get('num_turns'),end.get('total_cost_usd',0),end.get('subtype')))
print('--- final reply ---'); print(texts[-1] if texts else '(none)')
