"""Generate design artifacts from local V1.8 rules; never changes runtime rules."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Documentacion/Contratos'
RULES = ROOT / 'Backend/data/engine/Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json'


def obj(properties, required=None):
    return {'type': 'object', 'additionalProperties': False, 'properties': properties,
            'required': list(properties) if required is None else required}


def ref(name):
    return {'$ref': '#/$defs/' + name}


def array(items):
    return {'type': 'array', 'items': items}


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = RULES.read_bytes()
    rules = json.loads(raw.decode('utf-8-sig'))
    automatic = {'CIM-002', 'CIM-005', 'CIM-006', 'CIM-008', 'ACA-001', 'CAN-001', 'CAN-002', 'CAR-001', 'CAR-002', 'HER-002'}
    rows = []
    for entry in rules['concept_rules']:
        spec = entry['spec']
        rows.append({
            'code': entry['code'], 'conceptId': entry['concept_id'],
            'name': spec['spec_name'], 'active': entry['is_active'],
            'partida': entry['partida'], 'strategy': spec['inference_strategy'],
            'requiredInputs': spec['parameter_rules'].get('required_inputs', []),
            'requiresProjectDefinition': spec.get('requires_project_definition', False),
            'dependencies': spec.get('dependencies_json', {}),
            'exclusions': spec.get('exclusions_json', []),
            'unit': entry.get('activation_rule', {}).get('derivation_json', {}).get('unit'),
            'new04AdapterCoverage': 'CONDITIONAL' if entry['code'] in automatic else 'NOT_IMPLEMENTED_IN_NEW_ADAPTER',
        })
    matrix = {'status': 'AUDIT', 'rulesVersion': rules['rules_version'],
              'rulesSha256': hashlib.sha256(raw).hexdigest(), 'conceptCount': len(rows),
              'activeCount': sum(row['active'] for row in rows),
              'coverageNote': 'Coverage refers only to spatial_quantity_inputs.py, not all legacy motor paths.',
              'concepts': rows}
    (OUT / 'MATRIZ_REQUISITOS_MOTOR_04_05_V1.json').write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding='utf-8')

    string = {'type': 'string', 'minLength': 1}
    nullable_string = {'type': ['string', 'null']}
    metric = {'type': ['number', 'null'], 'minimum': 0}
    state = {'enum': ['UNKNOWN', 'PROPOSED', 'CONFIRMED', 'CONFLICT', 'EXCLUDED']}
    defs = {
        'point': obj({'x': {'type': 'number'}, 'y': {'type': 'number'}}),
        'polygon': obj({'outer': {'type': 'array', 'minItems': 3, 'items': ref('point')},
                        'holes': array({'type': 'array', 'minItems': 3, 'items': ref('point')})}),
        'evidence': obj({'source': {'enum': ['DOCUMENT', 'USER', 'AI', 'RULE']},
                         'sourceId': nullable_string, 'entityIds': array(string),
                         'confidence': {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1},
                         'ruleId': nullable_string}),
    }
    common = {'id': string, 'state': state, 'evidence': array(ref('evidence'))}
    nullable_polygon = {'anyOf': [ref('polygon'), {'type': 'null'}]}
    defs['level'] = obj({**common, 'key': string, 'order': {'type': 'integer'},
                         'elevationM': {'type': ['number', 'null']}, 'heightM': metric})
    defs['space'] = obj({**common, 'levelId': string, 'usage': nullable_string,
                         'geometryM': nullable_polygon, 'wallIds': array(string),
                         'intervention': {'enum': ['NEW', 'RETAIN', 'DEMOLISH', 'MODIFY', 'UNKNOWN']},
                         'finishes': array(ref('surface'))})
    defs['surface'] = obj({'id': string, 'side': {'enum': ['FLOOR', 'CEILING', 'LEFT', 'RIGHT', 'ROOF']},
                           'material': nullable_string, 'finish': nullable_string,
                           'coverageHeightM': metric, 'state': state})
    defs['wall'] = obj({**common, 'levelId': string, 'startM': ref('point'), 'endM': ref('point'),
                        'heightM': metric, 'thicknessM': metric, 'material': nullable_string,
                        'structuralRole': {'enum': ['LOAD_BEARING', 'PARTITION', 'UNKNOWN']},
                        'spaceIds': array(string), 'openingIds': array(string), 'finishes': array(ref('surface'))})
    defs['opening'] = obj({**common, 'levelId': string,
        'kind': {'enum': ['DOOR', 'WINDOW', 'GARAGE_DOOR', 'OPEN_PASSAGE', 'UNKNOWN']},
        'hostWallId': nullable_string, 'hostBoundaryId': nullable_string,
        'offsetStartM': metric, 'offsetEndM': metric, 'heightM': metric, 'sillHeightM': metric,
        'usage': {'enum': ['INTERIOR', 'MAIN_ENTRANCE', 'VEHICLE_ACCESS', 'OTHER', 'UNKNOWN']},
        'operation': {'enum': ['HINGED', 'SLIDING', 'FOLDING', 'SECTIONAL', 'ROLLING', 'TILT_UP', 'FIXED', 'UNKNOWN']},
        'leafCount': {'type': ['integer', 'null'], 'minimum': 1},
        'material': nullable_string, 'glazing': nullable_string,
        'catalogCode': nullable_string,
        'catalogStatus': {'enum': ['MAPPED', 'UNMAPPED', 'REVIEW']}})
    defs['flight'] = obj({'id': string, 'pathM': {'type': 'array', 'minItems': 2, 'items': ref('point')},
                          'widthM': metric, 'riserCount': {'type': ['integer', 'null'], 'minimum': 1},
                          'riserHeightM': metric, 'treadDepthM': metric,
                          'slabThicknessM': metric})
    defs['stair'] = obj({**common, 'levelFromId': string, 'levelToId': string,
        'shape': {'enum': ['STRAIGHT', 'L', 'U', 'WINDER', 'SPIRAL', 'OTHER', 'UNKNOWN']},
        'footprintM': nullable_polygon, 'totalRiseM': metric, 'system': nullable_string,
        'flights': array(ref('flight')), 'landings': array(ref('polygon')),
        'slabVoidIds': array(string), 'railingIds': array(string),
        'catalogStatus': {'enum': ['MAPPED', 'UNMAPPED', 'REVIEW']}})
    defs['element'] = obj({**common, 'levelId': string,
        'kind': {'enum': ['FOOTING', 'FOUNDATION_STRIP', 'FOUNDATION_WALL', 'GRADE_BEAM', 'COLUMN', 'TIE_COLUMN', 'BEAM', 'SLAB', 'RAILING', 'EXCAVATION', 'FILL', 'FIXTURE', 'SERVICE_POINT']},
        'geometryM': nullable_polygon, 'pathM': array(ref('point')),
        'widthM': metric, 'heightM': metric, 'depthM': metric, 'material': nullable_string,
        'hostIds': array(string), 'system': nullable_string, 'catalogCode': nullable_string})
    defs['completeness'] = obj({key: {'enum': ['UNKNOWN', 'PARTIAL', 'COMPLETE', 'NOT_APPLICABLE']}
                                for key in ['spaces', 'walls', 'openings', 'stairs', 'structuralElements', 'finishes', 'services']})
    defs['issue'] = obj({'code': string, 'entityIds': array(string), 'conceptCodes': array(string),
                        'message': string, 'resolveIn': {'enum': ['02', '03', '04', 'CATALOG', 'ENGINE']}})
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
              'title': 'Quantia 04 to 05 canonical consumption contract - design draft',
              '$comment': 'DESIGN PROPOSAL. Not yet wired into production endpoints. Semantic geometry and references require a separate validator.',
              **obj({'schemaVersion': {'const': 'QUANTIA_04_05_CANONICAL_V1_DRAFT'},
                     'projectId': string, 'revision': string, 'geometrySha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                     'rulesVersion': string, 'catalogVersion': string,
                     'units': {'const': 'm'}, 'coordinateSystem': {'const': 'LOCAL_XY_DOWN_Z_UP'},
                     'context02': obj({'intervention': nullable_string, 'scope': nullable_string,
                                        'structuralSystem': nullable_string, 'foundationType': nullable_string, 'slabSystem': nullable_string}),
                     'levels': array(ref('level')), 'spaces': array(ref('space')), 'walls': array(ref('wall')),
                     'openings': array(ref('opening')), 'stairs': array(ref('stair')),
                     'elements': array(ref('element')), 'completeness': ref('completeness'),
                     'issues': array(ref('issue'))}), '$defs': defs}
    (OUT / 'CONTRATO_CONSUMO_04_05_V1.schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
    example = {'schemaVersion': 'QUANTIA_04_05_CANONICAL_V1_DRAFT',
               'projectId': 'EXAMPLE_ONLY', 'revision': 'draft-0', 'geometrySha256': '0' * 64,
               'rulesVersion': rules['rules_version'], 'catalogVersion': 'V1.8-CAT-DEFINITIVO',
               'units': 'm', 'coordinateSystem': 'LOCAL_XY_DOWN_Z_UP',
               'context02': dict.fromkeys(['intervention', 'scope', 'structuralSystem', 'foundationType', 'slabSystem']),
               **{key: [] for key in ['levels', 'spaces', 'walls', 'openings', 'stairs', 'elements']},
               'completeness': {key: 'UNKNOWN' for key in defs['completeness']['properties']},
               'issues': [{'code': 'EMPTY_EXAMPLE_NOT_READY', 'entityIds': [], 'conceptCodes': [],
                           'message': 'Template only. No actual project geometry.', 'resolveIn': '04'}]}
    (OUT / 'CONSUMO_04_05_V1.plantilla.json').write_text(json.dumps(example, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Generated design schema, template and {len(rows)}-concept requirements matrix in {OUT}')


if __name__ == '__main__':
    build()
