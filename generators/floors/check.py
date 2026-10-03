"""Independent checks for assets/Floors.blend: layout invariants, an independent clipping oracle, UVs,
seeds and consumer isolation for GNL • Hardwood Floor. Run: python3 scripts/check.py floors
"""
from pathlib import Path
from collections import defaultdict, Counter
import json
import math
import sys
import time
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from authoring.modifiers import set_input,get_input
from authoring.uv import audit_uv


def polygon_area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2


def clip(poly,width,depth):
    for axis,bound,sign in [(0,-width/2,-1),(0,width/2,1),(1,-depth/2,-1),(1,depth/2,1)]:
        out=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            ai=sign*(a[axis]-bound)<=1e-12; bi=sign*(b[axis]-bound)<=1e-12
            if ai: out.append(a)
            if ai != bi:
                t=(bound-a[axis])/(b[axis]-a[axis]); out.append(tuple(a[k]+t*(b[k]-a[k]) for k in (0,1)))
        poly=out
        if not poly: break
    return poly


def inspect(obj):
    t=time.perf_counter(); bpy.context.view_layer.update()
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
    try:
        me.calc_loop_triangles()
        vertices=[tuple(v.co) for v in me.vertices]
        faces=[list(p.vertices) for p in me.polygons]
        attrs={name:[d.value for d in me.attributes[name].data] for name in ('board_id','row_id','retained_area')}
        colors=[tuple(d.color) for d in me.attributes['hardwood_tint'].data]
        uv=audit_uv(me)
        if uv['zero_area_faces']:
            print('UV ZERO',[(i,[(tuple(me.vertices[me.loops[j].vertex_index].co),tuple(me.uv_layers['UVMap'].data[j].uv)) for j in me.polygons[i].loop_indices]) for i in uv['zero_area_faces']],flush=True)
        assert uv['present'] and uv['finite'] and not uv['zero_area_faces'],uv
        coords=[tuple(d.uv) for d in me.uv_layers['UVMap'].data]
        triangles=[(list(t.vertices),t.polygon_index) for t in me.loop_triangles]
        return dict(vertices=vertices,faces=faces,attrs=attrs,colors=colors,uv=coords,triangles=triangles,seconds=time.perf_counter()-t)
    finally: ev.to_mesh_clear()


