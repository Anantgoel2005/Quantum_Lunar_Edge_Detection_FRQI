"""Source-derived circuit atlas and independent state/probability checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/circuit_showcase'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def operations(qc):
    return [{'name':i.operation.name,'qubits':[qc.find_bit(q).index for q in i.qubits],
             'clbits':[qc.find_bit(c).index for c in i.clbits]}
            for i in qc.data if i.operation.name!='barrier']


def worker(encoding):
    repo=ROOT.parent/('Quantum_Lunar_Edge_Detection_'+encoding)
    sys.path.insert(0,str(repo))
    from qiskit import transpile,qasm3
    from qiskit.quantum_info import Statevector
    if encoding=='QPIE':
        from quantum.qhed_circuit import build_qhed_circuit as build
    else:
        from quantum.variant_circuit import build_variant_circuit as build,ENCODING
        assert ENCODING==encoding
    image=np.array(Image.open(ROOT/'results/real_case/row0/input.png'),dtype=float)
    image=np.pad(image,((1,16),(1,16)),mode='edge')[:16,:16]
    if encoding=='QPIE':image-=image.min()
    n=256;theta=image/255*np.pi/2;levels=np.floor(image/255*15).astype(int)
    if encoding=='QPIE':
        norm=float(np.linalg.norm(image));initial=(image/norm).ravel().astype(complex)
    elif encoding=='FRQI':initial=np.concatenate([np.cos(theta).ravel(),np.sin(theta).ravel()]).astype(complex)/16
    else:
        initial=np.zeros(4096,complex);initial[levels.ravel()*n+np.arange(n)]=1/16
    records=[];max_state=max_born=0.
    for direction in ('horizontal','vertical'):
        for offset in (0,1):
            qc,qubits,selected=build(image,direction,offset)
            assert qubits=={'QPIE':8,'FRQI':9,'NEQR':12}[encoding]
            np.testing.assert_allclose(qc.data[0].operation.params,initial,atol=1e-14,rtol=1e-14)
            ops=operations(qc)
            assert [o['qubits'][0] for o in ops if o['name']=='h']==[0 if direction=='horizontal' else 4]
            assert [(o['qubits'],o['clbits']) for o in ops if o['name']=='measure']==[([i],[i]) for i in range(qubits)]
            expected=initial.reshape(-1,16,16).copy();axis=2 if direction=='horizontal' else 1
            if offset:expected=np.roll(expected,1,axis=axis)
            moved=np.moveaxis(expected,axis,-1);a=moved[...,::2].copy();b=moved[...,1::2].copy()
            moved[...,::2]=(a+b)/np.sqrt(2);moved[...,1::2]=(a-b)/np.sqrt(2)
            expected=np.moveaxis(moved,-1,axis).ravel()
            state=Statevector.from_instruction(qc.remove_final_measurements(inplace=False))
            error=float(np.max(np.abs(state.data-expected)));max_state=max(max_state,error)
            np.testing.assert_allclose(state.data,expected,atol=1e-12,rtol=1e-12)
            probabilities=(np.abs(state.data.reshape(-1,16,16))**2).sum(axis=0)
            values=np.roll(image,offset,axis=1 if direction=='horizontal' else 0)
            aa=np.moveaxis(values,1 if direction=='horizontal' else 0,-1)[...,::2]
            bb=np.moveaxis(values,1 if direction=='horizontal' else 0,-1)[...,1::2]
            if encoding=='QPIE':law=(aa-bb)**2/(2*norm**2)
            elif encoding=='FRQI':law=(1-np.cos((aa-bb)/255*np.pi/2))/n
            else:law=(np.floor(aa/255*15)!=np.floor(bb/255*15))/n
            accepted=np.moveaxis(probabilities,1 if direction=='horizontal' else 0,-1)[...,1::2]
            born_error=float(np.max(np.abs(accepted-law)));max_born=max(max_born,born_error)
            np.testing.assert_allclose(accepted,law,atol=1e-14,rtol=1e-12)
            stem=f'{encoding.lower()}_{direction}_{offset}'
            (OUT/(stem+'.txt')).write_text(str(qc.draw(output='text',fold=120))+'\n',encoding='utf8')
            records.append({'id':stem,'encoding':encoding,'direction':direction,'offset':offset,
                            'qubits':qubits,'position_qubits':8,'brightness_qubits':qubits-8,
                            'h_target':selected,'operations':ops,'operation_counts':dict(qc.count_ops()),
                            'initial_state_sha256':hashlib.sha256(initial.tobytes()).hexdigest(),
                            'state_error':error,'born_law_error':born_error})
            if direction=='horizontal' and offset==1:
                compiled=transpile(qc,basis_gates=['u','cx'],optimization_level=0,seed_transpiler=42)
                compiled_state=Statevector.from_instruction(compiled.remove_final_measurements(inplace=False))
                fidelity=float(abs(np.vdot(state.data,compiled_state.data))**2)
                assert np.isclose(fidelity,1.,atol=1e-10)
                (OUT/(encoding.lower()+'_primitive.qasm')).write_text(qasm3.dumps(compiled),encoding='utf8')
                records[-1]['primitive_example']={'counts':dict(compiled.count_ops()),'depth':compiled.depth(),
                                                 'state_fidelity':fidelity,'basis':'u,cx plus reset/measure/barrier; optimization_level0'}
    if encoding=='QPIE':
        from quantum.neqr_encoder import neqr_encode_simplified
        from quantum.qpie_encoder import qpie_encode,qpie_encode_with_ancilla
        sample=np.array([[0,85],[170,255]],float)
        legacy,np_,ni=neqr_encode_simplified(sample,2)
        legacy_state=Statevector.from_instruction(legacy).data;expected=np.zeros(16)
        for pos,value in enumerate([0,1,2,3]):expected[(pos<<2)+value]=.5
        np.testing.assert_allclose(legacy_state,expected,atol=1e-12)
        (OUT/'legacy_explicit_neqr.txt').write_text(str(legacy.draw(output='text',fold=100))+'\n',encoding='utf8')
        qpie,nn=qpie_encode(sample);ancilla,npos,ancilla_index=qpie_encode_with_ancilla(sample)
        astate=Statevector.from_instruction(ancilla).data
        np.testing.assert_allclose(astate[1::2],0,atol=1e-14)
        np.testing.assert_allclose(astate[::2],Statevector.from_instruction(qpie).data,atol=1e-14)
        write(OUT/'legacy_helpers.json',{'explicit_neqr_2x2_2bit':{'qubits':legacy.num_qubits,'position_qubits':np_,'intensity_qubits':ni,
              'operations':operations(legacy),'counts':dict(legacy.count_ops()),'state_verified':True},
              'qpie_2x2_ancilla_helper':{'qubits':ancilla.num_qubits,'position_qubits':npos,'ancilla_index':ancilla_index,
                                       'ancilla_is_zero':True,'state_verified':True},'used_by_live_apps':False})
    builder='quantum/qhed_circuit.py' if encoding=='QPIE' else 'quantum/variant_circuit.py'
    write(OUT/(encoding.lower()+'.json'),{'encoding':encoding,'source':str((repo/builder).relative_to(ROOT.parent)),
          'source_sha256':sha(repo/builder),'full_image_sha256':sha(repo/'quantum/full_image.py'),
          'max_state_error':max_state,'max_born_error':max_born,'records':records})
    print(encoding+' four circuits and state laws verified',flush=True)


def draw(axis,record):
    from matplotlib.patches import Rectangle,Circle
    n=record['qubits'];axis.set_xlim(-2.1,8.5);axis.set_ylim(n-.2,-1.4);axis.axis('off')
    for q in range(n):
        axis.plot([-.3,8],[q,q],color='#94a3b8',linewidth=1,zorder=0)
        role=f'col bit {q}' if q<4 else f'row bit {q-4}' if q<8 else 'brightness angle' if n==9 else f'brightness bit {q-8}'
        axis.text(-.45,q,f'q{q} · {role}',ha='right',va='center',fontsize=10)
    if n>8:axis.axhline(7.5,xmin=0,xmax=1,linestyle=':',color='#cbd5e1',linewidth=1)
    axis.add_patch(Rectangle((.1,-.35),1.3,n-.3,facecolor='#eff6ff',edgecolor='#2563eb'))
    axis.text(.75,(n-1)/2,record['encoding']+'\nstate\npreparation',ha='center',va='center',fontsize=11,color='#1d4ed8')
    nonterminal=[o for o in record['operations'] if o['name'] not in ('initialize','measure')]
    for j,o in enumerate(nonterminal):
        x=2.2+j*.85
        if o['name'] in ('cx','ccx','mcx'):
            controls=o['qubits'][:-1];target=o['qubits'][-1]
            axis.plot([x,x],[min(o['qubits']),max(o['qubits'])],color='#334155')
            axis.scatter([x]*len(controls),controls,color='#334155',s=24,zorder=3)
            axis.add_patch(Circle((x,target),.12,edgecolor='#334155',facecolor='white',zorder=4))
            axis.plot([x-.09,x+.09],[target,target],color='#334155',zorder=5)
            axis.plot([x,x],[target-.09,target+.09],color='#334155',zorder=5)
        else:
            target=o['qubits'][0];color='#fef3c7' if o['name']=='h' else '#f1f5f9'
            axis.add_patch(Rectangle((x-.2,target-.23),.4,.46,facecolor=color,edgecolor='#334155',zorder=4))
            axis.text(x,target,o['name'].upper(),ha='center',va='center',fontsize=11,zorder=5)
    for q in range(n):
        axis.add_patch(Rectangle((7.3,q-.23),.5,.46,facecolor='#ecfdf5',edgecolor='#047857'))
        axis.text(7.55,q,'M',ha='center',va='center',fontsize=10,color='#047857')
    axis.text(7.55,n-.4,'qᵢ → cᵢ',ha='center',va='top',fontsize=10)
    axis.set_title(f"{record['encoding']} · {record['direction']} · pair offset {record['offset']} · {n} qubits",loc='left',fontsize=13,fontweight='bold',pad=14)


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    OUT.mkdir(parents=True,exist_ok=True)
    for encoding in ('QPIE','FRQI','NEQR'):
        subprocess.run([sys.executable,str(Path(__file__)),'--worker',encoding],cwd=ROOT,check=True)
    records=[]
    for encoding in ('QPIE','FRQI','NEQR'):
        records+=json.loads((OUT/(encoding.lower()+'.json')).read_text())['records']
    for r in records:
        fig,axis=plt.subplots(figsize=(13,r['qubits']*.38+1.4),layout='constrained');draw(axis,r)
        fig.savefig(OUT/(r['id']+'.svg'));plt.close(fig)
    selected=[r for r in records if r['direction']=='horizontal' and r['offset']==1]
    fig,axes=plt.subplots(3,1,figsize=(14,15),layout='constrained')
    for ax,r in zip(axes,selected):draw(ax,r)
    fig.suptitle('The three live quantum edge circuits · actual 16×16-block gate topology',fontweight='bold',fontsize=16)
    fig.supxlabel('Position q0–q3: columns; q4–q7: rows. The offset-1 carry gates precede H. M: computational-basis measurement.',fontsize=11)
    fig.savefig(OUT/'circuits_overview.png',dpi=150);fig.savefig(OUT/'circuits_overview.pdf');plt.close(fig)
    verification={'status':'passed','live_circuit_variants':len(records),'qubits':{'QPIE':8,'FRQI':9,'NEQR':12},
                  'analytic_preparation_and_full_state_checks':12,'analytic_born_law_checks':12,'compiled_primitive_equivalence_checks':3,
                  'legacy_helper_state_checks':2,'max_state_error':max(r['state_error'] for r in records),
                  'max_born_error':max(r['born_law_error'] for r in records),'generator_sha256':sha(__file__),
                  'diagram_semantics':'Native Initialize is displayed as one preparation block; terminal measurements grouped in one column. Native gates and register order come from Qiskit builders.',
                  'source_files_unchanged':True}
    for enc in ('QPIE','FRQI','NEQR'):
        data=json.loads((OUT/(enc.lower()+'.json')).read_text())
        assert sha(ROOT.parent/data['source'])==data['source_sha256']
        repo=ROOT.parent/('Quantum_Lunar_Edge_Detection_'+enc)
        assert sha(repo/'quantum/full_image.py')==data['full_image_sha256']
    write(OUT/'verification.json',verification)
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--worker',choices=['QPIE','FRQI','NEQR']);args=p.parse_args()
    if args.worker:worker(args.worker)
    else:main()
