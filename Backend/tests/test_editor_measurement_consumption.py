from app.services.motor_simulation_service import _build_spatial_context, _resolve_required_inputs, _sum_confirmed_measure


def test_editor_assignment_consumed_and_invalidated_after_geometry_edit():
    entity = {"id": "S1", "areaM2": 12, "confirmed": True}
    name = "geometria_area_confirmada"
    spatial = {"espacios": [entity], "engineInputsByConcept": {"CIM-001": {name: [{
        "areaM2": 12, "scopeRef": "S1", "source": "EDITOR_ASSIGNMENT", "sourceSnapshot": dict(entity)
    }]}}}
    concept = {"code": "CIM-001", "engine_spec": {"parameter_rules": {"required_inputs": [name]}}}
    resolved = _resolve_required_inputs(concept, _build_spatial_context({}, spatial, {}))
    assert resolved["complete"]
    assert _sum_confirmed_measure(resolved["resolvedInputs"][name], "area") == 12
    entity["areaM2"] = 14
    resolved = _resolve_required_inputs(concept, _build_spatial_context({}, spatial, {}))
    assert resolved["missingInputs"] == [name]
    assert spatial["engineInputsByConcept"]["CIM-001"][name][0]["areaM2"] == 12
