"""The one place the project's name and node prefix live. Rename here, rebuild, done."""

PROJECT = 'GeoNodes Lab'
PREFIX = 'GNL •'
CATALOG_ROOT = 'GeoNodes Lab'


def named(name):
    """`named('Rustic Fence')` → 'GNL • Rustic Fence': for node groups, objects and materials."""
    return f'{PREFIX} {name}'
