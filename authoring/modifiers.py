"""Geometry Nodes modifier input access tested in Blender 5.2.1."""


def input_property(modifier, name):
    if modifier.type != 'NODES' or modifier.node_group is None:
        raise ValueError('Expected a Geometry Nodes modifier with a node group')
    matches = [item for item in modifier.node_group.interface.items_tree
               if item.item_type == 'SOCKET' and item.in_out == 'INPUT'
               and item.name == name]
    if len(matches) != 1:
        raise ValueError(f'Expected one input named {name!r}; found {len(matches)}')
    return getattr(modifier.properties.inputs, matches[0].identifier)


def set_input(modifier, name, value):
    input_property(modifier, name).value = value
    modifier.id_data.update_tag()


def get_input(modifier, name):
    return input_property(modifier, name).value
