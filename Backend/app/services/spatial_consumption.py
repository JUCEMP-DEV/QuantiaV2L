"""Shared, deterministic boundary from editor 04 to inference/review 05.

No network, model calls, catalog writes or guessed dimensions. Unknowns remain
in the delivery together with the original 03 evidence and 01/02 context.
"""
from copy import deepcopy
from hashlib import sha256
import json
from math import hypot, isfinite
from shapely.geometry import Polygon, LineString

VERSION = 'QUANTIA_04_05_V1'


def number(value):
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (ValueError, TypeError):
        return None


def opening_catalog(opening):
    kind, material = opening.get('kind'), opening.get('material')
    if kind == 'GARAGE_DOOR':
        return None
    if kind == 'WINDOW':
        return 'CAN-001' if material == 'ALUMINUM' and opening.get('glazing') == 'GLASS' else None
    if kind == 'DOOR':
        if material == 'ALUMINUM' and opening.get('glazing') == 'GLASS':
            return 'CAN-002'
        if material == 'WOOD':
            return {'INTERIOR': 'CAR-001', 'MAIN_ENTRANCE': 'CAR-002'}.get(opening.get('usage'))
    return None


def resolved_stairs(spatial):
    levels = {l.get('id'): l for l in spatial.get('niveles', [])}
    result = []
    for source in spatial.get('escaleras', []):
        stair = deepcopy(source)
        start = number(levels.get(stair.get('levelFromId'), {}).get('elevationM'))
        end = number(levels.get(stair.get('levelToId'), {}).get('elevationM'))
        rise = end - start if start is not None and end is not None else None
        counts = [number(f.get('riserCount')) for f in stair.get('flights', [])]
        valid = rise is not None and rise > 0 and bool(counts) and all(n is not None and n >= 2 and n.is_integer() for n in counts)
        try:
            footprint = Polygon([(float(p['x']), float(p['y'])) for p in (stair.get('geometry') or {}).get('vertices', [])])
            valid = valid and footprint.is_valid and footprint.area > 0
            for landing in stair.get('landings', []):
                polygon = Polygon([(float(p['x']), float(p['y'])) for p in landing.get('outer', [])])
                valid = valid and polygon.is_valid and polygon.area > 0 and footprint.buffer(1e-6).covers(polygon)
            if stair.get('type') not in {'STRAIGHT', 'straight'} and not stair.get('landings'):
                valid = False
        except (ValueError, TypeError, KeyError):
            valid = False
        stair['totalRiseM'] = rise
        stair['railings'] = []
        stair['slabVoids'] = [{'id': f"{stair['id']}:slab-void", 'levelId': stair.get('levelToId'),
                               'geometry': deepcopy(stair.get('geometry')), 'confirmed': bool(stair.get('confirmed'))}]
        if not stair.get('hasSlabVoid'):
            stair['slabVoids'] = []
        if valid:
            total = sum(counts)
            for f in stair.get('flights', []):
                points = f.get('pathM', [])
                if len(points) != 2 or any(number(p.get(k)) is None for p in points for k in ('x', 'y')):
                    valid = False
                    continue
                run = hypot(float(points[1]['x'])-float(points[0]['x']), float(points[1]['y'])-float(points[0]['y']))
                if run <= 0 or not number(f.get('widthM')) or number(f['widthM']) <= 0:
                    valid = False
                    continue
                strip = LineString([(float(p['x']), float(p['y'])) for p in points]).buffer(number(f['widthM'])/2, cap_style=2)
                if not footprint.buffer(1e-6).covers(strip):
                    valid = False
                count = number(f['riserCount'])
                f['riserHeightM'] = rise / total
                f['treadDepthM'] = run / (count - 1)
                sides = ['LEFT', 'RIGHT'] if stair.get('railingSide') == 'BOTH' else [stair.get('railingSide')]
                for side in sides:
                    if side in {'LEFT', 'RIGHT'}:
                        stair['railings'].append({'id': f"{stair['id']}:{f['id']}:{side}",
                            'longitudM': hypot(run, rise * count / total), 'material': stair.get('railingMaterial'),
                            'scopeRef': f"{stair['id']}:{f['id']}:{side}", 'entityIds': [stair['id'], f['id']]})
        stair['geometryValid'] = bool(valid)
        result.append(stair)
    return result


