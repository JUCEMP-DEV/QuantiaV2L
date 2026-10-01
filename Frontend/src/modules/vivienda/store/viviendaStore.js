import { defineStore } from "pinia";
import { receiveSpatialAnalysis } from "../editor/adapters/spatialWorkflowContract.js";
import { readReglasCatalogosV4 } from "@/modules/vivienda/services/viviendaService";
import { validateSpatialRelations } from "@/modules/vivienda/services/spatialRelationsService";

const MODULE_ORDER = [
  "cimentacion",
  "estructura",
  "albanileria",
  "instalaciones",
  "acabados",
  "complementarios_y_equipamiento",
];

const EDITOR_SPATIAL_SCHEMA_VERSION = "quantia-editor-1.0";

const ALCANCE_MODULES_OBRA_NUEVA = {
  obra_negra: ["cimentacion", "estructura", "albanileria"],
  obra_gris: ["cimentacion", "estructura", "albanileria", "instalaciones"],
  obra_completa: [...MODULE_ORDER],
  obra_blanca: [...MODULE_ORDER],
};

function normalizeModuleKey(value) {
  const raw = String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, "_")
    .replace(/-+/g, "_");

  if (raw === "complementarios") {
    return "complementarios_y_equipamiento";
  }

  return MODULE_ORDER.includes(raw) ? raw : "";
}

function normalizeModuleList(list = []) {
  const seen = new Set();
  const result = [];

  for (const item of Array.isArray(list) ? list : []) {
    const normalized = normalizeModuleKey(item);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    result.push(normalized);
  }

  return result;
}

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function emptyRegistro() {
  return {
    prestador: {
      nombre: "",
      telefono: "",
      profesion: "",
      alias: "",
    },

    cliente: {
      nombre: "",
      telefono: "",
      correo: "",
      ubicacion: "",
    },

    ubicacion: {
      estado: "",
      municipio: "",
      localidad: "",
      direccion: "",
    },

    proyecto: {
      nombre: "",
      folio: "",
      fecha: "",
    },

    terminosAceptados: false,
  };
}

function emptyClasificacion() {
  return {
    tipoIntervencion: "",
    nivelAcabado: "",
    arquitecturaVersion: "v4",
  };
}

function emptyAlcance() {
  return {
    tipoIntervencion: "",
    alcance: "",
    subalcances: [],
    restricciones: {},
    partidasSeleccionadas: [],
    modulosActivos: [],
    activacionModo: "",
  };
}

function emptyPreliminares() {
  return {
    tipoIntervencion: "",
    alcanceSeleccionado: "",
    areaPreliminares: "",
    superficiePreliminar: "",
    tipoAcceso: "",
    condicionTerreno: "",
    topografia: "",
    pendienteProfundidadM: "",
    servicios: {
      agua: null,
      energia: null,
      drenaje: null,
    },
    engineInputs: {},
    engineInputsByConcept: {},
    demolicion: {
      tipoDemolicion: "",
      tipoEstructuraExistente: "",
      nivelesExistentes: "",
      anchoDemolicionM: "",
      largoDemolicionM: "",
      areaDemolicionM2: "",
      volumenDemolicion: "",
    },
    observaciones: "",
    conceptosActivos: [],
    technicalConcepts: [],
    officialSummary: [],
    pendingDefinitions: [],
    costoEstimado: 0,
  };
}

function emptyResultado() {
  return {
    resultadoFinal: 0,
    desglose: {
      technicalConcepts: [],
      officialSummary: [],
    },
    metadata: {
      perfilSalida: "",
      motorVersion: "",
      factorAjusteAplicado: 1,
      pendingDefinitions: [],
    },
    fechaSimulacion: "",
    estadoResultado: "pendiente",
  };
}

function emptyDatosGeneralesObra() {
  return {
    ubicacionProyecto: "",
    anchoTerrenoM: "",
    largoTerrenoM: "",
    areaTerrenoM2: "",
    areaConstruccionPropuestaM2: "",
    areaConstruccionM2: "",
    niveles: "",
    alturaNivel1M: "",
    alturaNivel2M: "",
    alturaNivel3M: "",
    alturaPromedioM: "",
    sistemaEstructural: "",
    tipoCimentacion: "",
    nivelComplejidad: "",
    condicionesEspeciales: "",
    factorAjuste: 1,
    notas: "",
    engineInputs: {},
    engineInputsByConcept: {},
  };
}

