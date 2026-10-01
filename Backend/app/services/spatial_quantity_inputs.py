"""Geometry-to-rule boundary for the common 04 contract (Pipeline §§19, 23, 25).

Derive measurements, not structural dimensions. Rebuilt on every simulation.
"""
from math import isfinite

from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from app.services.spatial_consumption import inspect_spatial, resolved_stairs


def positive(value):
    try:
        number = float(value)
        return number if isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def automatic_spatial_inputs(spatial, context):
    spatial = spatial if isinstance(spatial, dict) else {}
    derived, audit = {}, []
    levels = {str(x.get('id')): x for x in spatial.get('niveles', []) if isinstance(x, dict)}

    def level_key(entity):
        level = levels.get(str(entity.get('levelId')), {})
        return str(level.get('key') or entity.get('nivel') or entity.get('levelId') or '')

    def ground(entity):
        return level_key(entity) in {'planta_baja', 'ground', 'ground_floor'}

    def publish(code, name, records, rule):
        if records:
            derived.setdefault(code, {})[name] = records
            audit.append({'concept': code, 'input': name, 'rule': rule,
                          'source': '04_CANONICAL_GEOMETRY', 'status': 'PROPOSED',
                          'scopeRefs': [r['scopeRef'] for r in records]})

    # A floor is a confirmed polygon, never an area copied from a project total.
    floor_groups, ceramic_groups = {}, {}
    for space in spatial.get('espacios', []):
        if not isinstance(space, dict) or space.get('confirmed') is not True:
            continue
        if str(space.get('category', '')).lower() in {'exterior', 'outdoor', 'circulacion_exterior'}:
            continue
        key = level_key(space)
        if not key or 'azotea' in key or 'roof' in key:
            continue
        geometry = space.get('geometry') or space.get('geometria') or {}
        metric = geometry.get('metrica', geometry)
        vertices = metric.get('vertices', [])
        if len(vertices) < 3:
            continue
        try:
            polygon = Polygon([(float(p['x']), float(p['y'])) for p in vertices],
                              [[(float(p['x']), float(p['y'])) for p in hole] for hole in metric.get('holes', [])])
            if not polygon.is_valid or not positive(polygon.area):
                continue
        except (ValueError, TypeError, KeyError):
            continue
        floor_groups.setdefault(key, []).append((str(space.get('id')), polygon))
        if any(f.get('side') == 'FLOOR' and f.get('finish') == 'CERAMIC' and f.get('state') == 'CONFIRMED'
               for f in space.get('finishes', [])):
            ceramic_groups.setdefault(key, []).append((str(space.get('id')), polygon))

    floors, ground_floors = [], []
    for key, items in floor_groups.items():
        merged = unary_union([polygon for _, polygon in items])
        row = {'areaM2': merged.area, 'scopeRef': f'floor:{key}',
               'entityIds': sorted({identifier for identifier, _ in items}),
               'source': '04_CANONICAL_GEOMETRY'}
        floors.append(row)
        if key in {'planta_baja', 'ground', 'ground_floor'}:
            ground_floors.append(row)

    # Whole-building automatic coverage applies to new construction only.
    # Remodel work requires actual intervention scope, not every existing surface.
    if context.get('tipoIntervencion') == 'obra_nueva':
        publish('CIM-008', 'geometria_area_confirmada', ground_floors, 'union_ground_floor_polygons')
        ceramic = [{'areaM2': unary_union([p for _, p in items]).area, 'scopeRef': f'ceramic:{key}',
                    'entityIds': sorted({i for i, _ in items}), 'source': '04_CANONICAL_GEOMETRY'}
                   for key, items in ceramic_groups.items()]
        publish('ACA-001', 'geometria_area_confirmada', ceramic, 'confirmed_ceramic_floor_polygons')

    # Under load-bearing masonry with a continuous foundation, measure ground
    # wall axes once. No footing width, depth or isolated supports are invented.
    continuous = context.get('tipoCimentacion') in {'mamposteria_corrida', 'zapata_corrida'}
    masonry = context.get('sistemaEstructural') in {'tradicional', 'mamposteria'}
    wall_lines, wall_ids = [], []
    for wall in spatial.get('muros', []):
        if not isinstance(wall, dict) or wall.get('confirmed') is not True or not ground(wall):
            continue
        role = wall.get('structuralRole')
        if (role is not None and role != 'LOAD_BEARING') or (role is None and wall.get('loadBearing') is not True):
            continue
        try:
            a, b = wall['start'], wall['end']
            line = LineString([(float(a['x']), float(a['y'])), (float(b['x']), float(b['y']))])
            if line.is_valid and positive(line.length):
                wall_lines.append(line)
                wall_ids.append(str(wall.get('id')))
        except (KeyError, ValueError, TypeError):
            continue
    if continuous and masonry and context.get('tipoIntervencion') == 'obra_nueva' and wall_lines:
        records = [{'longitudM': unary_union(wall_lines).length, 'scopeRef': 'ground_loadbearing_axes',
                    'entityIds': sorted(set(wall_ids)), 'source': '04_CANONICAL_GEOMETRY'}]
        publish('CIM-005', 'tramos_dala_desplante_confirmados', records, 'continuous_foundation_masonry_axes')
        if context.get('tipoCimentacion') == 'mamposteria_corrida':
            publish('CIM-006', 'geometria_longitud_confirmada', records, 'continuous_masonry_foundation_axes')
        else:
            publish('CIM-002', 'tramos_zapata_corrida_confirmados', records, 'strip_foundation_axes')

    # Architectural supplies use one catalog identity per physical opening.
    # Incomplete inventories/ambiguous hosts never become an apparently complete count.
    openings, issues = inspect_spatial(spatial)
    blocking = {'INVALID_OPENING', 'OVERLAPPING_OPENINGS', 'DUPLICATE_OR_MISSING_ID',
                'UNCONFIRMED_OPENING', 'OPENINGS_INCOMPLETE'}
    if context.get('tipoIntervencion') == 'obra_nueva' and not any(i['code'] in blocking for i in issues):
        groups = {}
        for opening in openings:
            code = opening['catalogCode']
            if not code:
                continue
            row = {'scopeRef': opening['id'], 'entityIds': [opening['id']],
                   'source': '04_CANONICAL_GEOMETRY', 'wallId': opening['hostWallId']}
            if code == 'CAN-001':
                row['areaM2'] = float(opening['widthM']) * float(opening['heightM'])
            else:
                row['cantidad'] = 1  # assembly, not number of leaves
            groups.setdefault(code, []).append(row)
        for code, records in groups.items():
            publish(code, 'dimensiones_ventanas_confirmadas' if code == 'CAN-001' else 'cantidad_piezas_confirmada',
                    records, 'classified_confirmed_openings')
    stairs = resolved_stairs(spatial)
    if context.get('tipoIntervencion') == 'obra_nueva' and spatial.get('completeness', {}).get('stairs') == 'COMPLETE':
        if not any(i['code'] == 'DUPLICATE_OR_MISSING_ID' for i in issues) and all(s['geometryValid'] and s.get('confirmed') and s.get('railingSide') in {'NONE', 'LEFT', 'RIGHT', 'BOTH'} for s in stairs):
            railings = [r for s in stairs for r in s['railings'] if r['material'] == 'STEEL']
            publish('HER-002', 'tramos_barandal_confirmados', railings, 'stair_flight_3d_railing_lengths')
    return derived, audit