def inspect_spatial(spatial):
    spatial = spatial or {}
    levels = {x['id']: x for x in spatial.get('niveles', []) if x.get('id')}
    walls = {x['id']: x for x in spatial.get('muros', []) if x.get('id')}
    issues, openings = [], []

    def issue(code, entity, message, resolve='04'):
        issues.append({'code': code, 'entityIds': [entity] if entity else [],
                       'message': message, 'resolveIn': resolve})

    ids = set()
    for key in ['niveles', 'espacios', 'muros', 'puertas', 'ventanas', 'escaleras', 'elementos']:
        for entity in spatial.get(key, []):
            identifier = entity.get('id')
            if not identifier or identifier in ids:
                issue('DUPLICATE_OR_MISSING_ID', identifier, 'Cada entidad debe tener un ID único.')
            ids.add(identifier)

    for key, kind in [('puertas', 'DOOR'), ('ventanas', 'WINDOW')]:
        for raw in spatial.get(key, []):
            item = deepcopy(raw)
            item['kind'] = raw.get('kind') or kind
            wall = walls.get(item.get('wallId'))
            width, height, position = map(number, (item.get('widthM'), item.get('heightM'), item.get('position')))
            sill = number(item.get('sillHeightM')) if kind == 'WINDOW' else 0.0
            errors = []
            length = None
            if wall:
                try:
                    a, b = wall['start'], wall['end']
                    values = [number(a.get('x')), number(a.get('y')), number(b.get('x')), number(b.get('y'))]
                    if None not in values:
                        length = hypot(values[2]-values[0], values[3]-values[1])
                except (KeyError, TypeError):
                    pass
                if item.get('levelId') != wall.get('levelId'):
                    errors.append('El vano y el muro pertenecen a niveles distintos.')
            if not wall or not length:
                errors.append('Falta un muro anfitrión con coordenadas métricas válidas.')
            wall_height = number(wall.get('heightM')) if wall else None
            if wall_height is None and wall:
                wall_height = number(levels.get(wall.get('levelId'), {}).get('heightM'))
            if width is None or width <= 0 or height is None or height <= 0 or sill is None or sill < 0:
                errors.append('Faltan dimensiones válidas del vano.')
            start = position * length - width / 2 if None not in (position, length, width) else None
            end = start + width if start is not None else None
            if start is None or start < -1e-6 or end > length + 1e-6:
                errors.append('El intervalo del vano está fuera del muro o no está localizado.')
            if wall_height is None or wall_height <= 0:
                errors.append('Falta la altura efectiva del muro.')
            elif height is not None and sill is not None and height + sill > wall_height + 1e-6:
                errors.append('El vano excede la altura del muro.')
            item.update({'hostWallId': item.get('wallId'), 'offsetStartM': start, 'offsetEndM': end,
                         'sillHeightM': sill, 'geometryValid': not errors,
                         'catalogCode': opening_catalog(item)})
            item['catalogStatus'] = 'MAPPED' if item['catalogCode'] else 'UNMAPPED'
            for message in errors:
                issue('INVALID_OPENING', item.get('id'), message)
            if not item.get('confirmed'):
                issue('UNCONFIRMED_OPENING', item.get('id'), 'Confirma las propiedades del vano en 04.')
            if not item['catalogCode']:
                issue('UNMAPPED_OPENING', item.get('id'), 'El elemento se conserva; no tiene suministro asociado en el catálogo actual.', 'CATALOG')
            openings.append(item)
    for i, a in enumerate(openings):
        if not a['geometryValid']:
            continue
        for b in openings[i+1:]:
            if not b['geometryValid'] or a['hostWallId'] != b['hostWallId']:
                continue
            horizontal = min(a['offsetEndM'], b['offsetEndM']) - max(a['offsetStartM'], b['offsetStartM']) > 1e-6
            vertical = min(a['sillHeightM'] + number(a['heightM']), b['sillHeightM'] + number(b['heightM'])) - max(a['sillHeightM'], b['sillHeightM']) > 1e-6
            if horizontal and vertical:
                a['geometryValid'] = b['geometryValid'] = False
                issue('OVERLAPPING_OPENINGS', a['id'], f"El vano se superpone con {b['id']} en la cara del muro.")
    if spatial.get('completeness', {}).get('openings') not in {'COMPLETE', 'CONFIRMED'}:
        issue('OPENINGS_INCOMPLETE', None, 'Revisa en 04 si están dibujadas todas las aberturas.')
    for stair in resolved_stairs(spatial):
        if not stair['geometryValid'] or not stair.get('confirmed'):
            issue('INCOMPLETE_STAIR', stair.get('id'), 'La escalera requiere niveles, elevaciones y tramos válidos.')
        issue('UNMAPPED_STAIR', stair.get('id'), 'Escalera conservada; no existe concepto de suministro completo.', 'CATALOG')
    for wall in walls.values():
        if not wall.get('confirmed') or wall.get('structuralRole') not in {'LOAD_BEARING', 'PARTITION'} or wall.get('material') in {None, '', 'UNKNOWN'}:
            issue('INCOMPLETE_WALL', wall['id'], 'Confirma material, función estructural y dimensiones del muro en 04.')
    for space in spatial.get('espacios', []):
        if not space.get('confirmed'):
            issue('UNCONFIRMED_SPACE', space.get('id'), 'Confirma el espacio y su uso en 04.')
        if not any(f.get('side') == 'FLOOR' and f.get('state') == 'CONFIRMED' and f.get('finish') not in {None, '', 'UNKNOWN'} for f in space.get('finishes', [])):
            issue('FLOOR_FINISH_UNKNOWN', space.get('id'), 'Define el acabado de piso o confirma que no lleva acabado en 04.')
    if not spatial.get('espacios') and not spatial.get('muros'):
        issue('EMPTY_MODEL', None, 'El modelo no contiene geometría para calcular.')
    return openings, issues