def placements(obj):
    """Read native layout as data, then check its invariants independently."""
    mod=obj.modifiers[0]; W=get_input(mod,'Room Width'); D=get_input(mod,'Room Depth'); angle=get_input(mod,'Rotation')
    c,s=abs(math.cos(angle)),abs(math.sin(angle)); run=W*c+D*s; across=W*s+D*c
    group=bpy.data.node_groups.new('Temporary layout inspection','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    n=group.nodes.new('GeometryNodeGroup'); n.node_tree=bpy.data.node_groups['GNL • Floor Laying']
    n.inputs['Run'].default_value=run; n.inputs['Across'].default_value=across
    for name in ('Board Width','Row Gap','Shortest Board','Longest Board','Stagger Target','Layout Seed'): n.inputs[name].default_value=get_input(mod,name)
    out=group.nodes.new('NodeGroupOutput'); group.links.new(n.outputs['Placements'],out.inputs[0])
    host=bpy.data.objects.new('Temporary layout host',bpy.data.meshes.new('Temporary'))
    bpy.context.collection.objects.link(host); mm=host.modifiers.new('Inspect','NODES'); mm.node_group=group
    bpy.context.view_layer.update(); ev=host.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh()
    try:
        result=[dict(center=tuple(v.co),length=mesh.attributes['board_length'].data[i].value,
                     row=mesh.attributes['row_id'].data[i].value,identity=mesh.attributes['board_id'].data[i].value)
                for i,v in enumerate(mesh.vertices)]
    finally:
        ev.to_mesh_clear(); data=host.data; bpy.data.objects.remove(host,do_unlink=True); bpy.data.meshes.remove(data); bpy.data.node_groups.remove(group)
    rows=max(1,math.floor(across/(get_input(mod,'Board Width')+get_input(mod,'Row Gap'))+.5)); pitch=across/rows
    width=pitch-get_input(mod,'Row Gap')
    buckets=defaultdict(list)
    for p in result: buckets[p['row']].append(p)
    assert set(buckets)==set(range(rows)),(rows,len(buckets))
    closest=float('inf'); prev=[]
    shortest=min(max(min(get_input(mod,'Shortest Board'),get_input(mod,'Longest Board')),.05),run)
    longest=min(max(get_input(mod,'Shortest Board'),get_input(mod,'Longest Board')),run)
    for row,boards in sorted(buckets.items()):
        boards.sort(key=lambda p:p['center'][0])
        cursor=-run/2; joints=[]
        for i,p in enumerate(boards):
            assert abs(p['center'][1]-(-across/2+(row+.5)*pitch))<1e-5
            assert abs(p['center'][0]-p['length']/2-cursor)<3e-5, (row,i,p,cursor,boards[:3])
            assert p['length']>0
            if i==0: assert p['length']>=shortest*.45-1e-5
            elif i<len(boards)-1: assert shortest-1e-5<=p['length']<=longest+1e-5
            if i==len(boards)-1 and i>0: assert p['length']>=shortest-1e-5
            cursor+=p['length']
            if i<len(boards)-1:
                joints.append(cursor)
                for x in prev: closest=min(closest,abs(cursor-x))
        assert abs(cursor-run/2)<4e-5
        prev=joints
    return result,width,rows,0 if math.isinf(closest) else closest


def verify(obj):
    data=inspect(obj); mod=obj.modifiers[0]; ps,width,rows,closest=placements(obj)
    W=get_input(mod,'Room Width'); D=get_input(mod,'Room Depth'); T=get_input(mod,'Thickness')
    angle=get_input(mod,'Rotation'); c=math.cos(angle); s=math.sin(angle)
    minimum=get_input(mod,'Min Sliver Area'); expected={}; slivers=0; clipped=0; absorbed=0; records=[]
    for p in ps:
        x,y,_=p['center']; L=p['length']
        poly=[(u*c-v*s,u*s+v*c) for u,v in [(x-L/2,y-width/2),(x+L/2,y-width/2),(x+L/2,y+width/2),(x-L/2,y+width/2)]]
        poly=clip(poly,W,D); area=polygon_area(poly) if len(poly)>2 else 0
        records.append((p,area))
    retained=[(p,a) for p,a in records if a>1e-8 and a>=minimum-1e-9]
    spans={p['identity']:[p['center'][0]-p['length']/2,p['center'][0]+p['length']/2] for p,a in retained}
    expected={p['identity']:a for p,a in retained}
    for p,a in records:
        if a<=1e-8 or p['identity'] in expected: continue
        candidates=[q for q,qa in retained if q['row']==p['row']]
        if not candidates:
            slivers+=1; continue
        owner=min(candidates,key=lambda q:abs(q['center'][0]-p['center'][0]))['identity']
        expected[owner]+=a; absorbed+=1
        spans[owner][0]=min(spans[owner][0],p['center'][0]-p['length']/2)
        spans[owner][1]=max(spans[owner][1],p['center'][0]+p['length']/2)
    clipped=sum(a<(spans[identity][1]-spans[identity][0])*width-1e-6 for identity,a in expected.items())
    by_board=defaultdict(list)
    for i,b in enumerate(data['attrs']['board_id']): by_board[b].append(i)
    assert set(by_board)==set(expected),(len(by_board),len(expected),set(by_board)^set(expected))
    for v in data['vertices']:
        assert all(math.isfinite(a) for a in v)
        assert abs(v[0])<=W/2+2e-5 and abs(v[1])<=D/2+2e-5 and -T-2e-5<=v[2]<=2e-5
    volumes=defaultdict(float)
    from mathutils import Vector
    for tri,face in data['triangles']:
        a,b,c=[Vector(data['vertices'][i]) for i in tri]
        assert (b-a).cross(c-a).length>1e-10,'Degenerate triangle'
        volumes[data['attrs']['board_id'][face]]+=a.dot(b.cross(c))/6
    for identity,faces in by_board.items():
        edges=Counter(); directed=Counter(); tints=set()
        for i in faces:
            f=data['faces'][i]; tints.add(data['colors'][i])
            for a,b in zip(f,f[1:]+f[:1]): edges[tuple(sorted((a,b)))]+=1; directed[a,b]+=1
        assert all(v==2 for v in edges.values()),('Open board',identity)
        assert all(directed[a,b]==directed[b,a] for a,b in directed),'Winding'
        assert len(tints)==1,'Color varies within board'
        assert abs(volumes[identity]-expected[identity]*T)<max(2e-7,expected[identity]*T*1e-4),(identity,volumes[identity],expected[identity]*T)
    area=sum(expected.values())
    return dict(boards=len(expected),rows=rows,actual_width=width,closest_joint=closest,
                clipped=clipped,slivers=slivers,absorbed=absorbed,area=area,seconds=data['seconds']),data


def diagnostics(obj):
    group=bpy.data.node_groups.new('Temporary output diagnostics','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    n=group.nodes.new('GeometryNodeGroup'); n.node_tree=obj.modifiers[0].node_group
    for s in n.inputs: s.default_value=get_input(obj.modifiers[0],s.name)
    geo=n.outputs['Geometry']
    names=['Board Count','Row Count','Actual Board Width','Closest Joint','Sliver Count','Clipped Count','Absorbed Count']
    for name in names:
        store=group.nodes.new('GeometryNodeStoreNamedAttribute'); store.data_type='FLOAT'; store.domain='FACE'
        store.inputs['Name'].default_value=name
        group.links.new(geo,store.inputs['Geometry']); group.links.new(n.outputs[name],store.inputs['Value'])
        geo=store.outputs['Geometry']
    out=group.nodes.new('NodeGroupOutput'); group.links.new(geo,out.inputs[0])
    host=bpy.data.objects.new('Temporary diagnostics',bpy.data.meshes.new('Temporary diagnostics'))
    bpy.context.collection.objects.link(host); mod=host.modifiers.new('Read outputs','NODES'); mod.node_group=group
    bpy.context.view_layer.update(); ev=host.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=ev.to_mesh()
    try: result={name:mesh.attributes[name].data[0].value for name in names}
    finally:
        ev.to_mesh_clear(); data=host.data; bpy.data.objects.remove(host,do_unlink=True); bpy.data.meshes.remove(data); bpy.data.node_groups.remove(group)
    return result


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(location=(20,20,0)); unrelated=bpy.context.object; unrelated.name='Existing consumer object'
    with bpy.data.libraries.load(str(ROOT/'assets/Floors.blend'),link=False) as (src,dst): dst.objects=['GNL • Hardwood Floor']
    obj=dst.objects[0]; bpy.context.collection.objects.link(obj); mod=obj.modifiers[0]
    defaults={name:get_input(mod,name) for name in ('Room Width','Room Depth','Rotation','Board Width','Row Gap','Thickness','Shortest Board','Longest Board','Stagger Target','Min Sliver Area','Layout Seed','Color Seed','Color A','Color B')}
    report=[]
    cases=[{}, {'Rotation':0.}, {'Rotation':math.pi/2}, {'Rotation':-.37}, {'Rotation':math.pi},
           {'Rotation':.02,'Min Sliver Area':0.}, {'Rotation':.71,'Row Gap':0.},
           {'Room Width':1.5,'Room Depth':1.5,'Board Width':.5,'Shortest Board':3.,'Longest Board':4.},
           {'Room Width':3.,'Room Depth':2.,'Board Width':.08,'Row Gap':.03,'Layout Seed':7},
           {'Shortest Board':1.4,'Longest Board':.5,'Stagger Target':1.5},
           {'Shortest Board':.7,'Longest Board':.7,'Stagger Target':0.},
           {'Min Sliver Area':.05,'Thickness':.2}, {'Layout Seed':65535,'Rotation':1.21},
           {'Room Width':10.,'Room Depth':10.,'Board Width':.08,'Row Gap':0.,'Shortest Board':.2,'Longest Board':.3,'Min Sliver Area':0.,'Layout Seed':0}]
    baseline=None
    for changes in cases:
        for name,value in defaults.items(): set_input(mod,name,value)
        for name,value in changes.items(): set_input(mod,name,value)
        stats,data=verify(obj); report.append({'changes':changes,**stats}); print('PASS',changes,stats,flush=True)
        outputs=diagnostics(obj)
        for key,name in [('boards','Board Count'),('rows','Row Count'),('actual_width','Actual Board Width'),('closest_joint','Closest Joint'),('slivers','Sliver Count'),('clipped','Clipped Count'),('absorbed','Absorbed Count')]:
            assert abs(stats[key]-outputs[name])<2e-5,(key,stats[key],outputs[name])
        if not changes:
            baseline=data
            assert stats['absorbed']==3 and stats['slivers']==0
            assert abs(stats['area']-18.8696885)<1e-5,stats
            # Interior probes in the three formerly missing wall-end triangles.
            from mathutils.bvhtree import BVHTree
            tree=BVHTree.FromPolygons(data['vertices'],data['faces'])
            for x,y in [(-1.9336173,1.9916226),(-2.4864069,-.6507355),(2.4899152,-.5387397)]:
                hit,normal,face,distance=tree.ray_cast((x,y,1),(0,0,-1),2)
                assert hit is not None and abs(hit.z)<1e-5,('Missing wall-end patch',x,y)
    for name,value in defaults.items(): set_input(mod,name,value)
    repeat=inspect(obj)
    for name in ('vertices','faces','colors','uv'): assert repeat[name]==baseline[name],('Repeatability',name)
    set_input(mod,'Color Seed',88); colored=inspect(obj)
    assert colored['vertices']==baseline['vertices'] and colored['faces']==baseline['faces'] and colored['uv']==baseline['uv']
    assert colored['colors']!=baseline['colors']
    set_input(mod,'Color A',(1,0,0,1)); recolored=inspect(obj); assert recolored['vertices']==baseline['vertices'] and recolored['colors']!=colored['colors']
    set_input(mod,'Use Base Color Variation',True); hsl=inspect(obj)
    assert hsl['vertices']==baseline['vertices'] and hsl['colors']!=recolored['colors']
    set_input(mod,'Layout Seed',123); changed=inspect(obj); assert changed['vertices']!=baseline['vertices']
    assert unrelated.name in bpy.context.scene.objects and tuple(unrelated.location)==(20.,20.,0.)
    # A second consumer instance shares the recipe with independent arguments.
    other=obj.copy(); other.data=obj.data.copy(); bpy.context.collection.objects.link(other)
    set_input(other.modifiers[0],'Room Width',2.); assert get_input(mod,'Room Width')==defaults['Room Width']
    # The saved node-group asset independently replaces an arbitrary host mesh.
    bpy.ops.mesh.primitive_cube_add(); host=bpy.context.object
    mm=host.modifiers.new('Standalone group consumer','NODES'); mm.node_group=bpy.data.node_groups['GNL • Hardwood Floor']
    direct=inspect(host)
    assert direct['vertices']==baseline['vertices'] and direct['faces']==baseline['faces']
    print(f'Floors: {len(report)} hardwood cases passed, plus layout invariants, independent clipping oracle, '
          'UV layers, seeds and consumer isolation')

if __name__=='__main__': main()
