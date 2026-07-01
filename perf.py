"""
Diagnóstico de rendimiento por rerun.

Se activa cuando la URL contiene ?debug=1 (la misma URL que usa el resto de
diagnósticos de la app). Sin ?debug=1, todas las funciones son no-op y no
añaden overhead.

Uso mínimo en app.py:

    from perf import perf

    perf.start()                                   # arriba del script
    perf.render_panel()                            # arriba (muestra rerun anterior)

    with perf.phase("cargar()"):
        df = cargar(...)

    # Variante SIN 'with' — útil cuando envolver requeriría reindentar mucho:
    perf.start_phase("Popover + filtros")
    if controles:
        with st.popover(...):
            ...
    perf.end_phase("Popover + filtros")

    @st.fragment
    def _render_contenido():
        perf.fragment_start("_render_contenido")   # arriba del cuerpo
        # ... código existente sin re-indentar ...
        perf.fragment_end()                        # abajo

    perf.set_df_info(df_grid, label="AgGrid")      # antes de AgGrid(...)
    with perf.phase("AgGrid render"):
        AgGrid(...)

    perf.end()                                     # al final del script

    # OPCIONAL: panel de tiempos del NAVEGADOR (JS de AgGrid).
    # Se llama junto al render_panel() de arriba.
    perf.render_browser_panel()
"""

from __future__ import annotations

import time
from collections import OrderedDict
from contextlib import contextmanager

import pandas as pd
import streamlit as st


STATE_KEY = "_perf_state"
HISTORY_LIMIT = 10

IGNORE_KEY_PREFIXES = (
    "_perf_",
    "FormSubmitter:",
    "_reporte_anterior",
    "_nav_",
)

WIDGET_PREFIXES = (
    ("fch_",         "date_input"),
    ("cat_",         "multiselect"),
    ("busc_",        "multiselect"),
    ("grp_",         "multiselect"),
    ("btn_",         "button"),
    ("insp_",        "inspector"),
    ("req_",         "requerimientos"),
    ("grid_",        "AgGrid"),
    ("ajuste_",      "ajuste_inventario"),
    ("tabla_tam",    "select_slider"),
    ("forzar_movil", "toggle"),
    ("vista_seg_",   "segmented_control"),
    ("colsel_",      "multiselect"),
    ("zoom_",        "select_slider"),
    ("export_",      "download_button"),
    ("ejex_",        "selectbox"),
    ("ejey_",        "selectbox"),
    ("data_editor_", "data_editor"),
)


