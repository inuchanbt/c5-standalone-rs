"""Conservative per-function static stack estimates from ARM disassembly.

Sums downward SP adjustments across every path, so mutually exclusive paths
overestimate. This is not a whole-call-tree or interrupt stack bound.
"""
import re

def register_bytes(registers, floating=False):
    total=0
    for reg in registers.strip('{} ').split(','):
        reg=reg.strip()
        m=re.fullmatch(r'([rds])(\d+)-[rds](\d+)',reg)
        if m:total+=(int(m[3])-int(m[2])+1)*(8 if m[1]=='d' else 4)
        else:total+=8 if floating and reg.startswith('d') else 4
    return total

def estimate(disassembly):
    frames={};dynamic=[];function=None
    for line in disassembly.splitlines():
        m=re.match(r'^[0-9a-f]+ <(.+)>:$',line)
        if m:function=m[1];frames[function]=0;continue
        m=re.match(r'^\s*[0-9a-f]+:[^\t]*\t(.+)$',line)
        if not m or function is None:continue
        instruction=m[1].split('@')[0].strip()
        op=instruction.split()[0]
        args=instruction[len(op):].strip()
        if op in ('push','push.w','vpush'):
            frames[function]+=register_bytes(args,op=='vpush')
        elif op in ('stmdb','stmdb.w') and args.startswith('sp!'):
            frames[function]+=register_bytes(args.split(',',1)[1])
        elif op in ('sub','sub.w') and re.match(r'sp,',args):
            amount=re.fullmatch(r'sp,\s*(?:sp,\s*)?#(0x[0-9a-f]+|\d+)',args)
            if amount:frames[function]+=int(amount[1],0)
            else:dynamic.append((function,instruction))
        elif op.startswith(('str','vstr')):
            amount=re.search(r'\[sp,\s*#-(0x[0-9a-f]+|\d+)\]!',args)
            if amount:frames[function]+=int(amount[1],0)
    if not frames:raise ValueError('No functions found in ARM disassembly')
    if dynamic:raise ValueError('Unrecognized dynamic stack adjustment: '+repr(dynamic))
    return frames
