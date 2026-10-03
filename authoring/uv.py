"""Explicit corner-layer storage and a bounded audit, never automatic mapping."""
import math


def assign_corner_uvs(mesh, faces, name='UVMap'):
    """Assign one UV pair per face corner in mesh polygon/loop order.

    Validate everything before changing an existing layer. The caller owns island
    layout, surface roles, seam policy, packing and texel density.
    """
    faces = [[tuple(uv) for uv in face] for face in faces]
    if len(faces) != len(mesh.polygons):
        raise ValueError('UV face count must match mesh polygon count')
    for polygon, uvs in zip(mesh.polygons, faces):
        if len(uvs) != polygon.loop_total:
            raise ValueError(f'UV corner count does not match polygon {polygon.index}')
        if any(len(uv) != 2 or not all(math.isfinite(v) for v in uv) for uv in uvs):
            raise ValueError('UV coordinates must be finite pairs')
    layer = mesh.uv_layers.get(name)
    if layer is None:
        layer = mesh.uv_layers.new(name=name)
    for polygon, uvs in zip(mesh.polygons, faces):
        for index, uv in zip(polygon.loop_indices, uvs):
            layer.data[index].uv = uv
    return layer


def audit_uv(mesh, name='UVMap', *, area_epsilon=1e-12):
    """Report coverage/finite values/zero signed area, not unwrap quality.

    Empty geometry is reported explicitly. This does not detect overlap, seam
    correctness, island connectivity, distortion, packing or export behavior.
    """
    layer = mesh.uv_layers.get(name)
    result = dict(layer=name, present=layer is not None, faces=len(mesh.polygons),
                  corners=len(mesh.loops), finite=None, zero_area_faces=None)
    if layer is None:
        return result
    coords = [tuple(item.uv) for item in layer.data]
    result['covered_corners'] = len(coords)
    result['finite'] = all(math.isfinite(v) for uv in coords for v in uv)
    zero = []
    for polygon in mesh.polygons:
        uv = [coords[index] for index in polygon.loop_indices]
        twice_area = sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(uv, uv[1:]+uv[:1]))
        if abs(twice_area)*.5 <= area_epsilon:
            zero.append(polygon.index)
    result['zero_area_faces'] = zero
    return result