class PerfTracker:
    """Rastreador de rendimiento por rerun.

    El estado real vive en st.session_state[STATE_KEY]. La instancia no guarda
    nada, así que el singleton `perf` funciona bien aunque Python cachee la
    importación del módulo.
    """

    @property
    def enabled(self) -> bool:
        """Se re-evalúa en cada llamada (por si el usuario quita/pone ?debug=1)."""
        try:
            return bool(st.query_params.get("debug"))
        except Exception:
            return False

    def _ensure_state(self):
        if STATE_KEY not in st.session_state:
            st.session_state[STATE_KEY] = {
                "rerun_count": 0,
                "history": [],
                "last_snapshot": {},
                "current": None,
            }

    # ---------- Ciclo de rerun completo -----------------------------------

    def start(self):
        if not self.enabled:
            return
        self._ensure_state()
        state = st.session_state[STATE_KEY]

        # Cerrar rerun zombie (>30 s sin end()) si lo hay
        cur = state.get("current")
        if cur is not None and time.perf_counter() - cur["start_time"] > 30:
            self._flush_current(zombie=True)

        trigger = self._detect_trigger(state.get("last_snapshot", {}))
        state["rerun_count"] += 1
        state["current"] = {
            "rerun_id": state["rerun_count"],
            "start_time": time.perf_counter(),
            "phases": OrderedDict(),
            "open_phases": {},
            "trigger": trigger,
            "started_at": time.time(),
            "df_info": None,
            "is_fragment": False,
            "fragment_owned": False,
        }

    def end(self):
        if not self.enabled:
            return
        self._flush_current(zombie=False)

    def _flush_current(self, zombie: bool = False):
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            return
        cur = state["current"]
        cur["total_ms"] = (time.perf_counter() - cur["start_time"]) * 1000
        state["last_snapshot"] = self._snapshot()
        history = state.get("history", [])
        history.insert(0, {
            "rerun_id": cur["rerun_id"],
            "trigger": cur["trigger"],
            "total_ms": cur["total_ms"],
            "phases": dict(cur["phases"]),
            "df_info": cur.get("df_info"),
            "started_at": cur["started_at"],
            "is_fragment": cur.get("is_fragment", False),
            "zombie": zombie,
        })
        state["history"] = history[:HISTORY_LIMIT]
        state["current"] = None

    # ---------- Fases -----------------------------------------------------

    @contextmanager
    def phase(self, name: str):
        if not self.enabled:
            yield
            return
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            yield
            return
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dur_ms = (time.perf_counter() - t0) * 1000
            phases = state["current"]["phases"]
            phases[name] = phases.get(name, 0.0) + dur_ms

    def start_phase(self, name: str):
        """Alternativa sin 'with' — evita reindentar bloques grandes."""
        if not self.enabled:
            return
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            return
        state["current"]["open_phases"][name] = time.perf_counter()

    def end_phase(self, name: str):
        if not self.enabled:
            return
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            return
        open_phases = state["current"]["open_phases"]
        if name not in open_phases:
            return
        t0 = open_phases.pop(name)
        dur_ms = (time.perf_counter() - t0) * 1000
        phases = state["current"]["phases"]
        phases[name] = phases.get(name, 0.0) + dur_ms

    # ---------- @st.fragment ---------------------------------------------

    def fragment_start(self, name: str = "fragment"):
        """Arriba del cuerpo de una función @st.fragment.

        - Rerun completo en curso → solo agrega una fase 'fragment[name]'.
        - Rerun aislado del fragment → arranca un rerun tracked propio.
        """
        if not self.enabled:
            return
        self._ensure_state()
        state = st.session_state[STATE_KEY]
        if state.get("current") is None:
            trigger = self._detect_trigger(state.get("last_snapshot", {}))
            state["rerun_count"] += 1
            state["current"] = {
                "rerun_id": state["rerun_count"],
                "start_time": time.perf_counter(),
                "phases": OrderedDict(),
                "open_phases": {},
                "trigger": trigger,
                "started_at": time.time(),
                "df_info": None,
                "is_fragment": True,
                "fragment_owned": True,
                "fragment_name": name,
            }
        self.start_phase(f"fragment[{name}]")

    def fragment_end(self, name: str = "fragment"):
        if not self.enabled:
            return
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            return
        self.end_phase(f"fragment[{name}]")
        if state["current"].get("fragment_owned"):
            self._flush_current(zombie=False)

    # ---------- Tamaño del DataFrame que va a AgGrid ---------------------

    def set_df_info(self, df: pd.DataFrame, label: str = "AgGrid"):
        if not self.enabled:
            return
        state = st.session_state.get(STATE_KEY)
        if not state or not state.get("current"):
            return
        try:
            n = len(df)
            mem_bytes = int(df.memory_usage(deep=True).sum())
            json_bytes = 0
            if n > 0:
                sample_n = min(200, n)
                try:
                    sample = df.head(sample_n).to_json(
                        orient="records", date_format="iso"
                    )
                    json_bytes = int(len(sample.encode("utf-8")) * n / sample_n)
                except Exception:
                    json_bytes = mem_bytes
            state["current"]["df_info"] = {
                "label": label,
                "rows": n,
                "cols": df.shape[1],
                "mem_mb": mem_bytes / 1_048_576,
                "json_mb": json_bytes / 1_048_576,
            }
        except Exception as e:
            state["current"]["df_info"] = {"label": label, "error": str(e)}

    # ---------- Panel ----------------------------------------------------

    def render_panel(self, expanded: bool = True):
        if not self.enabled:
            return
        self._ensure_state()
        state = st.session_state[STATE_KEY]
        history = state.get("history", [])

        with st.expander("⚡ Diagnóstico de rendimiento (?debug=1)", expanded=expanded):
            if not history:
                st.caption(
                    "Esperando al primer rerun completo. Haz cualquier "
                    "interacción y vuelve a mirar este panel."
                )
                st.caption(f"Reruns contados: **{state['rerun_count']}**")
                return

            last = history[0]
            avg_ms = sum(h["total_ms"] for h in history) / len(history)

            c1, c2, c3 = st.columns(3)
            c1.metric("🔁 Reruns totales", f"{state['rerun_count']}")
            c2.metric(
                "⏱️ Último rerun",
                f"{last['total_ms']:.0f} ms",
                delta=f"promedio {avg_ms:.0f} ms",
                delta_color="off",
            )
            df_info = last.get("df_info") or {}
            if "rows" in df_info:
                c3.metric(
                    f"📦 → {df_info.get('label', 'AgGrid')}",
                    f"{df_info['json_mb']:.1f} MB",
                    delta=f"{df_info['rows']:,} × {df_info['cols']} cols",
                    delta_color="off",
                )
            elif "error" in df_info:
                c3.metric("📦 DataFrame", "error",
                          delta=df_info["error"][:30], delta_color="off")
            else:
                c3.metric("📦 DataFrame", "—")

            trigger = last.get("trigger", {})
            frag_note = " · fragment rerun" if last.get("is_fragment") else ""
            zombie_note = " · ⚠️ abandonado" if last.get("zombie") else ""
            st.info(
                f"🎯 **Último rerun disparado por:** "
                f"`{trigger.get('key', '?')}` ({trigger.get('type', '?')})"
                f"{frag_note}{zombie_note} · hace {_ago(last['started_at'])}"
                + (f"\n\n{trigger.get('extra', '')}"
                   if trigger.get("extra") else "")
            )

            st.markdown("**Desglose del último rerun**")
            phases = last.get("phases", {})
            total = last["total_ms"]
            if phases and total > 0:
                fases_ord = sorted(phases.items(), key=lambda kv: kv[1], reverse=True)
                medido = sum(phases.values())
                overhead = max(0, total - medido)
                for name, ms in fases_ord:
                    pct = ms / total * 100
                    st.progress(min(pct / 100, 1.0),
                                text=f"{name} — {ms:.0f} ms ({pct:.0f}%)")
                if overhead > 5:
                    pct_ov = overhead / total * 100
                    st.progress(min(pct_ov / 100, 1.0),
                                text=f"(otros / no medido) — {overhead:.0f} ms ({pct_ov:.0f}%)")
            else:
                st.caption("Sin fases medidas en el último rerun.")

            if len(history) > 1:
                st.markdown("**Últimos reruns**")
                rows = []
                for h in history[:5]:
                    tr = h.get("trigger", {})
                    dfi = h.get("df_info") or {}
                    rows.append({
                        "#": h["rerun_id"],
                        "Tipo": "fragment" if h.get("is_fragment") else "full",
                        "Widget": tr.get("key", "?"),
                        "Duración (ms)": f"{h['total_ms']:.0f}",
                        "Filas": (f"{dfi.get('rows', 0):,}"
                                  if isinstance(dfi.get("rows"), int) else "—"),
                        "Hace": _ago(h["started_at"]),
                    })
                st.dataframe(pd.DataFrame(rows),
                             use_container_width=True, hide_index=True)

    # ---------- Panel de tiempos del NAVEGADOR (JS de AgGrid) ------------

    def render_browser_panel(self):
        """Panel que muestra los tiempos medidos DENTRO del navegador.

        Depende de que en tablas.py, en las `opciones_grid` del AgGrid,
        se emitan mensajes de BroadcastChannel('_perf_aggrid') desde los
        callbacks `onGridReady` y `onFirstDataRendered`.

        Los tiempos se actualizan en tiempo real via JavaScript, no depende
        de reruns de Streamlit.
        """
        if not self.enabled:
            return

        html_code = """
<div id="_perf_browser_wrap" style="border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin:8px 0 4px 0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:10px;">
        Tiempos del navegador (JavaScript de AgGrid)
    </div>
    <div style="font-size:13px;color:#475569;display:grid;grid-template-columns:1fr auto;gap:6px 12px;align-items:center;">
        <div>AgGrid instalado <code style="font-size:11px;color:#64748b;">(onGridReady)</code>:</div>
        <div id="_perf_ready" style="font-family:monospace;color:#1e3a5f;font-weight:600;text-align:right;">esperando...</div>
        <div>Filas dibujadas <code style="font-size:11px;color:#64748b;">(onFirstDataRendered)</code>:</div>
        <div id="_perf_render" style="font-family:monospace;color:#1e3a5f;font-weight:600;text-align:right;">esperando...</div>
        <div style="border-top:1px solid #e2e8f0;padding-top:8px;font-weight:600;color:#0f172a;">
            Tiempo dibujando la tabla (diferencia):
        </div>
        <div id="_perf_diff" style="font-family:monospace;font-weight:700;text-align:right;border-top:1px solid #e2e8f0;padding-top:8px;font-size:15px;color:#1e293b;">-</div>
        <div style="font-size:11px;color:#64748b;">Filas renderizadas:</div>
        <div id="_perf_rows" style="font-family:monospace;font-size:11px;color:#64748b;text-align:right;">-</div>
    </div>
    <div id="_perf_hint" style="font-size:11px;color:#64748b;margin-top:8px;font-style:italic;">
        Se actualiza cada vez que AgGrid termina de dibujar. Interactua con un widget para ver los tiempos.
    </div>
    <div id="_perf_err" style="font-size:11px;color:#dc2626;margin-top:6px;"></div>
</div>
<script>
(function() {
    var setErr = function(msg) {
        var el = document.getElementById('_perf_err');
        if (el) el.textContent = 'Error: ' + msg;
    };
    try {
        if (typeof BroadcastChannel === 'undefined') {
            setErr('BroadcastChannel no soportado en este navegador');
            return;
        }
        if (window._perfBcInit) return;
        window._perfBcInit = true;

        var bc = new BroadcastChannel('_perf_aggrid');
        var readyTime = null;

        bc.onmessage = function(event) {
            var d = event.data;
            if (!d || !d.event) return;

            if (d.event === 'gridReady') {
                readyTime = d.time;
                var el = document.getElementById('_perf_ready');
                if (el) el.textContent = readyTime.toFixed(0) + ' ms';
            }

            if (d.event === 'firstDataRendered') {
                var renderTime = d.time;
                var elR = document.getElementById('_perf_render');
                if (elR) elR.textContent = renderTime.toFixed(0) + ' ms';

                if (readyTime !== null) {
                    var diff = renderTime - readyTime;
                    var elD = document.getElementById('_perf_diff');
                    if (elD) {
                        var label = diff.toFixed(0) + ' ms';
                        if (diff >= 1000) {
                            label = (diff / 1000).toFixed(1) + ' s (' + diff.toFixed(0) + ' ms)';
                        }
                        elD.textContent = label;
                        if (diff > 10000) elD.style.color = '#dc2626';
                        else if (diff > 3000) elD.style.color = '#ea580c';
                        else if (diff > 1000) elD.style.color = '#ca8a04';
                        else elD.style.color = '#16a34a';
                    }
                }

                if (d.rowCount != null) {
                    var elRC = document.getElementById('_perf_rows');
                    if (elRC) elRC.textContent = Number(d.rowCount).toLocaleString();
                }

                var hint = document.getElementById('_perf_hint');
                if (hint) hint.textContent = 'Ultima medida OK. Toca otro widget para volver a medir.';
            }
        };
    } catch(e) {
        setErr(e.message || String(e));
    }
})();
</script>
        """
        st.components.v1.html(html_code, height=260)



    def _snapshot(self) -> dict:
        snap = {}
        try:
            for k, v in st.session_state.items():
                if k == STATE_KEY:
                    continue
                if any(k.startswith(p) for p in IGNORE_KEY_PREFIXES):
                    continue
                try:
                    r = repr(v)
                    snap[k] = r if len(r) <= 300 else r[:300] + "…"
                except Exception:
                    snap[k] = f"<{type(v).__name__}>"
        except Exception:
            pass
        return snap

    def _detect_trigger(self, prev_snapshot: dict) -> dict:
        if not prev_snapshot:
            return {"key": "(carga inicial)", "type": "initial", "extra": ""}
        current = self._snapshot()
        changed = [k for k, v in current.items() if prev_snapshot.get(k) != v]
        changed += [k for k in prev_snapshot if k not in current]
        if not changed:
            return {"key": "(sin cambios detectables)", "type": "unknown", "extra": ""}
        prio = [k for k in changed if _widget_type(k) != "unknown"]
        principal = prio[0] if prio else changed[0]
        extra = ""
        if len(changed) > 1:
            extra = f"Otras claves cambiadas: `{'`, `'.join(changed[1:6])}`"
            if len(changed) > 6:
                extra += f" y {len(changed) - 6} más"
        return {
            "key": principal,
            "type": _widget_type(principal),
            "extra": extra,
            "all_changed": changed,
        }


def _widget_type(key: str) -> str:
    for prefix, tipo in WIDGET_PREFIXES:
        if key == prefix or key.startswith(prefix):
            return tipo
    return "unknown"


def _ago(ts: float) -> str:
    secs = int(time.time() - ts)
    if secs < 60:
        return f"{secs} s"
    if secs < 3600:
        return f"{secs // 60} min"
    return f"{secs // 3600} h"


# Singleton (todo el estado real vive en session_state)
perf = PerfTracker()
