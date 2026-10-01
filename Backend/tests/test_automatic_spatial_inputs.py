import copy
import json
from pathlib import Path

from app.services.spatial_quantity_inputs import automatic_spatial_inputs
from app.services import motor_simulation_service as motor


def model():
    return {
        'niveles': [{'id': 'L0', 'key': 'planta_baja'}, {'id': 'L1', 'key': 'segunda_planta'}],
        'espacios': [{'id': 'S1', 'levelId': 'L0', 'confirmed': True,
                      'geometry': {'vertices': [{'x': 0, 'y': 0}, {'x': 5, 'y': 0}, {'x': 5, 'y': 4}, {'x': 0, 'y': 4}]}}],
        'muros': [{'id': 'W1', 'levelId': 'L0', 'confirmed': True, 'structuralRole': 'LOAD_BEARING', 'start': {'x': 0, 'y': 0}, 'end': {'x': 5, 'y': 0}}],
    }


CONTEXT = {'tipoIntervencion': 'obra_nueva', 'sistemaEstructural': 'tradicional', 'tipoCimentacion': 'mamposteria_corrida'}


def test_infers_geometry_without_manual_concept_inputs_and_deduplicates():
    spatial = model()
    spatial['espacios'].append({**copy.deepcopy(spatial['espacios'][0]), 'id': 'S_DUP'})
    wall = spatial['muros'][0]
    spatial['muros'].append({**wall, 'id': 'W_DUP', 'start': wall['end'], 'end': wall['start']})
    inputs, audit = automatic_spatial_inputs(spatial, CONTEXT)
    assert inputs['CIM-008']['geometria_area_confirmada'][0]['areaM2'] == 20
    assert inputs['CIM-006']['geometria_longitud_confirmada'][0]['longitudM'] == 5
    assert inputs['CIM-005']['tramos_dala_desplante_confirmados'][0]['entityIds'] == ['W1', 'W_DUP']
    assert 'CIM-001' not in inputs  # No foundation width was supplied.
    assert 'CIM-003' not in inputs  # No isolated footing geometry was supplied.
    assert all(entry['status'] == 'PROPOSED' for entry in audit)


def test_scope_and_recalculation():
    spatial = model()
    first, _ = automatic_spatial_inputs(spatial, CONTEXT)
    spatial['muros'][0]['end']['x'] = 6
    second, _ = automatic_spatial_inputs(spatial, CONTEXT)
    assert first['CIM-006']['geometria_longitud_confirmada'][0]['longitudM'] == 5
    assert second['CIM-006']['geometria_longitud_confirmada'][0]['longitudM'] == 6
    spatial['muros'][0]['levelId'] = 'L1'
    third, _ = automatic_spatial_inputs(spatial, CONTEXT)
    assert 'CIM-006' not in third
    assert automatic_spatial_inputs(spatial, {**CONTEXT, 'tipoIntervencion': 'remodelacion'})[0] == {}


def test_unconfirmed_and_raster_only_are_not_metric_geometry():
    spatial = model()
    spatial['muros'][0]['confirmed'] = False
    spatial['espacios'][0]['geometry'] = {'raster': spatial['espacios'][0]['geometry']}
    assert automatic_spatial_inputs(spatial, CONTEXT)[0] == {}


def test_real_engine_rule_consumes_04_without_frontend_mapping(monkeypatch):
    rules = json.loads((Path(__file__).parents[1] / 'data/engine/Reglas_Motor_Inferencia_Quantia_V2_V1_8_DEFINITIVAS.json').read_text(encoding='utf-8-sig'))
    rule = next(r for r in rules['concept_rules'] if r['code'] == 'CIM-008')
    concept = {'id': rule['concept_id'], 'code': rule['code'], 'is_active': True,
               'unit_code': 'M2', 'unit_symbol': 'm2', 'unit_price': 10, 'technical_description': 'Firme',
               'engine_spec': rule['spec'], 'activation_rule': rule['activation_rule']}
    monkeypatch.setattr(motor, '_fetch_catalog_concepts', lambda *args, **kwargs: [concept])
    result = motor.simulate_modulo(module_key='cimentacion', controles=CONTEXT, estructura_espacial=model())
    row = next(x for x in result['availableConcepts'] if x['key'] == 'CIM-008')
    assert row['quantity'] == 20
    assert row['status'] == 'PROPOSED'
    assert result['contextSnapshot']['geometryInference']
    spatial = model()
    spatial['engineInputsByConcept'] = {'CIM-008': {'geometria_area_confirmada': [{'areaM2': 8, 'scopeRef': 'explicit'}]}}
    result = motor.simulate_modulo(module_key='cimentacion', controles=CONTEXT, estructura_espacial=spatial)
    assert result['availableConcepts'][0]['quantity'] == 8
    assert not any(r['concept'] == 'CIM-008' for r in result['contextSnapshot']['geometryInference'])