function toComparableDatosGeneralesObra(payload = {}) {
  const text = (value) => String(value ?? "").trim();

  const number = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  return {
    ubicacionProyecto: text(payload.ubicacionProyecto),
    anchoTerrenoM: number(payload.anchoTerrenoM),
    largoTerrenoM: number(payload.largoTerrenoM),
    areaTerrenoM2: number(payload.areaTerrenoM2),
    areaConstruccionPropuestaM2: number(
      payload.areaConstruccionPropuestaM2
    ),
    areaConstruccionM2: number(payload.areaConstruccionM2),
    niveles: number(payload.niveles),
    alturaNivel1M: number(payload.alturaNivel1M),
    alturaNivel2M: number(payload.alturaNivel2M),
    alturaNivel3M: number(payload.alturaNivel3M),
    alturaPromedioM: number(payload.alturaPromedioM),
    sistemaEstructural: text(payload.sistemaEstructural),
    tipoCimentacion: text(payload.tipoCimentacion),
    nivelComplejidad: text(payload.nivelComplejidad),
    condicionesEspeciales: text(payload.condicionesEspeciales),
    factorAjuste: number(payload.factorAjuste),
    notas: text(payload.notas),
    engineInputs: JSON.stringify(payload.engineInputs || {}),
    engineInputsByConcept: JSON.stringify(
      payload.engineInputsByConcept || {}
    ),
  };
}

function toComparablePreliminares(payload = {}) {
  const text = (value) => String(value ?? "").trim();

  const number = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const demolicion = payload.demolicion || {};

  return {
    tipoIntervencion: text(payload.tipoIntervencion),
    alcanceSeleccionado: text(payload.alcanceSeleccionado),

    areaPreliminares: number(
      payload.areaPreliminares ||
      payload.superficiePreliminar
    ),

    tipoAcceso: text(payload.tipoAcceso),
    condicionTerreno: text(payload.condicionTerreno),
    topografia: text(payload.topografia),
    pendienteProfundidadM: number(payload.pendienteProfundidadM),
    tipoDemolicion: text(demolicion.tipoDemolicion),
    tipoEstructuraExistente: text(
      demolicion.tipoEstructuraExistente
    ),
    nivelesExistentes: number(demolicion.nivelesExistentes),
    anchoDemolicionM: number(demolicion.anchoDemolicionM),
    largoDemolicionM: number(demolicion.largoDemolicionM),
    engineInputs: JSON.stringify(payload.engineInputs || {}),
    engineInputsByConcept: JSON.stringify(
      payload.engineInputsByConcept || {}
    ),
  };
}

function emptyVariablesEntrada() {
  return {
    ubicacionProyecto: "",
    nivelComplejidad: "",
    condicionesEspeciales: "",
    factorAjuste: 1,
    notas: "",
  };
}

function emptyEstructuraEspacial() {
  return {
    schemaVersion: EDITOR_SPATIAL_SCHEMA_VERSION,

    projectId: null,
    activeLevelId: null,
    sourceMode: "",

    metadata: {
      sourceMode: "",
      createdAt: "",
      updatedAt: "",
    },

    terreno: null,

    niveles: [],
    espacios: [],
    muros: [],
    puertas: [],
    ventanas: [],
    escaleras: [],
    anotaciones: [],

    validacion: {
      isValid: false,
      conflicts: [],
      warnings: [],
      lastValidatedAt: "",
    },

    observaciones: "",
    engineInputs: {},
    engineInputsByConcept: {},
  };
}

function normalizeEstructuraEspacial(payload = {}) {
  payload = receiveSpatialAnalysis(payload);
  const source =
    payload && typeof payload === "object"
      ? payload
      : {};

  const base = emptyEstructuraEspacial();

  const metadata =
    source.metadata &&
    typeof source.metadata === "object"
      ? source.metadata
      : {};

  const validacion =
    source.validacion &&
    typeof source.validacion === "object"
      ? source.validacion
      : {};

  return {
    ...base,
    ...source,

    schemaVersion:
      String(
        source.schemaVersion ||
        EDITOR_SPATIAL_SCHEMA_VERSION
      ).trim() ||
      EDITOR_SPATIAL_SCHEMA_VERSION,

    projectId:
      source.projectId ?? null,

    activeLevelId:
      source.activeLevelId ?? null,

    sourceMode:
      String(
        source.sourceMode ||
        metadata.sourceMode ||
        ""
      ).trim(),

    metadata: {
      ...base.metadata,
      ...metadata,

      sourceMode:
        String(
          metadata.sourceMode ||
          source.sourceMode ||
          ""
        ).trim(),

      createdAt:
        String(
          metadata.createdAt || ""
        ).trim(),

      updatedAt:
        String(
          metadata.updatedAt || ""
        ).trim(),
    },

    terreno:
      source.terreno &&
      typeof source.terreno === "object"
        ? source.terreno
        : null,

    niveles:
      Array.isArray(source.niveles)
        ? source.niveles
        : [],

    espacios:
      Array.isArray(source.espacios)
        ? source.espacios
        : [],

    muros:
      Array.isArray(source.muros)
        ? source.muros
        : [],

    puertas:
      Array.isArray(source.puertas)
        ? source.puertas
        : [],

    ventanas:
      Array.isArray(source.ventanas)
        ? source.ventanas
        : [],

    escaleras:
      Array.isArray(source.escaleras)
        ? source.escaleras
        : [],

    anotaciones:
      Array.isArray(source.anotaciones)
        ? source.anotaciones
        : [],

    validacion: {
      ...base.validacion,
      ...validacion,

      isValid:
        validacion.isValid === true,

      conflicts:
        Array.isArray(
          validacion.conflicts
        )
          ? validacion.conflicts
          : [],

      warnings:
        Array.isArray(
          validacion.warnings
        )
          ? validacion.warnings
          : [],

      lastValidatedAt:
        String(
          validacion.lastValidatedAt ||
          ""
        ).trim(),
    },

    observaciones:
      String(
        source.observaciones || ""
      ),

    engineInputs:
      source.engineInputs &&
      typeof source.engineInputs === "object"
        ? source.engineInputs
        : {},

    engineInputsByConcept:
      source.engineInputsByConcept &&
      typeof source.engineInputsByConcept === "object"
        ? source.engineInputsByConcept
        : {},
  };
}

