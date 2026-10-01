/**
 * Quantia V2 — Editor 04
 * Defaults exclusivamente de interacción/UI.
 * No contiene dimensiones constructivas, alturas ni espesores técnicos.
 */

export const DEFAULT_EDITOR_SETTINGS = Object.freeze({
  showGrid: true,
  gridSizeM: 0.5,
  snapEnabled: true,
  showDimensions: true,
  showTerrain: true,
  showSpaces: true,
  showWalls: true,
  showDoors: true,
  showWindows: true,
  showAnnotations: true,
});

export const DEFAULT_VIEWPORT = Object.freeze({
  zoom: 1,
  offsetX: 0,
  offsetY: 0,
});

export const DEFAULT_HISTORY_OPTIONS = Object.freeze({
  maxEntries: 100,
  coalesceWindowMs: 800,
});

export const DEFAULT_LAYER_VISIBILITY = Object.freeze({
  terrain: true,
  grid: true,
  spaces: true,
  walls: true,
  doors: true,
  windows: true,
  dimensions: true,
  annotations: true,
});
