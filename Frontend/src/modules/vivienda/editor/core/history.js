import {
  DEFAULT_HISTORY_OPTIONS,
} from "./editorDefaults";

import {
  cloneEditorState,
} from "./editorSchema";

function clone(value) {
  return cloneEditorState(value);
}

export class EditorHistory {
  constructor(options = {}) {
    this.maxEntries = Number.isInteger(options.maxEntries)
      ? Math.max(2, options.maxEntries)
      : DEFAULT_HISTORY_OPTIONS.maxEntries;

    this.coalesceWindowMs = Number.isFinite(Number(options.coalesceWindowMs))
      ? Math.max(0, Number(options.coalesceWindowMs))
      : DEFAULT_HISTORY_OPTIONS.coalesceWindowMs;

    this.entries = [];
    this.index = -1;
    this.group = null;
  }

  reset(initialState, label = "Estado inicial") {
    this.entries = [{
      id: makeHistoryId(),
      label,
      timestamp: new Date().toISOString(),
      coalesceKey: null,
      state: clone(initialState),
    }];
    this.index = 0;
    this.group = null;
  }

  push(state, options = {}) {
    const label = options.label || "Cambio";
    const coalesceKey = options.coalesceKey || null;
    const force = Boolean(options.force);
    const now = Date.now();

    if (this.index < this.entries.length - 1) {
      this.entries = this.entries.slice(0, this.index + 1);
    }

    if (this.group) {
      this.group.latestState = clone(state);
      this.group.latestLabel = label;
      return;
    }

    const current = this.entries[this.index];
    const currentTime = current
      ? new Date(current.timestamp).getTime()
      : 0;

    const canCoalesce =
      !force &&
      coalesceKey &&
      current?.coalesceKey === coalesceKey &&
      now - currentTime <= this.coalesceWindowMs;

    const entry = {
      id: makeHistoryId(),
      label,
      timestamp: new Date(now).toISOString(),
      coalesceKey,
      state: clone(state),
    };

    if (canCoalesce) {
      this.entries[this.index] = entry;
    } else {
      this.entries.push(entry);
      this.index = this.entries.length - 1;
    }

    this.trim();
  }

  beginGroup(label = "Operación") {
    if (this.group) return;

    this.group = {
      label,
      latestLabel: label,
      latestState: null,
    };
  }

  endGroup(options = {}) {
    if (!this.group) return;

    const group = this.group;
    this.group = null;

    if (group.latestState) {
      this.push(group.latestState, {
        label: options.label || group.latestLabel || group.label,
        force: true,
      });
    }
  }

  cancelGroup() {
    this.group = null;
  }

  undo() {
    if (!this.canUndo()) return null;
    this.index -= 1;
    return clone(this.entries[this.index].state);
  }

  redo() {
    if (!this.canRedo()) return null;
    this.index += 1;
    return clone(this.entries[this.index].state);
  }

  current() {
    if (this.index < 0) return null;
    return clone(this.entries[this.index].state);
  }

  canUndo() {
    return this.index > 0;
  }

  canRedo() {
    return this.index >= 0 && this.index < this.entries.length - 1;
  }

  clear() {
    this.entries = [];
    this.index = -1;
    this.group = null;
  }

  getSummary() {
    return {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      size: this.entries.length,
      index: this.index,
      currentLabel: this.entries[this.index]?.label || null,
    };
  }

  trim() {
    if (this.entries.length <= this.maxEntries) return;

    const excess = this.entries.length - this.maxEntries;
    this.entries.splice(0, excess);
    this.index = Math.max(0, this.index - excess);
  }
}

export function createEditorHistory(options = {}) {
  return new EditorHistory(options);
}

function makeHistoryId() {
  return `history_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}
