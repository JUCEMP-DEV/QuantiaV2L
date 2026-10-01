import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.v1.endpoints.motor import router
from app.services.spatial_consumption import build_consumption, inspect_spatial
from app.services.spatial_quantity_inputs import automatic_spatial_inputs
from app.services import motor_simulation_service as motor

CONTEXT = {'tipoIntervencion': 'obra_nueva', 'sistemaEstructural': 'tradicional', 'tipoCimentacion': 'mamposteria_corrida'}


def model():
    wall = {'id': 'W', 'levelId': 'L0', 'confirmed': True, 'start': {'x': 0, 'y': 0}, 'end': {'x': 12, 'y': 0},
            'heightM': 3, 'thicknessM': .15, 'material': 'BRICK', 'structuralRole': 'LOAD_BEARING'}
    opening = {'wallId': 'W', 'levelId': 'L0', 'confirmed': True, 'heightM': 2.1, 'widthM': 1, 'operation': 'HINGED'}
    return {'sourceMode': 'manual', 'units': 'm', 'niveles': [{'id': 'L0', 'key': 'planta_baja', 'heightM': 3, 'elevationM': 0}, {'id': 'L1', 'key': 'segunda_planta', 'elevationM': 3}],
            'muros': [wall], 'espacios': [], 'completeness': {'openings': 'COMPLETE', 'stairs': 'COMPLETE'},
            'puertas': [{**opening, 'id': 'D', 'kind': 'DOOR', 'position': .1, 'material': 'WOOD', 'usage': 'INTERIOR'},
                        {**opening, 'id': 'A', 'kind': 'DOOR', 'position': .3, 'material': 'ALUMINUM', 'glazing': 'GLASS', 'usage': 'MAIN_ENTRANCE'},
                        {**opening, 'id': 'G', 'kind': 'GARAGE_DOOR', 'position': .6, 'widthM': 3, 'material': 'STEEL', 'usage': 'VEHICLE_ACCESS'}],
            'ventanas': [{**opening, 'id': 'V', 'kind': 'WINDOW', 'position': .9, 'widthM': 1.2, 'heightM': 1, 'sillHeightM': 1, 'material': 'ALUMINUM', 'glazing': 'GLASS'}],
            'escaleras': [{'id': 'S', 'confirmed': True, 'levelFromId': 'L0', 'levelToId': 'L1', 'type': 'STRAIGHT', 'system': 'CONCRETE',
                'hasSlabVoid': True, 'railingSide': 'LEFT', 'railingMaterial': 'STEEL',
                'geometry': {'vertices': [{'x': 0, 'y': 1}, {'x': 1, 'y': 1}, {'x': 1, 'y': 5}, {'x': 0, 'y': 5}]},
                'flights': [{'id': 'F', 'widthM': 1, 'riserCount': 18, 'pathM': [{'x': .5, 'y': 1}, {'x': .5, 'y': 5}]}]}]}


def test_delivery_is_deterministic_retains_unmapped_elements_and_recalculates():
    spatial = model()
    result = build_consumption(spatial, {}, CONTEXT)
    inputs = result['derivedInputsByConcept']
    assert inputs['CAN-001']['dimensiones_ventanas_confirmadas'][0]['areaM2'] == 1.2
    assert inputs['CAR-001']['cantidad_piezas_confirmada'][0]['cantidad'] == 1
    assert inputs['CAN-002']['cantidad_piezas_confirmada'][0]['cantidad'] == 1
    assert 'CAR-002' not in inputs  # aluminum main entrance is not counted twice
    assert inputs['HER-002']['tramos_barandal_confirmados'][0]['longitudM'] == 5
    assert next(o for o in result['openings'] if o['id'] == 'G')['catalogStatus'] == 'UNMAPPED'
    assert result['stairs'][0]['slabVoids'][0]['levelId'] == 'L1'
    assert result['stairs'][0]['totalRiseM'] == 3
    assert spatial == model()  # no mutation
    assert build_consumption(spatial, {}, CONTEXT)['modelSha256'] == result['modelSha256']
    spatial['ventanas'][0]['widthM'] = 1.4
    updated = build_consumption(spatial, {}, CONTEXT)
    assert updated['modelSha256'] != result['modelSha256']
    assert updated['derivedInputsByConcept']['CAN-001']['dimensiones_ventanas_confirmadas'][0]['areaM2'] == 1.4