function emptyColindanciasRecorrido() {
  return {
    relaciones: [],
    inconsistencias: [],

    resumen: {
      spacesCount: 0,
      relationRowsCount: 0,
      internalLinks: 0,
      reciprocalLinks: 0,
      brokenLinks: 0,
      coverageRatio: 0,
    },

    observaciones: "",
  };
}

function emptyValidacionEspacial() {
  return {
    coherenciaArea: false,
    coherenciaVolumetria: false,
    revisado: false,
    observaciones: "",
    alertas: [],
  };
}

function emptyRevisionInferencia() {
  return {
    revisado: false,
    observaciones: "",

    snapshot: {
      conceptosActivados: 0,
      reglasAplicadas: 0,
      pendientes: [],
    },
  };
}

function emptyModuleRow() {
  return {
    capturado: false,
    noApplicable: false,
    controles: {},
    selectedConceptKeys: [],
    selectedConcepts: [],
    summaryByPartida: [],
    proposedConcepts: [],
    blockedConcepts: [],
    notApplicableConcepts: [],
    inactiveConcepts: [],
    activationCoverage: {},
    costoEstimado: 0,
  };
}

function emptyModulos() {
  return {
    cimentacion: emptyModuleRow(),
    estructura: emptyModuleRow(),
    albanileria: emptyModuleRow(),
    instalaciones: emptyModuleRow(),
    acabados: emptyModuleRow(),
    complementarios_y_equipamiento:
      emptyModuleRow(),
  };
}

function getOrderedRequiredModules(state) {
  if (
    state.clasificacion.tipoIntervencion ===
    "obra_nueva"
  ) {
    const alcanceKey = String(
      state.alcance?.alcance || ""
    ).trim();

    const byScope =
      ALCANCE_MODULES_OBRA_NUEVA[
        alcanceKey
      ];

    if (
      Array.isArray(byScope) &&
      byScope.length > 0
    ) {
      return [...byScope];
    }

    return [...MODULE_ORDER];
  }

  const active = normalizeModuleList(
    state.alcance.modulosActivos || []
  );

  if (active.length > 0) {
    const ordered =
      MODULE_ORDER.filter((key) =>
        active.includes(key)
      );

    if (ordered.length > 0) {
      return ordered;
    }
  }

  return [];
}

function isModuloRequiredState(
  state,
  key
) {
  const normalizedKey =
    normalizeModuleKey(key);

  return normalizedKey
    ? getOrderedRequiredModules(
        state
      ).includes(normalizedKey)
    : false;
}

