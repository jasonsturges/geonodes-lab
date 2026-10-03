"""The public composition: GNL • Vessel (silhouette in; glass, liquid and sections out) and the
modifier groups behind the ready-made vessel objects."""
import math

from authoring.graph import Graph
from authoring.naming import named


PANELS = {
    'Silhouette': ['Smooth Silhouette', 'Smooth Resolution'],
    'Glass': ['Thickness', 'Rim', 'Rounded Rim', 'Glass Material'],
    'Liquid': ['Show Liquid', 'Fill', 'Fill Inset', 'Liquid Material'],
    'Detail': ['Radial Segments', 'Smooth Angle'],
}
VESSEL_INPUTS = [name for names in PANELS.values() for name in names]


def vessel_inputs(G):
    G.input('Smooth Silhouette', 'NodeSocketBool', False,
            description='Treat the silhouette points as a Catmull-Rom spline: rounded, still through every point.')
    G.input('Smooth Resolution', 'NodeSocketInt', 8, 1, 32, 'Curve steps between silhouette points when smoothing.')
    G.input('Thickness', 'NodeSocketFloat', 0.03, 0.0, 1.0,
            '0 = single surface with a rolled rim (light, good for real-time glass); >0 = closed double wall.')
    G.input('Rim', 'NodeSocketFloat', 0.1, 0.0, 0.9, 'Rolled-lip size as a fraction of rim radius (Thickness 0).')
    G.input('Rounded Rim', 'NodeSocketBool', True, description='Round the double wall over a bead; off = flat rim.')
    G.input('Glass Material', 'NodeSocketMaterial')
    G.input('Show Liquid', 'NodeSocketBool', True)
    G.input('Fill', 'NodeSocketFloat', 0.5, 0.0, 1.0, 'Liquid level as a fraction of the vessel height.', subtype='FACTOR')
    G.input('Fill Inset', 'NodeSocketFloat', 0.03, 0.0, 0.5, 'Gap between liquid and glass, fraction of widest radius.')
    G.input('Liquid Material', 'NodeSocketMaterial')
    G.input('Radial Segments', 'NodeSocketInt', 48, 3, 256, 'Facets around the axis.')
    G.input('Smooth Angle', 'NodeSocketFloat', math.radians(40), 0.0, math.pi,
            'Edges sharper than this stay creased; the rest shade smooth.', subtype='ANGLE')


def vessel_group(shell, fill, lathe):
    G = Graph(named('Vessel'))
    G.input('Silhouette', 'NodeSocketGeometry',
            description='Outer wall, base to rim, as a curve in the XZ plane (X = radius). Any curve type.')
    vessel_inputs(G)
    for name in ('Geometry', 'Glass', 'Liquid', 'Glass Section', 'Liquid Section'):
        G.output(name)
    G.finish_io()
    i = G.i
    sil = i['Silhouette']
    smooth = G.n('GeometryNodeCurveSplineType', 'Catmull-Rom', spline_type='CATMULL_ROM')
    G.link(sil, smooth.inputs['Curve'])
    res = G.n('GeometryNodeSetSplineResolution', 'Smoothness')
    G.link(smooth.outputs[0], res.inputs['Curve'])
    G.link(i['Smooth Resolution'], res.inputs['Resolution'])
    sil = G.switch('GEOMETRY', i['Smooth Silhouette'], sil, res.outputs[0])
    # Bake whatever arrives (poly, Bézier, Catmull-Rom, NURBS) into its evaluated poly points.
    poly = G.n('GeometryNodeResampleCurve', 'Evaluated points')
    poly.inputs['Mode'].default_value = 'Evaluated'
    G.link(sil, poly.inputs['Curve'])
    sil = poly.outputs[0]

    def lathed(section, material, label):
        node = G.group(lathe, label)
        G.link(section, node.inputs['Profile'])
        G.link(i['Radial Segments'], node.inputs['Radial Segments'])
        G.link(i['Smooth Angle'], node.inputs['Smooth Angle'])
        mat = G.n('GeometryNodeSetMaterial', f'{label} material')
        G.link(node.outputs[0], mat.inputs['Geometry'])
        G.link(material, mat.inputs['Material'])
        return mat.outputs[0]

    sh = G.group(shell, 'Glass section')
    G.link(sil, sh.inputs['Silhouette'])
    for name in ('Thickness', 'Rim', 'Rounded Rim'):
        G.link(i[name], sh.inputs[name])
    fl = G.group(fill, 'Liquid section')
    G.link(sil, fl.inputs['Silhouette'])
    G.link(i['Fill'], fl.inputs['Fill'])
    G.link(i['Fill Inset'], fl.inputs['Inset'])
    glass = lathed(sh.outputs[0], i['Glass Material'], 'Glass')
    liquid = G.switch('GEOMETRY', i['Show Liquid'], None, lathed(fl.outputs[0], i['Liquid Material'], 'Liquid'))
    liquid_section = G.switch('GEOMETRY', i['Show Liquid'], None, fl.outputs[0])
    G.link(G.join(glass, liquid), G.o['Geometry'])
    G.link(glass, G.o['Glass'])
    G.link(liquid, G.o['Liquid'])
    G.link(sh.outputs[0], G.o['Glass Section'])
    G.link(liquid_section, G.o['Liquid Section'])
    G.layout()
    G.panels(PANELS, closed=('Detail',))
    G.g.description = ('Any silhouette curve in, glass and liquid out. Thickens the wall, fills to a level, '
                       'lathes with UVs. Outputs the sections too, for composing your own graph.')
    return G.g


def vessel_object_group(name, source, vessel, *, from_object=False):
    """The modifier group on each ready-made vessel object."""
    G = Graph(named(name), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    shape = []
    if from_object:
        G.input('Profile Curve', 'NodeSocketObject',
                description='A curve object drawn in its local XZ plane (X = radius), base at the axis.')
        shape.append('Profile Curve')
    else:
        for item in source.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                G.input(item.name, item.socket_type, item.default_value, item.min_value, item.max_value,
                        item.description)
                shape.append(item.name)
    vessel_inputs(G)
    G.output('Geometry')
    G.finish_io()
    if from_object:
        info = G.n('GeometryNodeObjectInfo', 'Your curve', transform_space='RELATIVE')
        G.link(G.i['Profile Curve'], info.inputs['Object'])
        sil = info.outputs['Geometry']
    else:
        node = G.group(source, name)
        for k in shape:
            G.link(G.i[k], node.inputs[k])
        sil = node.outputs[0]
    v = G.group(vessel, 'Vessel')
    G.link(sil, v.inputs['Silhouette'])
    for k in VESSEL_INPUTS:
        G.link(G.i[k], v.inputs[k])
    G.link(v.outputs['Geometry'], G.o['Geometry'])
    G.layout()
    G.panels({'Shape': shape, **PANELS}, closed=('Detail',))
    return G.g
