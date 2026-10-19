"""Independent emitted-subset VRML97 syntax, placement and input-integrity checks."""
import sys
sys.dont_write_bytecode = True
import json
import re
import math
import csv
from pathlib import Path
import numpy as np
import generate_wrl_visualizations as g

# Field types: number of scalar values, string, boolean, node, or bracketed list.
SCHEMA = {
 'WorldInfo': {'title':'s','info':'ms'},
 'NavigationInfo': {'type':'ms','headlight':'b','avatarSize':'mn'},
 'Background': {'skyColor':'mn'},
 'DirectionalLight': {'direction':3,'intensity':1},
 'Viewpoint': {'description':'s','position':3,'orientation':4,'fieldOfView':1},
 'Switch': {'whichChoice':1,'choice':'mo'},
 'Shape': {'appearance':'o','geometry':'o'},
 'Appearance': {'material':'o'},
 'Material': {'diffuseColor':3,'specularColor':3,'emissiveColor':3,'transparency':1},
 'Box': {'size':3}, 'Sphere': {'radius':1},
 'Transform': {'translation':3,'children':'mo'},
 'Billboard': {'axisOfRotation':3,'children':'mo'},
 'Text': {'string':'ms','fontStyle':'o'},
 'FontStyle': {'size':1,'family':'ms'},
 'Group': {'children':'mo'},
 'IndexedLineSet': {'coord':'o','coordIndex':'mn'},
 'Coordinate': {'point':'mn'},
}
TOKEN = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}\[\],]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[A-Za-z_][A-Za-z_0-9]*')

class Parser:
    def __init__(self, text):
        self.tokens=[]; end=0; self.defs={}; self.i=0
        for m in TOKEN.finditer(text):
            assert m.start()==end, 'Invalid lexical content at '+str(end)
            end=m.end(); t=m.group()
            if not t.isspace() and not t.startswith('#') and t!=',': self.tokens.append(t)
        assert end==len(text)
    def take(self, expected=None):
        t=self.tokens[self.i]; self.i+=1
        assert expected is None or t==expected, (expected,t)
        return t
    def value(self, kind):
        if isinstance(kind,int):
            v=[float(self.take()) for _ in range(kind)]
            assert all(math.isfinite(x) for x in v)
            return v
        if kind=='s':
            t=self.take(); assert t.startswith('"'); return json.loads(t)
        if kind=='b':
            t=self.take(); assert t in ('TRUE','FALSE'); return t
        if kind=='o': return self.node()
        self.take('['); v=[]
        while self.tokens[self.i]!=']': v.append(self.value({'ms':'s','mn':1,'mo':'o'}[kind]))
        self.take(']')
        return [x[0] for x in v] if kind=='mn' else v
    def node(self):
        ident=None; kind=self.take()
        if kind=='USE': return self.defs[self.take()]
        if kind=='DEF': ident=self.take(); assert ident not in self.defs; kind=self.take()
        assert kind in SCHEMA, 'Unsupported/invalid node '+kind
        self.take('{'); n={'_type':kind}
        while self.tokens[self.i]!='}':
            field=self.take(); assert field in SCHEMA[kind] and field not in n, (kind,field)
            n[field]=self.value(SCHEMA[kind][field])
        self.take('}')
        if ident: self.defs[ident]=n
        return n
    def parse(self):
        roots=[]
        while self.i<len(self.tokens): roots.append(self.node())
        return roots

def close(a,b):
    assert np.allclose(a,b,atol=1e-8,rtol=0), (a,b)

def points(group):
    return np.array(group['children'][0]['geometry']['coord']['point']).reshape(-1,3)

