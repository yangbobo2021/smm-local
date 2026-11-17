# SPDX-License-Identifier: Apache-2.0
"""Export only synthetic reader SQL from a generated fixture's server log."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def audit(path):
    roles={'source_reader','replacement_reader','limited_reader'}
    header=re.compile(r'^\S+ \S+ \S+ (\w+)@\S+ \[(\d+)\] LOG:  statement: (.*)$')
    commands=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        match=header.match(line)
        if match:
            role,pid,sql=match.groups()
            if role in roles:commands.append([pid,sql])
            else:commands.append([None,''])
        elif line.startswith('\t') and commands:commands[-1][1]+='\n'+line
    state={};counts=Counter();samples={};errors=[]
    for pid,sql in commands:
        if pid is None:continue
        kind=sql.strip().split(None,1)[0].rstrip(';').upper()
        if kind=='BEGIN':
            assert sql.strip()=='BEGIN READ ONLY;', 'reader transaction lacks explicit READ ONLY'
            state[pid]=True
        elif kind in {'SELECT','COPY','SET'}:
            if not state.get(pid):errors.append({'pid_alias':len(errors),'kind':kind})
        elif kind in {'COMMIT','ROLLBACK'}:state[pid]=False
        else:raise AssertionError('unexpected reader command: '+kind)
        counts[kind]+=1
        samples.setdefault(kind,sql)
    assert not errors,errors
    assert counts['SELECT']>0 and counts['COPY']>0 and counts['BEGIN']>0
    return {'status':'passed','scope':'all source_reader/replacement_reader/limited_reader statements in this isolated cluster log',
            'query_outside_explicit_readonly_transaction':0,'counts':dict(counts),'first_example_by_kind':samples,
            'note':'Fixture administrator statements and connection metadata are excluded. Failed permission probes may end by connection close.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture-log',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('output must be new')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(audit(a.fixture_log),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
