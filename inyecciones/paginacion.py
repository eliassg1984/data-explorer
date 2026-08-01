"""inyecciones.paginacion - barra de paginacion v2 del AgGrid.

Reemplaza la paginacion nativa por una con numeros de pagina y salto directo.
"""

import json
import streamlit.components.v1 as components
from inyecciones._fragmentos import _PGV2_CSS_IFRAME


def inject_pagination_v2():
    """Barra de paginación personalizada con números y salto de página.

    NOTA — colores del bloque #pgv2:
        Se inyecta con agDoc.head.appendChild dentro del iframe de AgGrid.
        Antes usaba var(--x) del padre y no resolvía (botones sin fondo,
        número activo sin destacar, etc). Ahora usa el bloque pre-computado
        _PGV2_CSS_IFRAME con constantes de tema.py. Ver arquitectura.md §Fase 2.
    """
    pgv2_css_js = json.dumps(_PGV2_CSS_IFRAME)
    components.html("""
    <script>
    (function(){
      var win = window.parent, doc = win.document;
      var tries = 0, MAX = 60;

      var PGV2_CSS = """ + pgv2_css_js + """;

      function intDe(txt){
        var m = (txt||'').match(/\\d[\\d.,]*/g);
        if (!m) return [];
        return m.map(function(s){ return parseInt(s.replace(/[^0-9]/g,''),10); })
                .filter(function(n){ return !isNaN(n); });
      }

      function leerEstado(panel){
        var desc = panel.querySelector('.ag-paging-description');
        var nums = desc ? intDe(desc.textContent) : [];
        if (nums.length >= 2) return { cur: nums[0], tot: nums[nums.length-1] };
        var c = panel.querySelector('[ref=lbCurrent]');
        var t = panel.querySelector('[ref=lbTotal]');
        if (c && t){
          var cc = intDe(c.textContent)[0], tt = intDe(t.textContent)[0];
          if (!isNaN(cc) && !isNaN(tt)) return { cur: cc, tot: tt };
        }
        return null;
      }

      function montar(agDoc){
        var panel = agDoc.querySelector('.ag-paging-panel');
        if (!panel) return 'sin-panel';
        var est = leerEstado(panel);
        if (!est) return 'sin-estado';

        if (!agDoc.getElementById('pgv2-css')){
          var stl = agDoc.createElement('style');
          stl.id = 'pgv2-css';
          stl.textContent = PGV2_CSS;
          agDoc.head.appendChild(stl);
        }

        function go(p){
          var e = leerEstado(panel); if (!e) return;
          p = Math.max(1, Math.min(e.tot, p));
          if (p === e.cur) return;
          win.__pgv2busy = true;
          /* AgGrid moderno usa data-ref; ref queda por compatibilidad. */
          var btn = (p > e.cur)
              ? panel.querySelector('[ref=btNext], [data-ref=btNext]')
              : panel.querySelector('[ref=btPrevious], [data-ref=btPrevious]');
          var n = Math.abs(p - e.cur);
          for (var k=0; k<n && btn; k++){ btn.click(); }
          win.__pgv2busy = false;
          render();
        }

        function paginas(c, t){
          var want = [1, t, c, c-1, c+1, c-2, c+2], seen = {}, arr = [];
          for (var i=0;i<want.length;i++){
            var v = want[i];
            if (v>=1 && v<=t && !seen[v]){ seen[v]=1; arr.push(v); }
          }
          arr.sort(function(a,b){ return a-b; });
          var out = [];
          for (var j=0;j<arr.length;j++){
            if (j>0 && arr[j]-arr[j-1] > 1) out.push('...');
            out.push(arr[j]);
          }
          return out;
        }

        function render(){
          var e = leerEstado(panel); if (!e) return;
          var c = e.cur, t = e.tot;
          /* Una sola página: nada que paginar; la barra completa se oculta
             y reaparece sola cuando el total de páginas vuelve a crecer
             (el MutationObserver re-invoca render en cada cambio). */
          panel.style.display = (t <= 1) ? 'none' : '';
          if (t <= 1) return;
          var bar = agDoc.getElementById('pgv2');
          if (!bar){ bar = agDoc.createElement('div'); bar.id = 'pgv2'; panel.appendChild(bar); }
          var html = '<span class="pgv2-pages">';
          html += '<button data-go="'+(c-1)+'" '+(c<=1?'disabled':'')+' aria-label="Anterior">\\u2039</button>';
          var ps = paginas(c, t);
          for (var i=0;i<ps.length;i++){
            if (ps[i]==='...') html += '<span class="pgv2-dots">\\u2026</span>';
            else html += '<button data-go="'+ps[i]+'" class="'+(ps[i]===c?'pgv2-on':'')+'">'+ps[i]+'</button>';
          }
          html += '<button data-go="'+(c+1)+'" '+(c>=t?'disabled':'')+' aria-label="Siguiente">\\u203a</button>';
          html += '</span>';
          html += '<span class="pgv2-jump">Ir a '+
                  '<input type="number" min="1" max="'+t+'" value="'+c+'" id="pgv2-in" aria-label="Ir a pagina">'+
                  '<button id="pgv2-goin" aria-label="Ir">\\u2192</button></span>';
          bar.innerHTML = html;

          var btns = bar.querySelectorAll('button[data-go]');
          for (var b=0;b<btns.length;b++){
            btns[b].addEventListener('click', function(){
              var v = parseInt(this.getAttribute('data-go'),10);
              if (!isNaN(v)) go(v);
            });
          }
          var inp = bar.querySelector('#pgv2-in');
          var goin = bar.querySelector('#pgv2-goin');
          function jump(){ var v = parseInt(inp.value,10); if (!isNaN(v)) go(v); }
          goin.addEventListener('click', jump);
          inp.addEventListener('keydown', function(ev){
            if (ev.key === 'Enter'){ ev.preventDefault(); jump(); }
          });
        }

        win.__pgv2render = render;
        if (!panel.__pgv2obs){
          var diana = panel.querySelector('.ag-paging-description') || panel;
          var obs = new win.MutationObserver(function(){
            if (!win.__pgv2busy && win.__pgv2render) win.__pgv2render();
          });
          obs.observe(diana, {childList:true, characterData:true, subtree:true});
          panel.__pgv2obs = obs;
        }

        render();
        return 'ok';
      }

      function buscarFrames(){
        var f = doc.querySelectorAll('iframe[src*="st_aggrid"]');
        if (f.length) return f;
        return doc.querySelectorAll('iframe');
      }

      function check(){
        tries++;
        var frames = buscarFrames();
        var ultimo = 'sin-iframe';
        for (var i=0;i<frames.length;i++){
          var d = null;
          try { d = frames[i].contentDocument; } catch(e){}
          if (!d || !d.querySelector('.ag-paging-panel')) continue;
          var r = montar(d);
          if (r === 'ok') return;
          ultimo = r;
        }
        if (tries < MAX){ win.setTimeout(check, 500); return; }
        /* Aviso solo en modo debug: con la barra auto-oculta (1 pagina),
           un grid vacio o la vista de graficos, no montar es esperable. */
        var esDebug = (win.location.search || '').indexOf('debug') !== -1;
        if (esDebug && win.__logErr) win.__logErr('Paginacion v2 no se pudo montar (' + ultimo + ').');
      }
      win.setTimeout(check, 800);
    })();
    </script>
    """, height=0)