def main():
    sys.addaudithook(g.guard)
    out=g.OUT
    manifest=json.loads((out/'generation_manifest.json').read_text())
    baseline=json.loads((out/'protected_inputs_sha256.json').read_text())
    assert baseline==g.protected_inputs(), 'Scientific input hashes changed'
    cfg=json.loads((g.MAGIC/'config/magiccube_config.json').read_text())
    one=json.loads((g.ONE/'config/onecube_config.json').read_text())
    grid=json.loads((g.MAGIC/'config/source_grid_config.json').read_text())
    with (g.MAGIC/'config/detector_map.csv').open() as f: rows=list(csv.DictReader(f))
    with (g.MAGIC/'config/full_source_positions.csv').open() as f: sources=list(csv.DictReader(f))
    byid={int(r['detector_id']):r for r in rows}
    assert sorted(byid)==list(range(2048))
    close(list(cfg['detector']['mother_size_mm'].values()),[67.2,67.2,32])
    lat=cfg['lattice']; close([lat['n'+a] for a in 'xyz'],[16]*3)
    close([lat['pitch_'+a+'_mm'] for a in 'xyz'],[4.2,4.2,2])
    required=['onecube_geometry','onecube_source_view','magiccube_full_geometry','magiccube_cutaway','magiccube_exploded_layers','magiccube_single_layer','magiccube_adjacent_layers','magiccube_source_fov','magiccube_source_grid','magiccube_geometry_with_source','magiccube_detector_ids']
    assert all(n+'.wrl' in manifest['files'] for n in required)
    stats={}
    for filename,sha in manifest['files'].items():
        path=out/filename; text=path.read_text(); assert path.stat().st_size>100
        assert text.startswith('#VRML V2.0 utf8\n') and g.digest(path)==sha
        p=Parser(text); roots=p.parse(); defs=p.defs
        # Prototypes must be hidden, not extra renderable cubes at the origin.
        assert all(n['_type'] not in ('Box','Appearance') and not (n['_type']=='Shape' and n.get('geometry',{}).get('_type') in ('Box','Sphere')) for n in roots)
        close(defs['ElementBox']['size'],[2,2,2])
        gag={int(k[5:]):v for k,v in defs.items() if re.fullmatch(r'GAGG_\d+',k)}
        k9={k:v for k,v in defs.items() if re.fullmatch(r'K9_\d+_\d+_\d+',k)}
        transformed=filename in ('magiccube_exploded_layers.wrl','magiccube_adjacent_layers.wrl')
        if transformed: assert 'EXPLODED VISUALIZATION — NOT PHYSICAL GEOMETRY' in text
        if filename.startswith('onecube'):
            assert not gag and not k9 and 'OneCube' in defs
            close(defs['OneCube']['translation'],[one['detector'][a+'_mm'] for a in 'xyz'])
            close(defs['SourceMarker']['translation'],[one['source'][a+'_mm'] for a in 'xyz'])
        else:
            ng,nk=(128,128) if 'single_layer' in filename else ((256,256) if 'adjacent_layers' in filename else (2048,0) if any(s in filename for s in ('detector_ids','validated_response')) else (2048,2048))
            assert (len(gag),len(k9))==(ng,nk), (filename,len(gag),len(k9))
            positions=[]
            for did,node in gag.items():
                r=byid[did]; ix,iy,k,d=[int(r[f]) for f in ('ix','iy','physical_layer_k','d')]
                assert did==d*256+iy*16+ix and k==2*d+(ix+iy)%2
                expected=[float(r[a+'_mm']) for a in 'xyz']
                close(expected,[(ix-7.5)*4.2,(iy-7.5)*4.2,(k-7.5)*2])
                if transformed: expected[2]=8*k
                close(node['translation'],expected); positions.append(expected)
                if 'single_layer' in filename: assert k==0
                if 'adjacent_layers' in filename: assert k in (0,1)
            for key,node in k9.items():
                k,iy,ix=map(int,key.split('_')[1:]); assert (ix+iy+k)%2==1
                expected=[(ix-7.5)*4.2,(iy-7.5)*4.2,8*k if transformed else (k-7.5)*2]
                close(node['translation'],expected); positions.append(expected)
            if ng==2048 and not transformed:
                close(np.min(positions,axis=0),[-31.5,-31.5,-15]); close(np.max(positions,axis=0),[31.5,31.5,15])
            if 'MotherBounds' in defs:
                pp=points(defs['MotherBounds']); close(pp.min(0),[-33.6,-33.6,-16]); close(pp.max(0),[33.6,33.6,16])
            if 'SourceMarker' in defs: close(defs['SourceMarker']['translation'],cfg['source']['validation_position_mm'])
            if 'FOVOutline' in defs:
                pp=points(defs['FOVOutline']); close(pp.min(0),[-50,-50,-66]); close(pp.max(0),[50,50,-66])
                assert cfg['detector']['front_surface_z_mm']-grid['z_mm']==50
            if 'source_grid' in filename:
                assert len([k for k in defs if k.startswith('Sample_')])==2601
                for r in sources: close(defs['Sample_'+r['source_id']]['translation'],[float(r[a+'_mm']) for a in 'xyz'])
            if 'detector_ids' in filename:
                for did in g.REP: assert f'"detector {did}"' in text and did in gag
            if 'cutaway' in filename:
                assert 'Visualization cutaway — scientific geometry unchanged.' in text
                assert defs['K9Shape']['appearance']['material']['transparency'][0]>=.8
            if 'validated_response' in filename:
                raw=np.load(g.MAGIC/'results/system_matrix/system_matrix_raw.npy',allow_pickle=False)[:,0]
                counts={int(i):int(c) for i,c in re.findall(r'detector_id=(\d+) validated_singles=(\d+)',text)}
                assert len(counts)==2048
                for did,node in gag.items():
                    assert counts[did]==raw[did]
                    t=(raw[did]-raw.min())/max(1,raw.max()-raw.min())
                    close(node['children'][0]['appearance']['material']['diffuseColor'],[.12+.88*t,.08+.77*t,.35-.2*t])
        stats[filename]={'bytes':path.stat().st_size,'gagg':len(gag),'k9':len(k9),'syntax':'PASS'}
    for name in ('CASTLE_MODEL_VIEWER_GUIDE.md','SCREENSHOT_PLAN.md','WRL_GENERATION_SUMMARY.md'):
        assert (out/name).stat().st_size>100
    assert not manifest['gate_executed'] and not manifest['slurm_submitted']
    report={'status':'PASS','models':stats,'protected_input_hashes_unchanged':len(baseline),'write_boundary':str(out),'gate_executed':False,'slurm_submitted':False,'viewer_launched':False,'limitations':'Checks emitted VRML97 node/field syntax and data; no GUI rendering test. Active production outputs excluded from static integrity baseline.'}
    (out/'VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MAGICCUBE WRL VISUALIZATION PACKAGE: PASS')
    print(f'{len(stats)} models; {len(baseline)} protected scientific input hashes unchanged.')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('MAGICCUBE WRL VISUALIZATION PACKAGE: FAIL — '+repr(exc)); sys.exit(1)
