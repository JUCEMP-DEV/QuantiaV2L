import test from "node:test";
import assert from "node:assert/strict";

import {
  buildProjectInputContext,
} from "../src/modules/vivienda/services/projectInputContextService.js";

test("builds 01/02 context with declared site area, shape and boundaries", () => {
  const result = buildProjectInputContext({
    registro: {
      ubicacion: {
        estado: "Michoacán",
        municipio: "Uruapan",
        localidad: "Centro",
        direccion: "Referencia",
      },
    },
    clasificacion: {
      tipoIntervencion: "obra_nueva",
    },
    alcance: {
      alcance: "obra_completa",
    },
    datosGeneralesObra: {
      areaTerrenoM2: "165",
      geometriaPredio: "varios_lados",
      colindanciasPredio: {
        frente: "Calle",
        fondo: "Propiedad particular",
      },
      sistemaEstructural: "tradicional",
      tipoCimentacion: "zapata_corrida",
      tipoLosa: "maciza",
      factorAjuste: 1,
      engineInputs: {
        modo_diseno: "subir_plano",
      },
    },
    preliminares: {
      topografia: "plana",
      condicionTerreno: "limpio",
      tipoAcceso: "facil",
      servicios: {
        agua: true,
        drenaje: false,
        energia: true,
      },
      configuracionInicial: {
        instalaciones: {
          agua: true,
          drenaje: false,
          energia: true,
          gas: null,
          telecomunicaciones: true,
        },
      },
    },
  });

  assert.equal(result.contract_version, "PROJECT_INPUT_CONTEXT_V1");
  assert.equal(result.source, "USER_DECLARED");
  assert.equal(result.site.area_m2, 165);
  assert.equal(result.site.geometry_type, "POLYGONAL");
  assert.equal(result.site.boundaries.front, "Calle");
  assert.equal(result.site.boundaries.rear, "Propiedad particular");
  assert.equal(result.site_conditions.services.drenaje, false);
  assert.equal(result.site_conditions.services.telecomunicaciones, true);
  assert.equal("engineInputs" in result, false);
  assert.equal(JSON.stringify(result).includes("factorAjuste"), false);
  assert.ok(
    result.evidence.some(
      (item) =>
        item.field === "site.area_m2" &&
        item.evidence_type === "USER_DECLARED" &&
        item.source_interface === "02",
    ),
  );
});

test("does not convert missing or default data into evidence", () => {
  const result = buildProjectInputContext({
    datosGeneralesObra: {
      areaTerrenoM2: "",
      geometriaPredio: "",
      factorAjuste: 1,
      engineInputs: {
        sistema_estructural: "default",
      },
    },
    preliminares: {
      servicios: {
        agua: null,
      },
    },
  });

  assert.equal(result.site, undefined);
  assert.equal(result.location, undefined);
  assert.equal(result.project, undefined);
  assert.equal(result.construction, undefined);
  assert.equal(result.site_conditions, undefined);
  assert.equal(result.evidence, undefined);
});
