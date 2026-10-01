# Recepción 03 → 04 y plantilla 04 → 05

`viviendaStore.setEstructuraEspacial()` normaliza el contrato legacy y acepta
`SPATIAL_INTERFACE04_REVIEW_V1`. Conserva campos originales, evidencia, revisión,
segmentos raster, coordenadas métricas y candidatos. Los IDs de nivel se resuelven
contra `niveles`; no se interpretan nombres de proyectos.

Para el paquete de revisión, 03 debe entregar `planoBase.referencia` como URL
utilizable del recorte local exacto. Una referencia de archivo como `original.png`
se conserva en metadata pero no se solicita como ruta web ni se sustituye por una
página completa. Sin URL se pueden visualizar los segmentos sobre el lienzo raster.

04 muestra conteos y evidencia y permite guardar en el store de la sesión o
descargar `QUANTIA_04_TO_05_DRAFT_V1`. La descarga incorpora los espacios editados,
datos generales, revisión de origen, información fuente y entradas por concepto.
No añade inferencias de cantidades ni consume automáticamente el motor de 05.

El contrato tiene `status=DRAFT` y `readyForCalculation=false`. `data.puertas` y
`data.ventanas` son null mientras `completeness.openings` no sea `CONFIRMED`.
Una lista vacía únicamente representa ausencia confirmada con ese estado.
Los candidatos permanecen en `reviewSource`; no se promueven a aberturas.

El receptor futuro de 05 deberá validar versión, revisión, geometría, completitud
y requisitos por concepto antes de construir la petición real del motor. El flujo
legacy de 05 se conserva; un paquete que declare `readiness.workflowContinuation`
false no puede avanzar desde 04. Guardar un borrador no cambia ese estado.

Pruebas: `node --test tests/spatialWorkflowContract.test.mjs tests/planEditorView.test.mjs`.
