"""Generate VRML97 presentation assets; scientific projects are read-only inputs."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parents[1]
MAGIC = OUT.parents[1]
ONE = MAGIC.parent / 'OneCube'
REP = [0, 1, 15, 16, 255, 256, 1792, 2047]


def guard(event, args):
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes, os.PathLike)) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            if not Path(path).resolve().is_relative_to(OUT):
                raise PermissionError('Visualization-only write boundary: ' + str(path))
    if event in ('subprocess.Popen', 'os.system', 'os.remove', 'os.rename'):
        raise PermissionError('Operation prohibited in visualization generation: ' + event)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def protected_inputs():
    # Static scientific files only: active production artifacts are deliberately not scanned.
    paths = []
    for root in (ONE, MAGIC):
        for folder in ('config', 'GATE-Macro', 'scripts', 'slurm'):
            base = root / folder
            if base.exists():
                paths.extend(p for p in base.rglob('*') if p.is_file() and p.suffix.lower() in ('.json', '.csv', '.parquet', '.mac', '.db', '.py', '.sh', '.slurm', '.txt', '.yaml', '.yml'))
    paths += [MAGIC / 'results/final_summary_validation.json', MAGIC / 'results/validation/runtime_validation_validation.json', MAGIC / 'results/system_matrix/system_matrix_raw.npy']
    return {str(p): digest(p) for p in sorted(set(paths)) if p.exists()}


def vec(v):
    assert all(math.isfinite(float(x)) for x in v)
    return ' '.join(f'{float(x):.9g}' for x in v)


def q(s):
    return json.dumps(s, ensure_ascii=False)


def label(s, pos, size=2):
    return f'Transform {{ translation {vec(pos)} children [ Billboard {{ axisOfRotation 0 0 0 children [ Shape {{ appearance USE LabelAppearance geometry Text {{ string [{q(s)}] fontStyle FontStyle {{ size {size} family ["SANS"] }} }} }} ] }} ] }}\n'


def lines(points, indices, color=(.6, .7, .8)):
    return f'Shape {{ appearance Appearance {{ material Material {{ emissiveColor {vec(color)} }} }} geometry IndexedLineSet {{ coord Coordinate {{ point [{", ".join(vec(p) for p in points)}] }} coordIndex [{" ".join(str(i) for i in indices)}] }} }}\n'


def cameras(center, radius):
    # VRML cameras look down local -z; derive axis-angle rotation from a look-at basis.
    import numpy as np
    result = ''
    for name, direction in [('Isometric', (1, .65, -1.6)), ('Source-facing (-z)', (0, 0, -1)), ('Side (+x)', (1, 0, 0)), ('Top (+y)', (0, 1, 0)), ('Rear (+z)', (0, 0, 1))]:
        back = np.array(direction, dtype=float); back /= np.linalg.norm(back)
        up = np.array([0, 0, 1] if name.startswith('Top') else [0, 1, 0], dtype=float)
        right = np.cross(up, back); right /= np.linalg.norm(right)
        up = np.cross(back, right)
        r = np.column_stack([right, up, back])
        angle = math.acos(float(np.clip((np.trace(r)-1)/2, -1, 1)))
        if angle < 1e-8:
            axis = np.array([0, 1, 0])
        elif abs(angle-math.pi) < 1e-7:
            vals, eigs = np.linalg.eig(r); axis = np.real(eigs[:, np.argmin(abs(vals-1))])
        else:
            axis = np.array([r[2,1]-r[1,2], r[0,2]-r[2,0], r[1,0]-r[0,1]])/(2*math.sin(angle))
        pos = np.array(center)+back*radius*3.3
        result += f'Viewpoint {{ description {q(name)} position {vec(pos)} orientation {vec(axis)} {angle:.9g} fieldOfView 0.72 }}\n'
    return result


def raw_header(name, center, radius, size, transparency=.28, note='Physical element coordinates; colors and annotations are visualization only.'):
    return '#VRML V2.0 utf8\n' + f'# {note}\n# Units: millimetres (one scene unit = 1 mm). No photon trajectories.\n' + f'WorldInfo {{ title {q(name)} info [{q(note)} "Source spheres are display markers, not physical source volumes." "Presentation colors do not represent GATE optical properties."] }}\n' + 'NavigationInfo { type ["EXAMINE" "ANY"] headlight TRUE avatarSize [0.1 1.6 0.75] }\nBackground { skyColor [0.035 0.05 0.08] }\nDirectionalLight { direction -1 -1 1 intensity 0.65 }\n' + cameras(center, radius) + f'DEF ElementBox Box {{ size {vec(size)} }}\nDEF LabelAppearance Appearance {{ material Material {{ diffuseColor 0.94 0.96 1 emissiveColor 0.5 0.5 0.5 }} }}\nDEF GAGGShape Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.05 0.72 0.85 specularColor 0.25 0.25 0.25 }} }} geometry USE ElementBox }}\nDEF K9Shape Shape {{ appearance Appearance {{ material Material {{ diffuseColor 0.95 0.57 0.15 transparency {transparency} }} }} geometry USE ElementBox }}\n'


def header(name, center, radius, size, transparency=.28, note='Physical element coordinates; colors and annotations are visualization only.'):
    # Store reusable nodes inside an inactive Switch, so prototypes do not render.
    s = raw_header(name, center, radius, size, transparency, note)
    prefix, definitions = s.split('DEF ElementBox ', 1)
    box, definitions = definitions.split('\n', 1)
    appearance, shapes = definitions.split('\n', 1)
    shapes = shapes.replace('geometry USE ElementBox', 'geometry DEF ElementBox '+box, 1)
    return prefix+'Switch { whichChoice -1 choice [ Shape { appearance '+appearance+' }\n'+shapes+'] }\n'


def axes(origin, length=15):
    s = ''
    for i, (name, color) in enumerate([('x', (1,.25,.25)), ('y', (.25,1,.35)), ('z', (.35,.55,1))]):
        end = list(origin); end[i] += length
        s += lines([origin, end], [0, 1, -1], color) + label('+'+name, end, length*.11)
    return s


def source(pos, radius=1):
    return f'DEF SourceMarker Transform {{ translation {vec(pos)} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor 1 0.2 0.55 emissiveColor 0.4 0.04 0.12 }} }} geometry Sphere {{ radius {radius} }} }} ] }}\n' + label('140 keV point source (display marker)', [pos[0]+2, pos[1], pos[2]], max(radius*1.7, .8))


def bounds(cfg):
    size = cfg['detector']['mother_size_mm']; center = cfg['detector']['center_mm']
    p = [[center[0]+a*size['x']/2, center[1]+b*size['y']/2, center[2]+c*size['z']/2] for c in (-1,1) for b in (-1,1) for a in (-1,1)]
    idx = []
    for a in range(8):
        for bit in (1,2,4):
            if not a & bit: idx.extend([a,a|bit,-1])
    return 'DEF MotherBounds Group { children [\n'+lines(p,idx,(.4,.5,.6))+'] }\n'+label('Mother bounds 67.2 x 67.2 x 32 mm', [-33.6,-40,16],2)


def fov(grid, cfg):
    x,y = grid['fov_mm']['x']/2, grid['fov_mm']['y']/2
    cx,cy,z = grid['center_mm']['x'],grid['center_mm']['y'],grid['z_mm']
    p = [[cx-x,cy-y,z],[cx+x,cy-y,z],[cx+x,cy+y,z],[cx-x,cy+y,z]]
    front = cfg['detector']['front_surface_z_mm']
    return 'DEF FOVOutline Group { children [\n'+lines(p,[0,1,2,3,0,-1],(.5,.65,.8))+'] }\n'+label('100 x 100 mm FOV; z=-66 mm',[-50,-57,z],2.5)+lines([[43,0,z],[43,0,front],[41,0,z],[45,0,z],[41,0,front],[45,0,front]],[0,1,-1,2,3,-1,4,5,-1],(1,.8,.4))+label('50 mm to front face',[45,0,(z+front)/2],2)+label('Source-facing surface z=-16 mm',[-33,38,front],2)


def load():
    one = json.loads((ONE/'config/onecube_config.json').read_text())
    cfg = json.loads((MAGIC/'config/magiccube_config.json').read_text())
    grid = json.loads((MAGIC/'config/source_grid_config.json').read_text())
    with (MAGIC/'config/detector_map.csv').open() as f: rows=list(csv.DictReader(f))
    with (MAGIC/'config/full_source_positions.csv').open() as f: sources=list(csv.DictReader(f))
    lattice = cfg['lattice']; center = cfg['detector']['center_mm']
    elements=[]; bypos = {(int(r['ix']),int(r['iy']),int(r['physical_layer_k'])):r for r in rows}
    for k in range(lattice['nz']):
        for iy in range(lattice['ny']):
            for ix in range(lattice['nx']):
                material = 'GAGG' if (ix+iy+k)%2 == cfg['material_pattern']['gagg_when_remainder'] else 'K9'
                pos = [center[i]+(v-(lattice[n]-1)/2)*lattice[p] for i,v,n,p in [(0,ix,'nx','pitch_x_mm'),(1,iy,'ny','pitch_y_mm'),(2,k,'nz','pitch_z_mm')]]
                row=bypos.get((ix,iy,k)); did=int(row['detector_id']) if row else -1
                if material=='GAGG':
                    assert row is not None and all(abs(pos[i]-float(row[a+'_mm']))<1e-8 for i,a in enumerate('xyz'))
                    assert did == int(row['d'])*256+iy*16+ix
                else: assert row is None
                elements.append(dict(material=material,pos=pos,k=k,ix=ix,iy=iy,id=did))
    return one,cfg,grid,rows,sources,elements


def elements_text(elements, layer_step=None, response=None):
    s=''
    for e in elements:
        p=e['pos'].copy()
        if layer_step is not None: p[2] = e['k']*layer_step
        ident=f"GAGG_{e['id']}" if e['material']=='GAGG' else f"K9_{e['k']}_{e['iy']}_{e['ix']}"
        if response is None:
            child='USE '+e['material']+'Shape'
        else:
            count=int(response[e['id']]); t=(count-response.min())/max(1,response.max()-response.min())
            color=(.12+.88*t,.08+.77*t,.35-.2*t)
            child=f'Shape {{ appearance Appearance {{ material Material {{ diffuseColor {vec(color)} }} }} geometry USE ElementBox }}'
            s+=f'# detector_id={e["id"]} validated_singles={count}\n'
        s+=f'DEF {ident} Transform {{ translation {vec(p)} children [ {child} ] }}\n'
    return s


def main():
    sys.addaudithook(guard)
    before=protected_inputs()
    one,cfg,grid,rows,sources,elements=load()
    l=cfg['lattice']; size=[l['segment_size_'+a+'_mm'] for a in 'xyz']
    src=cfg['source']['validation_position_mm']; outputs={}
    d=one['detector']; o=one['source']; op=[o[a+'_mm'] for a in 'xyz']; dp=[d[a+'_mm'] for a in 'xyz']; ds=[d['size_'+a+'_mm'] for a in 'xyz']
    for name in ('onecube_geometry','onecube_source_view'):
        s=header(name,[0,0,-25],32,ds)+f'DEF OneCube Transform {{ translation {vec(dp)} children [ USE GAGGShape ] }}\n'+source(op,.65)+axes([5,-4,0],5)
        s+=lines([op,dp],[0,1,-1],(.8,.8,.5))+label('Schematic source-to-detector direction; not a photon track',[3,0,-30],1)
        s+=label('50 mm to face / 51 mm to center',[3,0,-38],1)+label('GAGG: 2 x 2 x 2 mm',[-4,4,0],.8)
        outputs[name]=s
    modes={'magiccube_full_geometry':.25,'magiccube_cutaway':.9,'magiccube_source_fov':.65,'magiccube_source_grid':.8,'magiccube_geometry_with_source':.8}
    for name,trans in modes.items():
        has_fov=name in ('magiccube_source_fov','magiccube_source_grid','magiccube_geometry_with_source')
        note='Visualization cutaway — scientific geometry unchanged.' if name=='magiccube_cutaway' else 'Physical element positions; presentation annotations only.'
        s=header(name,[0,0,-25] if has_fov else [0,0,0],80 if has_fov else 58,size,trans,note)+elements_text(elements)+bounds(cfg)+axes([-43,-40,-16])
        if name=='magiccube_cutaway': s+=label(note,[-35,44,16],2)
        if has_fov: s+=source(src)+fov(grid,cfg)
        if name=='magiccube_source_grid':
            s+='Switch { whichChoice -1 choice [ DEF GridMarkerShape Shape { appearance Appearance { material Material { emissiveColor 0.45 0.55 0.7 } } geometry Sphere { radius 0.12 } } ] }\n'
            for r in sources:
                s+=f'DEF Sample_{int(r["source_id"])} Transform {{ translation {vec([float(r[a+"_mm"]) for a in "xyz"])} children [ USE GridMarkerShape ] }}\n'
            s+=label('Source-grid visualization: 2601 point locations; marker sizes arbitrary',[-50,58,-66],2)
        outputs[name]=s
    for name,layers,step in [('magiccube_exploded_layers',range(16),8),('magiccube_single_layer',[0],None),('magiccube_adjacent_layers',[0,1],8)]:
        note='EXPLODED VISUALIZATION — NOT PHYSICAL GEOMETRY' if step else 'Physical layer k=0 subset; other layers omitted for presentation.'
        selected=[e for e in elements if e['k'] in layers]
        s=header(name,[0,0,60] if len(layers)==16 else [0,0,0],90 if len(layers)==16 else 55,size,.15,note)+elements_text(selected,step)
        for k in layers: s+=label(f'k={k}',[37,0,k*step if step else -15],2)
        s+=axes([-42,-42,0])+label(note,[-33,42,0],1.8)+label('4.2 mm x/y pitch; 2 x 2 mm footprint',[-33,-47,0],1.8)
        outputs[name]=s
    s=header('Canonical detector IDs',[0,0,0],65,size)+elements_text([e for e in elements if e['material']=='GAGG'])+axes([-43,-40,-16])
    for j,did in enumerate(REP):
        e=next(e for e in elements if e['id']==did); p=e['pos']; target=[-65 if j%2==0 else 40,-45+j*13,p[2]]
        s+=lines([p,target],[0,1,-1],(1,.8,.3))+label(f'detector {did}',target,1.8)
    s+=label('ID = d*256 + iy*16 + ix; position-derived',[-36,63,0],2)
    outputs['magiccube_detector_ids']=s
    response_note=''
    try:
        import numpy as np
        report=json.loads((MAGIC/'results/final_summary_validation.json').read_text())
        validation=json.loads((MAGIC/'results/validation/runtime_validation_validation.json').read_text())
        assert report['passed'] and validation['passed'] and report['shape']==[2048,1] and report['canonical_detector_order']=='0..2047'
        assert report['pass_token']=='MAGICCUBE_2048x1_END_TO_END_PASS'
        path=MAGIC/report['raw_counts']; response=np.load(path,allow_pickle=False)
        assert response.shape==(2048,1) and np.isfinite(response).all() and (response>=0).all()
        response=response[:,0]
        outputs['magiccube_validated_response']=header('Validated 2048 x 1 Singles response',[0,0,-25],75,size)+elements_text([e for e in elements if e['material']=='GAGG'],response=response)+source(src)+axes([-43,-40,-16])+label(f'Validated Singles: {int(response.min())} (purple) to {int(response.max())} (yellow)',[-40,43,0],2)
        response_note=f'Generated from {path}. Minimum {response.min()}, maximum {response.max()}, sum {response.sum()}. Linear t=(count-min)/(max-min); RGB=(0.12+0.88t,0.08+0.77t,0.35-0.20t). Counts are raw Singles, not normalized sensitivity. K9 omitted. Canonical order 0..2047; no production data used.'
        (OUT/'magiccube_validated_response_legend.txt').write_text(response_note+'\n')
    except (OSError,KeyError,AssertionError,ImportError,ValueError) as exc:
        response_note='Optional response view skipped: '+repr(exc)
    for name,s in outputs.items(): (OUT/(name+'.wrl')).write_text(s,encoding='utf-8')
    assert before==protected_inputs(), 'Protected scientific inputs changed'
    (OUT/'protected_inputs_sha256.json').write_text(json.dumps(before,indent=2)+'\n')
    (OUT/'generation_manifest.json').write_text(json.dumps({'generated_utc':datetime.now(timezone.utc).isoformat(),'files':{name+'.wrl':digest(OUT/(name+'.wrl')) for name in outputs},'response':response_note,'write_boundary':str(OUT),'protected_files':len(before),'audit_guard':'Only output-directory writes permitted; no subprocesses allowed','gate_executed':False,'slurm_submitted':False},indent=2)+'\n')
    docs(outputs,response_note)
    print(f'Generated {len(outputs)} VRML models under {OUT}; {len(before)} protected-file hashes unchanged.')


def docs(outputs,response_note):
    guide='''# Castle Model Viewer meeting guide

All coordinates use millimetres. Open Castle Model Viewer yourself, use File → Open, and choose a `.wrl` in this directory. These are standalone VRML97 models with no external textures.

Use Examine navigation. Drag with the left mouse button to rotate, middle-drag (or Shift+left-drag) to pan, and use the wheel/right-drag to zoom. Use Navigation → Jump To Viewpoint for the built-in Isometric, Source-facing (-z), Side (+x), Top (+y), and Rear (+z) cameras. Source-facing looks along +z; the top camera looks down -y. Space stops automatic rotation. Exact menus may differ by release.

Controls reference: [official Castle Model Viewer manual](https://castle-engine.io/castle-model-viewer).

## Recommended files to open during meeting

1. `onecube_source_view.wrl`: explain the point source, 50 mm face distance, and single 2 mm GAGG cube.
2. `magiccube_full_geometry.wrl`: show 2048 GAGG and 2048 K9 elements in the frozen 16-layer arrangement.
3. `magiccube_cutaway.wrl`: use the highly transparent K9 to reveal all internal GAGG locations.
4. `magiccube_exploded_layers.wrl`: show layer order k=0 through k=15 and alternating checkerboards.
5. `magiccube_source_fov.wrl`: explain the 100 mm FOV outline 50 mm from the detector front.
6. `magiccube_geometry_with_source.wrl`: combine the detector, source, FOV, and distance in the main meeting view.
7. `magiccube_validated_response.wrl`, when present: explain actual completed single-source Singles counts using the accompanying legend.

## Physical geometry versus display transformations

OneCube views, full geometry, cutaway, source/FOV, source grid, and geometry-with-source preserve physical element locations and sizes. Cutaway changes only K9 opacity. Detector-ID and response views are physical-position GAGG subsets with K9 omitted. The single-layer model is a physical-position k=0 subset. Exploded and adjacent-layer models move z layers to display z=8*k mm: x/y, cube size, and layer order remain unchanged. They are explicitly marked NOT PHYSICAL GEOMETRY.

The mother outline is 67.2×67.2×32 mm; occupied element bounds are ±32.5 mm in x/y and ±16 mm in z. Air and cylindricalPET bookkeeping are hidden. Source spheres, lines, axes, labels, and grid markers are presentation aids, not physical source volumes or photon tracks. Colors/transparency do not represent optical properties; K9 is the existing provisional glass proxy.

Use Isometric for the full detector/cutaway, Source-facing for checkerboards, Side for depth and source spacing, and Top for an orthogonal overview. For the OneCube close-up, zoom toward its detector; its cube retains true scale despite the long source distance. Transparent surfaces may sort differently by renderer; use the GAGG-only ID/response view for an unobstructed interior.

The source grid comes from the existing full_source_positions.csv (51×51 inclusive endpoints). Its endpoints are a project convention, not a paper-confirmed result. The central validation source is separate from full-grid source_id=0 at a corner.

## Verification and regeneration

Run `python scripts/validate_wrl_visualizations.py`. The generator can be run with `python scripts/generate_wrl_visualizations.py`; it writes only here. No Gate, Slurm, or GUI invocation is needed. The validator checks generated VRML structure and placement, not a Castle rendering session.
'''
    (OUT/'CASTLE_MODEL_VIEWER_GUIDE.md').write_text(guide)
    plan='''# Screenshot plan

| File | Camera | Demonstrates | Suggested slide title |
|---|---|---|---|
| onecube_source_view.wrl | Isometric, then slightly rotate/zoom to retain both source and cube | True source-to-detector relationship; display line is schematic | OneCube: the minimal pipeline proof |
| magiccube_full_geometry.wrl | Isometric | Complete alternating lattice and detector envelope | Scaling to the full MagicCube |
| magiccube_cutaway.wrl | Isometric or Side | Internal GAGG structure through transparent K9 | Inside the 16-layer detector |
| magiccube_adjacent_layers.wrl | Isometric, tilted enough to separate both layers | Checkerboard flips; z separation is display-only | Adjacent layers alternate material positions |
| magiccube_geometry_with_source.wrl | Isometric or Side | FOV z=-66, detector front z=-16, 50 mm gap | Source and field-of-view geometry |
| magiccube_validated_response.wrl (if generated) | Isometric | Actual validated 2048×1 counts; show legend text alongside screenshot | Validated single-source detector response |

Keep axes and view notes visible. For response screenshots include the minimum/maximum and data-source caption from the legend. Do not caption exploded views as physical geometry or the source line as a photon trajectory. Screenshots are to be captured interactively by the user; the viewer was not launched.
'''
    (OUT/'SCREENSHOT_PLAN.md').write_text(plan)
    (OUT/'WRL_GENERATION_SUMMARY.md').write_text('# WRL generation summary\n\n'+ '\n'.join('- `'+name+'.wrl`' for name in outputs)+'\n\n'+response_note+'\n\nAll generated files are under '+str(OUT)+'.\n\nPhysical positions are retained except in the explicitly marked exploded and adjacent-layer display transformations. Cutaway is transparency-only; ID/response and single-layer files omit elements for clarity. Source markers are schematic. See CASTLE_MODEL_VIEWER_GUIDE.md for classifications.\n\nScientific configuration, macros, maps, scripts, and completed response inputs are SHA-256 checked before/after generation. Active production outputs are not scanned or modified. A Python audit guard rejects writes outside this directory and subprocess launches. Gate executed: NO. Slurm submitted/controlled: NO. Viewer launched: NO.\n\nValidation result is recorded in VALIDATION_REPORT.json after the validator runs.\n')


if __name__=='__main__':
    main()