def test_invalid_unknown_or_duplicate_openings_never_produce_silent_partial_counts():
    for mutate in [lambda s: s['completeness'].update(openings='UNKNOWN'),
                   lambda s: s['puertas'][0].update(wallId='missing'),
                   lambda s: s['puertas'][0].update(confirmed=False),
                   lambda s: s['ventanas'][0].update(sillHeightM=2.8),
                   lambda s: s['puertas'].append(copy.deepcopy(s['puertas'][0]))]:
        spatial = model(); mutate(spatial)
        result = build_consumption(spatial, {}, CONTEXT)
        assert not {'CAN-001', 'CAN-002', 'CAR-001', 'CAR-002'} & result['derivedInputsByConcept'].keys()
        assert result['issues']


def test_wall_face_overlap_and_unknown_structural_role():
    spatial = model()
    spatial['ventanas'][0].update(position=.1, widthM=1, heightM=.5, sillHeightM=2.2)
    assert not any(i['code'] == 'OVERLAPPING_OPENINGS' for i in inspect_spatial(spatial)[1])
    spatial['ventanas'][0]['sillHeightM'] = 1
    assert any(i['code'] == 'OVERLAPPING_OPENINGS' for i in inspect_spatial(spatial)[1])
    spatial['muros'][0]['structuralRole'] = 'UNKNOWN'
    assert 'CIM-005' not in automatic_spatial_inputs(spatial, CONTEXT)[0]
    spatial['muros'][0].update(structuralRole='PARTITION', loadBearing=True)
    assert 'CIM-005' not in automatic_spatial_inputs(spatial, CONTEXT)[0]


def test_floor_finish_is_not_assumed_from_a_polygon():
    spatial = model()
    spatial['espacios'] = [{'id': 'ROOM', 'levelId': 'L0', 'confirmed': True,
        'geometry': {'vertices': [{'x': 0, 'y': 0}, {'x': 4, 'y': 0}, {'x': 4, 'y': 3}, {'x': 0, 'y': 3}]}}]
    assert 'ACA-001' not in automatic_spatial_inputs(spatial, CONTEXT)[0]
    spatial['espacios'][0]['finishes'] = [{'side': 'FLOOR', 'finish': 'CERAMIC', 'state': 'CONFIRMED'}]
    assert automatic_spatial_inputs(spatial, CONTEXT)[0]['ACA-001']['geometria_area_confirmada'][0]['areaM2'] == 12


def test_export_endpoint_and_actual_rules_consume_the_same_model(monkeypatch):
    spatial = model()
    app = FastAPI(); app.include_router(router)
    response = TestClient(app).post('/motor/consumo-04', json={'estructuraEspacial': spatial, 'controles': CONTEXT})
    assert response.status_code == 200
    exported = response.json()
    rules = json.loads((Path(__file__).parents[1] / 'data/engine/Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json').read_text(encoding='utf-8-sig'))
    for code, quantity in [('CAN-001', 1.2), ('CAN-002', 1), ('CAR-001', 1), ('HER-002', 5)]:
        rule = next(r for r in rules['concept_rules'] if r['code'] == code)
        concept = {'id': rule['concept_id'], 'code': code, 'is_active': True,
                   'unit_code': rule['activation_rule']['derivation_json']['unit'], 'unit_symbol': rule['activation_rule']['derivation_json']['unit'],
                   'unit_price': 10, 'technical_description': code, 'engine_spec': rule['spec'], 'activation_rule': rule['activation_rule']}
        monkeypatch.setattr(motor, '_fetch_catalog_concepts', lambda *args, c=concept, **kwargs: [c])
        result = motor.simulate_modulo(module_key='acabados', controles=CONTEXT, estructura_espacial=spatial)
        row = next(r for r in result['availableConcepts'] if r['key'] == code)
        assert row['quantity'] == quantity, row
        assert result['contextSnapshot']['consumption04']['modelSha256'] == exported['modelSha256']