export const useViviendaStore =
  defineStore("vivienda", {
    state: () => ({
      projectPersistence: { id: null, userId: null },
      registro:
        emptyRegistro(),

      clasificacion:
        emptyClasificacion(),

      alcance:
        emptyAlcance(),

      preliminares:
        emptyPreliminares(),

      modulos:
        emptyModulos(),

      datosGeneralesObra:
        emptyDatosGeneralesObra(),

      variablesEntrada:
        emptyVariablesEntrada(),

      estructuraEspacial:
        emptyEstructuraEspacial(),

      colindanciasRecorrido:
        emptyColindanciasRecorrido(),

      validacionEspacial:
        emptyValidacionEspacial(),

      revisionInferencia:
        emptyRevisionInferencia(),

      resumenConfirmado:
        false,

      resultado:
        emptyResultado(),

      reglasSnapshot: {
        reglas: [],
        catalogos: [],
        errors: [],
        loaded: false,
      },
    }),

    getters: {
      acumuladoPreliminares:
        (state) =>
          Number(
            toNumber(
              state.preliminares
                ?.costoEstimado,
              0
            ).toFixed(2)
          ),

      acumuladoModulos:
        (state) => {
          const keys =
            Object.keys(
              state.modulos || {}
            );

          const total =
            keys.reduce(
              (acc, key) =>
                acc +
                toNumber(
                  state.modulos?.[key]
                    ?.costoEstimado,
                  0
                ),
              0
            );

          return Number(
            total.toFixed(2)
          );
        },

      acumuladoGlobal() {
        return Number(
          (
            toNumber(
              this.acumuladoPreliminares,
              0
            ) +
            toNumber(
              this.acumuladoModulos,
              0
            )
          ).toFixed(2)
        );
      },
    },

    actions: {
      setRegistro(payload) {
        const previous =
          JSON.stringify(
            this.registro
          );

        const next = {
          ...emptyRegistro(),
          ...payload,
        };

        this.registro = next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.resetFrom(
            "clasificacion"
          );
        }
      },

      setClasificacion(payload) {
        const previousTipoIntervencion =
          String(
            this.clasificacion
              ?.tipoIntervencion ||
            ""
          ).trim();

        const previous =
          JSON.stringify(
            this.clasificacion
          );

        const next = {
          ...emptyClasificacion(),
          ...payload,
        };

        this.clasificacion =
          next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.alcance =
            emptyAlcance();

          console.info(
            "[TRACE][STORE][ESCENARIO][CLASIFICACION]",
            {
              previousTipoIntervencion,

              nextTipoIntervencion:
                String(
                  next.tipoIntervencion ||
                  ""
                ).trim(),

              resetDesde:
                "preliminares",
            }
          );

          this.resetFrom(
            "preliminares"
          );
        }
      },

      setAlcance(payload) {
        const previousAlcanceKey =
          String(
            this.alcance?.alcance ||
            ""
          ).trim();

        const previousModulosActivos =
          normalizeModuleList(
            this.alcance
              ?.modulosActivos ||
            []
          );

        const previous =
          JSON.stringify(
            this.alcance
          );

        const nextRaw = {
          ...emptyAlcance(),
          ...payload,
        };

        const tipoIntervencion =
          String(
            nextRaw
              .tipoIntervencion ||
            this.clasificacion
              .tipoIntervencion ||
            ""
          ).trim();

        const alcanceKey =
          String(
            nextRaw.alcance || ""
          ).trim();

        const derivedByScope =
          tipoIntervencion ===
          "obra_nueva"
            ? ALCANCE_MODULES_OBRA_NUEVA[
                alcanceKey
              ] ||
              [...MODULE_ORDER]
            : null;

        const next = {
          ...nextRaw,

          partidasSeleccionadas:
            normalizeModuleList(
              nextRaw
                .partidasSeleccionadas
            ),

          modulosActivos:
            normalizeModuleList(
              derivedByScope ||
              nextRaw.modulosActivos
            ),

          subalcances:
            normalizeModuleList(
              nextRaw.subalcances
            ),
        };

        this.alcance = next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          console.info(
            "[TRACE][STORE][ESCENARIO][ALCANCE]",
            {
              previousAlcance:
                previousAlcanceKey,

              nextAlcance:
                alcanceKey,

              previousModulosActivos,

              nextModulosActivos:
                next.modulosActivos,

              resetDesde:
                "preliminares",
            }
          );

          this.resetFrom(
            "preliminares"
          );
        }
      },

      setPreliminares(payload) {
        const previousComparable =
          toComparablePreliminares(
            this.preliminares
          );

        const next = {
          ...emptyPreliminares(),
          ...payload,
        };

        const nextComparable =
          toComparablePreliminares(
            next
          );

        this.preliminares =
          next;

        console.info(
          "[TRACE][PRELIMINARES][SAVE]",
          {
            costoBloque:
              Number(
                toNumber(
                  next.costoEstimado,
                  0
                ).toFixed(2)
              ),

            conceptosTecnicos:
              Array.isArray(
                next.technicalConcepts
              )
                ? next
                    .technicalConcepts
                    .length
                : 0,

            partidas:
              Array.isArray(
                next.officialSummary
              )
                ? next
                    .officialSummary
                    .length
                : 0,

            acumuladoGlobal:
              Number(
                (
                  toNumber(
                    next.costoEstimado,
                    0
                  ) +
                  toNumber(
                    this
                      .acumuladoModulos,
                    0
                  )
                ).toFixed(2)
              ),
          }
        );

        if (
          JSON.stringify(
            previousComparable
          ) !==
          JSON.stringify(
            nextComparable
          )
        ) {
          this.resetFrom(
            "modulos"
          );
        }
      },

      setModuloData(
        key,
        payload
      ) {
        const normalizedKey =
          normalizeModuleKey(key);

        if (
          !normalizedKey ||
          !this.modulos[
            normalizedKey
          ]
        ) {
          return false;
        }

        const previous =
          JSON.stringify(
            this.modulos[
              normalizedKey
            ]
          );

        const noApplicable =
          payload
            ?.noApplicable === true;

        const selectedConcepts =
          Array.isArray(
            payload
              ?.selectedConcepts
          )
            ? payload
                .selectedConcepts
                .map((item) => ({
                  ...item,
                }))
            : [];

        const summaryByPartida =
          Array.isArray(
            payload
              ?.summaryByPartida
          )
            ? payload
                .summaryByPartida
                .map((item) => ({
                  ...item,
                }))
            : [];

        const selectedTotal =
          selectedConcepts.reduce(
            (acc, item) =>
              acc +
              toNumber(
                item?.total,
                0
              ),
            0
          );

        const summaryTotal =
          summaryByPartida.reduce(
            (acc, item) =>
              acc +
              toNumber(
                item?.total,
                0
              ),
            0
          );

        const normalizedCost =
          Number(
            toNumber(
              payload
                ?.costoEstimado,
              0
            ).toFixed(2)
          );

        const base =
          Math.max(
            selectedTotal,
            summaryTotal,
            1
          );

        const mismatch =
          Math.abs(
            selectedTotal -
            summaryTotal
          ) / base;

        if (!noApplicable) {
          if (
            !selectedConcepts.length ||
            !summaryByPartida.length ||
            normalizedCost < 0
          ) {
            return false;
          }

          if (mismatch > 0.05) {
            return false;
          }

          if (
            normalizedCost + 0.01 <
            Math.max(
              selectedTotal,
              summaryTotal
            )
          ) {
            return false;
          }
        }

        const selectedConceptKeysRaw =
          Array.isArray(
            payload
              ?.selectedConceptKeys
          )
            ? payload
                .selectedConceptKeys
            : [];

        const selectedConceptKeys = [
          ...new Set(
            [
              ...selectedConceptKeysRaw,

              ...selectedConcepts.map(
                (item) =>
                  String(
                    item?.key || ""
                  )
              ),
            ].filter(Boolean)
          ),
        ];

        const next = {
          ...emptyModuleRow(),
          ...payload,

          noApplicable,

          selectedConceptKeys,

          selectedConcepts,

          summaryByPartida,

          costoEstimado:
            normalizedCost,

          capturado: true,
        };

        this.modulos[
          normalizedKey
        ] = next;

        console.info(
          "[TRACE][MODULO][SAVE]",
          {
            modulo:
              normalizedKey,

            costoBloque:
              normalizedCost,

            conceptos:
              selectedConcepts.length,

            partidas:
              summaryByPartida.length,

            noApplicable,

            acumuladoGlobal:
              Number(
                (
                  toNumber(
                    this
                      .acumuladoPreliminares,
                    0
                  ) +
                  toNumber(
                    this
                      .acumuladoModulos,
                    0
                  )
                ).toFixed(2)
              ),
          }
        );

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.resetFrom(
            "revision_inferencia"
          );
        }

        return true;
      },

      isModuloRequired(key) {
        return isModuloRequiredState(
          this.$state,
          key
        );
      },

      getRequiredModuleOrder() {
        return getOrderedRequiredModules(
          this.$state
        );
      },

      setDatosGeneralesObra(
        payload
      ) {
        const previous = {
          ...this
            .datosGeneralesObra,
        };

        const next = {
          ...emptyDatosGeneralesObra(),
          ...payload,
        };

        const previousComparable =
          toComparableDatosGeneralesObra(
            previous
          );

        const nextComparable =
          toComparableDatosGeneralesObra(
            next
          );

        const hasAnyChange =
          JSON.stringify(
            previousComparable
          ) !==
          JSON.stringify(
            nextComparable
          );

        if (!hasAnyChange) {
          return;
        }

        const structuralChanged =
          previousComparable
            .ubicacionProyecto !==
            nextComparable
              .ubicacionProyecto ||

          previousComparable
            .anchoTerrenoM !==
            nextComparable
              .anchoTerrenoM ||

          previousComparable
            .largoTerrenoM !==
            nextComparable
              .largoTerrenoM ||

          previousComparable
            .areaTerrenoM2 !==
            nextComparable
              .areaTerrenoM2 ||

          previousComparable
            .areaConstruccionPropuestaM2 !==
            nextComparable
              .areaConstruccionPropuestaM2 ||

          previousComparable
            .areaConstruccionM2 !==
            nextComparable
              .areaConstruccionM2 ||

          previousComparable
            .niveles !==
            nextComparable
              .niveles ||

          previousComparable
            .alturaNivel1M !==
            nextComparable
              .alturaNivel1M ||

          previousComparable
            .alturaNivel2M !==
            nextComparable
              .alturaNivel2M ||

          previousComparable
            .alturaNivel3M !==
            nextComparable
              .alturaNivel3M ||

          previousComparable
            .alturaPromedioM !==
            nextComparable
              .alturaPromedioM ||

          previousComparable
            .sistemaEstructural !==
            nextComparable
              .sistemaEstructural ||

          previousComparable
            .tipoCimentacion !==
            nextComparable
              .tipoCimentacion;

        this.datosGeneralesObra =
          next;

        this.variablesEntrada = {
          ...emptyVariablesEntrada(),

          ubicacionProyecto:
            next.ubicacionProyecto,

          nivelComplejidad:
            next.nivelComplejidad,

          condicionesEspeciales:
            next
              .condicionesEspeciales,

          factorAjuste:
            next.factorAjuste,

          notas:
            next.notas,
        };

        if (structuralChanged) {
          this.resetFrom(
            "estructura_espacial"
          );

          return;
        }

        this.resetFrom(
          "revision_inferencia"
        );
      },

      setVariablesEntrada(
        payload
      ) {
        this.setDatosGeneralesObra({
          ...this
            .datosGeneralesObra,
          ...payload,
        });
      },

      setEstructuraEspacial(
        payload
      ) {
        const previous =
          JSON.stringify(
            this.estructuraEspacial
          );

        const next =
          normalizeEstructuraEspacial(
            payload
          );

        this.estructuraEspacial =
          next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.resetFrom(
            "colindancias"
          );
        }
      },

      setColindanciasRecorrido(
        payload
      ) {
        const validation =
          validateSpatialRelations({
            espacios:
              this
                .estructuraEspacial
                .espacios || [],

            relaciones:
              payload
                ?.relaciones || [],
          });

        const previous =
          JSON.stringify(
            this
              .colindanciasRecorrido
          );

        const next = {
          ...emptyColindanciasRecorrido(),
          ...payload,

          relaciones:
            validation
              .normalizedRelations,

          inconsistencias:
            validation.issues,

          resumen:
            validation.summary,
        };

        this.colindanciasRecorrido =
          next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.resetFrom(
            "validacion_espacial"
          );
        }
      },

      setValidacionEspacial(
        payload
      ) {
        const previous =
          JSON.stringify(
            this.validacionEspacial
          );

        const next = {
          ...emptyValidacionEspacial(),
          ...payload,
        };

        this.validacionEspacial =
          next;

        if (
          previous !==
          JSON.stringify(next)
        ) {
          this.resetFrom(
            "modulos"
          );
        }
      },

      setRevisionInferencia(
        payload
      ) {
        this.revisionInferencia = {
          ...emptyRevisionInferencia(),
          ...payload,
        };

        this.resumenConfirmado =
          false;
      },

      confirmResumen() {
        this.resumenConfirmado =
          true;
      },

      setResultado(payload) {
        this.resultado = {
          resultadoFinal:
            payload
              .resultadoFinal ?? 0,

          desglose: {
            technicalConcepts:
              payload.desglose
                ?.technicalConcepts ||
              [],

            officialSummary:
              payload.desglose
                ?.officialSummary ||
              [],
          },

          metadata: {
            perfilSalida:
              payload.metadata
                ?.perfilSalida ||
              "",

            motorVersion:
              payload.metadata
                ?.motorVersion ||
              "",

            factorAjusteAplicado:
              payload.metadata
                ?.factorAjusteAplicado ||
              1,

            pendingDefinitions:
              payload.metadata
                ?.pendingDefinitions ||
              [],
          },

          fechaSimulacion:
            payload.fechaSimulacion ||
            new Date()
              .toISOString(),

          estadoResultado:
            payload
              .estadoResultado ||
            "generado",
        };
      },

      resetFrom(step) {
        const sequence = [
          "clasificacion",
          "alcance",
          "preliminares",
          "datos_generales",
          "estructura_espacial",
          "colindancias",
          "validacion_espacial",
          "modulos",
          "revision_inferencia",
          "resumen",
          "resultado",
        ];

        const stepIndex =
          sequence.indexOf(step);

        if (stepIndex < 0) {
          return;
        }

        console.info(
          "[TRACE][STORE][RESET_FROM]",
          {
            step,
            cleared:
              sequence.slice(
                stepIndex
              ),
          }
        );

        if (stepIndex <= 0) {
          this.clasificacion =
            emptyClasificacion();
        }

        if (stepIndex <= 1) {
          this.alcance =
            emptyAlcance();
        }

        if (stepIndex <= 2) {
          this.preliminares =
            emptyPreliminares();
        }

        if (stepIndex <= 3) {
          this.datosGeneralesObra =
            emptyDatosGeneralesObra();

          this.variablesEntrada =
            emptyVariablesEntrada();
        }

        if (stepIndex <= 4) {
          this.estructuraEspacial =
            emptyEstructuraEspacial();
        }

        if (stepIndex <= 5) {
          this.colindanciasRecorrido =
            emptyColindanciasRecorrido();
        }

        if (stepIndex <= 6) {
          this.validacionEspacial =
            emptyValidacionEspacial();
        }

        if (stepIndex <= 7) {
          this.modulos =
            emptyModulos();
        }

        if (stepIndex <= 8) {
          this.revisionInferencia =
            emptyRevisionInferencia();
        }

        if (stepIndex <= 9) {
          this.resumenConfirmado =
            false;
        }

        if (stepIndex <= 10) {
          this.resultado =
            emptyResultado();
        }
      },

      resetSimulation() {
        this.registro =
          emptyRegistro();

        this.clasificacion =
          emptyClasificacion();

        this.alcance =
          emptyAlcance();

        this.preliminares =
          emptyPreliminares();

        this.modulos =
          emptyModulos();

        this.datosGeneralesObra =
          emptyDatosGeneralesObra();

        this.variablesEntrada =
          emptyVariablesEntrada();

        this.estructuraEspacial =
          emptyEstructuraEspacial();

        this.colindanciasRecorrido =
          emptyColindanciasRecorrido();

        this.validacionEspacial =
          emptyValidacionEspacial();

        this.revisionInferencia =
          emptyRevisionInferencia();

        this.resumenConfirmado =
          false;

        this.resultado =
          emptyResultado();

        this.reglasSnapshot = {
          reglas: [],
          catalogos: [],
          errors: [],
          loaded: false,
        };
      },

      async loadReglasSnapshot() {
        const snapshot =
          await readReglasCatalogosV4();

        this.reglasSnapshot = {
          reglas:
            snapshot.reglas || [],

          catalogos:
            snapshot.catalogos || [],

          errors:
            snapshot.errors ||
            snapshot.pending ||
            [],

          loaded: true,
        };
      },

      sanitizeHydratedState() {
        // ------------------------------------------------------------
        // Registro / compatibilidad con estado persistido anterior
        // ------------------------------------------------------------

        const savedRegistro =
          this.registro || {};

        const savedPrestador =
          savedRegistro.prestador ||
          {};

        const savedCliente =
          savedRegistro.cliente ||
          {};

        const savedProyecto =
          savedRegistro.proyecto ||
          {};

        const savedUbicacion =
          savedRegistro.ubicacion ||
          {};

        this.registro = {
          ...emptyRegistro(),
          ...savedRegistro,

          prestador: {
            ...emptyRegistro()
              .prestador,
            ...savedPrestador,
          },

          cliente: {
            ...emptyRegistro()
              .cliente,
            ...savedCliente,
          },

          ubicacion: {
            ...emptyRegistro()
              .ubicacion,
            ...savedUbicacion,

            municipio:
              savedUbicacion
                .municipio ||
              savedCliente
                .ubicacion ||
              "",
          },

          proyecto: {
            ...emptyRegistro()
              .proyecto,
            ...savedProyecto,

            nombre:
              savedProyecto.nombre ||
              savedProyecto
                .nombreProyecto ||
              "",
          },

          terminosAceptados:
            Boolean(
              savedRegistro
                .terminosAceptados
            ),
        };

        // ------------------------------------------------------------
        // Clasificación y alcance
        // ------------------------------------------------------------

        this.clasificacion = {
          ...emptyClasificacion(),
          ...(this.clasificacion ||
            {}),
        };

        this.alcance = {
          ...emptyAlcance(),
          ...(this.alcance || {}),
        };

        const tipoIntervencion =
          String(
            this.clasificacion
              ?.tipoIntervencion ||
            ""
          ).trim();

        const alcanceKey =
          String(
            this.alcance
              ?.alcance ||
            ""
          ).trim();

        if (
          tipoIntervencion ===
          "obra_nueva"
        ) {
          const derived =
            ALCANCE_MODULES_OBRA_NUEVA[
              alcanceKey
            ] ||
            [...MODULE_ORDER];

          this.alcance
            .modulosActivos =
            normalizeModuleList(
              derived
            );
        } else {
          this.alcance
            .modulosActivos =
            normalizeModuleList(
              this.alcance
                ?.modulosActivos ||
              []
            );
        }

        this.alcance
          .partidasSeleccionadas =
          normalizeModuleList(
            this.alcance
              ?.partidasSeleccionadas ||
            []
          );

        this.alcance
          .subalcances =
          normalizeModuleList(
            this.alcance
              ?.subalcances ||
            []
          );

        // ------------------------------------------------------------
        // Módulos constructivos
        // ------------------------------------------------------------

        const savedModulos =
          this.modulos || {};

        this.modulos =
          emptyModulos();

        for (
          const key of MODULE_ORDER
        ) {
          const row =
            savedModulos[key] ||
            emptyModuleRow();

          const selected =
            Array.isArray(
              row.selectedConcepts
            )
              ? row.selectedConcepts
              : [];

          const summary =
            Array.isArray(
              row.summaryByPartida
            )
              ? row.summaryByPartida
              : [];

          const costo =
            toNumber(
              row.costoEstimado,
              0
            );

          const selectedConceptKeys = [
            ...new Set(
              [
                ...(Array.isArray(
                  row.selectedConceptKeys
                )
                  ? row
                      .selectedConceptKeys
                  : []),

                ...selected.map(
                  (item) =>
                    String(
                      item?.key || ""
                    )
                ),
              ].filter(Boolean)
            ),
          ];

          this.modulos[key] = {
            ...emptyModuleRow(),
            ...row,

            capturado:
              Boolean(
                row.capturado
              ),

            controles:
              row.controles &&
              typeof row.controles ===
                "object"
                ? {
                    ...row.controles,
                  }
                : {},

            selectedConcepts:
              selected.map(
                (item) => ({
                  ...item,
                })
              ),

            summaryByPartida:
              summary.map(
                (item) => ({
                  ...item,
                })
              ),

            selectedConceptKeys,

            costoEstimado:
              Number(
                Math.max(
                  costo,
                  0
                ).toFixed(2)
              ),
          };
        }

        // ------------------------------------------------------------
        // Preliminares
        // ------------------------------------------------------------

        const savedPreliminares =
          this.preliminares ||
          {};

        this.preliminares = {
          ...emptyPreliminares(),
          ...savedPreliminares,

          servicios: {
            ...emptyPreliminares()
              .servicios,

            ...(savedPreliminares
              .servicios || {}),
          },

          demolicion: {
            ...emptyPreliminares()
              .demolicion,

            ...(savedPreliminares
              .demolicion || {}),
          },

          engineInputs:
            savedPreliminares
              .engineInputs &&
            typeof savedPreliminares
              .engineInputs ===
              "object"
              ? {
                  ...savedPreliminares
                    .engineInputs,
                }
              : {},

          engineInputsByConcept:
            savedPreliminares
              .engineInputsByConcept &&
            typeof savedPreliminares
              .engineInputsByConcept ===
              "object"
              ? {
                  ...savedPreliminares
                    .engineInputsByConcept,
                }
              : {},

          conceptosActivos:
            Array.isArray(
              savedPreliminares
                .conceptosActivos
            )
              ? savedPreliminares
                  .conceptosActivos
              : [],

          technicalConcepts:
            Array.isArray(
              savedPreliminares
                .technicalConcepts
            )
              ? savedPreliminares
                  .technicalConcepts
              : [],

          officialSummary:
            Array.isArray(
              savedPreliminares
                .officialSummary
            )
              ? savedPreliminares
                  .officialSummary
              : [],

          pendingDefinitions:
            Array.isArray(
              savedPreliminares
                .pendingDefinitions
            )
              ? savedPreliminares
                  .pendingDefinitions
              : [],

          costoEstimado:
            Number(
              toNumber(
                savedPreliminares
                  .costoEstimado,
                0
              ).toFixed(2)
            ),
        };

        // ------------------------------------------------------------
        // Datos generales
        // ------------------------------------------------------------

        const savedGeneral =
          this.datosGeneralesObra ||
          {};

        this.datosGeneralesObra = {
          ...emptyDatosGeneralesObra(),
          ...savedGeneral,

          engineInputs:
            savedGeneral
              .engineInputs &&
            typeof savedGeneral
              .engineInputs ===
              "object"
              ? {
                  ...savedGeneral
                    .engineInputs,
                }
              : {},

          engineInputsByConcept:
            savedGeneral
              .engineInputsByConcept &&
            typeof savedGeneral
              .engineInputsByConcept ===
              "object"
              ? {
                  ...savedGeneral
                    .engineInputsByConcept,
                }
              : {},
        };

        // ------------------------------------------------------------
        // Estructura espacial
        // ------------------------------------------------------------

        const savedSpatial =
          this.estructuraEspacial ||
          {};

        this.estructuraEspacial =
          normalizeEstructuraEspacial(
            savedSpatial
          );

        // ------------------------------------------------------------
        // Estados posteriores
        // ------------------------------------------------------------

        this.variablesEntrada = {
          ...emptyVariablesEntrada(),
          ...(this
            .variablesEntrada ||
            {}),
        };

        this.colindanciasRecorrido = {
          ...emptyColindanciasRecorrido(),
          ...(this
            .colindanciasRecorrido ||
            {}),
        };

        this.validacionEspacial = {
          ...emptyValidacionEspacial(),
          ...(this
            .validacionEspacial ||
            {}),
        };

        this.revisionInferencia = {
          ...emptyRevisionInferencia(),
          ...(this
            .revisionInferencia ||
            {}),
        };

        this.resultado = {
          ...emptyResultado(),
          ...(this.resultado ||
            {}),
        };
      },
    },
  });