def build_consumption(spatial, context01=None, context02=None):
    from app.services.spatial_quantity_inputs import automatic_spatial_inputs
    spatial = deepcopy(spatial or {})
    spatial.pop('quantityHandoff', None)
    context01 = {'project': deepcopy(spatial.get('context01', {})), 'datosGeneralesObra': deepcopy(context01 or {})}
    incoming = context02 or spatial.get('context02') or {}
    context02 = {key: incoming.get(key) or '' for key in ('tipoIntervencion', 'alcanceProyecto', 'sistemaEstructural', 'tipoCimentacion', 'tipoLosa', 'varianteZapata')}
    context02['serviciosInstalaciones'] = deepcopy(incoming.get('serviciosInstalaciones') or {})
    openings, issues = inspect_spatial(spatial)
    derived, audit = automatic_spatial_inputs(spatial, context02)
    # Timestamp is not geometry: re-exporting the same model yields the same hash.
    model = {key: spatial.get(key, []) for key in ['niveles', 'espacios', 'muros', 'puertas', 'ventanas', 'escaleras', 'elementos']}
    fingerprint = {'model': model, 'completeness': spatial.get('completeness', {}), 'context01': context01, 'context02': context02}
    digest = sha256(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'schemaVersion': VERSION, 'units': 'm', 'modelSha256': digest,
            'sourceMode': spatial.get('sourceMode', 'manual'), 'revision': str(spatial['revision']) if spatial.get('revision') is not None else None,
            'context01': context01, 'context02': context02, 'estructuraEspacial': spatial,
            'openings': openings, 'stairs': resolved_stairs(spatial), 'derivedInputsByConcept': derived, 'derivationTrace': audit,
            'issues': issues, 'status': 'REVIEW_REQUIRED' if issues else 'READY_FOR_RULE_EVALUATION',
            'rulesVersion': 'V1.8-INF-DEFINITIVO', 'catalogVersion': 'V1.8-CAT-DEFINITIVO'}
