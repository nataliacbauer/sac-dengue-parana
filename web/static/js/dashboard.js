/* =====================================================================
 * SAC Dengue Paraná - Dashboard Interativo (Fase 4 - Frontend)
 * Mapa Leaflet de buffers, KPIs, gráficos Chart.js, tabela,
 * modal horário por estação e exportação do mapa oficial QGIS.
 * ===================================================================== */

// ---------------------------------------------------------------------
// Bloco 1 - Estado global e utilitários
// ---------------------------------------------------------------------
const STATE = {
  modo: "7dias",          // "7dias" | "se"
  ano: null,
  semana: null,
  config: null,
  dados: null,            // resposta de /api/dados
  resultadosPorIbge: {},
  resultadosPorNome: {},
  map: null,
  layerBuffers: null,
  layerAbrangencia: null,
  layerMunicipios: null,
  geoBuffers: null,
  charts: { ranking: null, balanco: null, horario: null, expandido: null },
  sortCol: "k177",
  sortAsc: false,
  carregando: false
};

const ORDEM_RISCO = {
  "Risco Muito Alto": 4,
  "Risco Alto": 3,
  "Risco Medio": 2,
  "Risco Baixo": 1,
  "Dados Insuficientes": 0
};

const CORES_RISCO = {
  "Risco Baixo": "#fff8bd",
  "Risco Medio": "#ffd95b",
  "Risco Alto": "#f15b1b",
  "Risco Muito Alto": "#b50000",
  "Dados Insuficientes": "#cbd5e0"
};

const PR_BOUNDS = [[-26.75, -54.65], [-22.50, -48.00]];

function normalizarTexto(s) {
  return String(s || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim();
}

function normalizarRisco(risco) {
  if (!risco) return "Dados Insuficientes";
  const r = normalizarTexto(risco);
  if (r.includes("muito alto")) return "Risco Muito Alto";
  if (r.includes("alto")) return "Risco Alto";
  if (r.includes("medio")) return "Risco Medio";
  if (r.includes("baixo")) return "Risco Baixo";
  return "Dados Insuficientes";
}

function rotuloRisco(riscoNorm) {
  return riscoNorm === "Risco Medio" ? "Risco Médio" : riscoNorm;
}

function badgeClasseRisco(riscoNorm) {
  switch (riscoNorm) {
    case "Risco Muito Alto": return "badge-risco-muito-alto";
    case "Risco Alto": return "badge-risco-alto";
    case "Risco Medio": return "badge-risco-medio";
    case "Risco Baixo": return "badge-risco-baixo";
    default: return "badge-insuficiente";
  }
}

function fmt(v, casas = 1, sufixo = "") {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "--";
  return Number(v).toLocaleString("pt-BR", {
    minimumFractionDigits: casas, maximumFractionDigits: casas
  }) + sufixo;
}

function queryPeriodo() {
  const p = new URLSearchParams({ tipo: STATE.modo });
  if (STATE.modo === "se" && STATE.ano && STATE.semana) {
    p.set("ano", STATE.ano);
    p.set("semana", STATE.semana);
  }
  return p;
}

async function fetchJSON(url, opts) {
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try { const j = await resp.json(); if (j.erro) msg = j.erro; } catch (_) {}
    throw new Error(msg);
  }
  return resp.json();
}

function mostrarToast(mensagem, tipo = "info") {
  let cont = document.getElementById("toastContainer");
  if (!cont) {
    cont = document.createElement("div");
    cont.id = "toastContainer";
    cont.className = "toast-container position-fixed bottom-0 end-0 p-3";
    cont.style.zIndex = 2000;
    document.body.appendChild(cont);
  }
  const cores = { info: "text-bg-primary", sucesso: "text-bg-success", erro: "text-bg-danger", aviso: "text-bg-warning" };
  const el = document.createElement("div");
  el.className = `toast align-items-center border-0 ${cores[tipo] || cores.info}`;
  el.setAttribute("role", "status");
  el.innerHTML = `<div class="d-flex"><div class="toast-body">${mensagem}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button></div>`;
  cont.appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 5000 });
  t.show();
  el.addEventListener("hidden.bs.toast", () => el.remove());
}

function setBotaoCarregando(btn, carregando, textoCarregando) {
  if (!btn) return;
  if (carregando) {
    btn.dataset.htmlOriginal = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>${textoCarregando || "Processando..."}`;
  } else {
    btn.disabled = false;
    if (btn.dataset.htmlOriginal) btn.innerHTML = btn.dataset.htmlOriginal;
  }
}

// ---------------------------------------------------------------------
// Bloco 2 - Mapa Leaflet (buffers, abrangência, municípios, legenda)
// ---------------------------------------------------------------------
function initMapa() {
  STATE.map = L.map("map", { zoomControl: true, minZoom: 5, maxZoom: 14 });

  const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19
  });

  const esriClaro = L.layerGroup([
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles &copy; Esri", maxZoom: 16
    }),
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 16
    })
  ]);

  const esriTopo = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
    attribution: "Tiles &copy; Esri", maxZoom: 18
  });

  osm.addTo(STATE.map);
  L.control.layers(
    {
      "OpenStreetMap": osm,
      "Mapa Claro (Esri)": esriClaro,
      "Topográfico (Esri)": esriTopo
    },
    null,
    { position: "topright", collapsed: true }
  ).addTo(STATE.map);

  STATE.map.fitBounds(PR_BOUNDS);

  // Panes na ordem exata do projeto QGIS: estados < municípios < abrangência < buffers < rótulos
  STATE.map.createPane("paneEstados").style.zIndex = 380;
  STATE.map.createPane("paneMunicipios").style.zIndex = 390;
  STATE.map.createPane("paneAbrangencia").style.zIndex = 400;
  STATE.map.createPane("paneBuffers").style.zIndex = 410;
  STATE.map.createPane("paneRotulos").style.zIndex = 420;
  STATE.map.getPane("paneRotulos").style.pointerEvents = "none";

  adicionarLegenda();
}

async function carregarCamadasBase() {
  const [uf, mun, abr, buf] = await Promise.all([
    fetchJSON("/static/estados_br.geojson?v=3").catch(() => null),
    fetchJSON("/static/municipios_pr.geojson?v=3").catch(() => null),
    fetchJSON("/static/abrangencia.geojson?v=3").catch(() => null),
    fetchJSON("/static/risco_buffer.geojson?v=3")
  ]);

  if (uf) {
    L.geoJSON(uf, {
      pane: "paneEstados",
      interactive: false,
      smoothFactor: 0.3,
      style: { color: "#232323", weight: 1.0, fillColor: "#ffffff", fillOpacity: 0.45 }
    }).addTo(STATE.map);
  }
  if (mun) {
    STATE.layerMunicipios = L.geoJSON(mun, {
      pane: "paneMunicipios",
      interactive: false,
      smoothFactor: 0.2,
      style: { color: "#4a4a4a", weight: 0.55, fillColor: "#ffffff", fillOpacity: 0.78 }
    }).addTo(STATE.map);
  }
  if (abr) {
    STATE.layerAbrangencia = L.geoJSON(abr, {
      pane: "paneAbrangencia",
      interactive: false,
      smoothFactor: 0,
      style: { stroke: false, fillColor: "#b6b6b6", fillOpacity: 0.35 }
    }).addTo(STATE.map);
  }
  STATE.geoBuffers = buf;
}

function resultadoDoBuffer(props) {
  const ibge = String(props.cod_IBGE || "");
  if (STATE.resultadosPorIbge[ibge]) return STATE.resultadosPorIbge[ibge];
  const nome = normalizarTexto(props.Name);
  if (STATE.resultadosPorNome[nome]) return STATE.resultadosPorNome[nome];
  for (const [n, r] of Object.entries(STATE.resultadosPorNome)) {
    if (n.includes(nome) || nome.includes(n)) return r;
  }
  return null;
}

function estiloBuffer(feature) {
  const r = resultadoDoBuffer(feature.properties);
  const risco = r && r.status === "OK" ? normalizarRisco(r.risco) : "Dados Insuficientes";
  return {
    pane: "paneBuffers",
    color: "#505050",
    weight: 0.75,
    fillColor: CORES_RISCO[risco],
    fillOpacity: 0.62
  };
}

function htmlPopupEstacao(r, nomeBuffer) {
  if (!r) {
    return `<div class="fw-bold">${nomeBuffer}</div><div class="text-muted small">Sem dados vinculados.</div>`;
  }
  const risco = r.status === "OK" ? normalizarRisco(r.risco) : "Dados Insuficientes";
  const corpo = r.status === "OK" ? `
      <table class="table table-sm mb-2 small">
        <tr><td>Temp. média</td><td class="text-end">${fmt(r.temp_media, 1, " °C")}</td></tr>
        <tr><td>Chuva acumulada</td><td class="text-end">${fmt(r.chuva_total, 1, " mm")}</td></tr>
        <tr><td>Evapotranspiração</td><td class="text-end">${fmt(r.evapotranspiracao, 1, " mm")}</td></tr>
        <tr><td>Índice térmico</td><td class="text-end">${fmt(r.k176, 2)}</td></tr>
        <tr><td>Balanço hídrico</td><td class="text-end">${fmt(r.h180, 2)}</td></tr>
        <tr class="fw-bold"><td>Índice de risco</td><td class="text-end">${fmt(r.k177, 2)}</td></tr>
        <tr><td>Horas válidas</td><td class="text-end">${r.horas_validas ?? "--"}</td></tr>
      </table>`
    : `<div class="small text-danger mb-2">${r.motivo || "Dados insuficientes no período."}</div>`;
  return `
    <div style="min-width:230px">
      <div class="fw-bold mb-1">${r.nome}</div>
      <span class="badge ${badgeClasseRisco(risco)} mb-2">${rotuloRisco(risco)}</span>
      ${corpo}
      <button class="btn btn-sm btn-outline-primary w-100" onclick="abrirModalEstacao(${r.api_city_id})">
        <i class="fa-solid fa-chart-line me-1"></i> Ver evolução horária
      </button>
    </div>`;
}

function renderizarBuffers() {
  if (!STATE.geoBuffers) return;
  if (STATE.layerBuffers) STATE.map.removeLayer(STATE.layerBuffers);
  if (STATE.layerRotulos) STATE.map.removeLayer(STATE.layerRotulos);

  const rotulos = [];
  STATE.layerBuffers = L.geoJSON(STATE.geoBuffers, {
    pane: "paneBuffers",
    smoothFactor: 0,
    style: estiloBuffer,
    onEachFeature: (feature, layer) => {
      const r = resultadoDoBuffer(feature.properties);
      const nome = feature.properties.Name;
      const tip = r && r.status === "OK"
        ? `<b>${r.nome}</b><br>${rotuloRisco(normalizarRisco(r.risco))} (${fmt(r.k177, 2)})`
        : `<b>${nome}</b><br>Dados insuficientes`;
      layer.bindTooltip(tip, { sticky: true });
      layer.bindPopup(htmlPopupEstacao(r, nome));
      layer.on({
        mouseover: e => e.target.setStyle({ weight: 2.2, color: "#111", fillOpacity: 0.78 }),
        mouseout: e => STATE.layerBuffers.resetStyle(e.target)
      });

      const centro = layer.getBounds().getCenter();
      const m = L.marker(centro, {
        pane: "paneRotulos",
        interactive: false,
        icon: L.divIcon({
          className: "station-label",
          html: `<span>${nome}</span>`,
          iconSize: [0, 0],
          iconAnchor: [-4, 6]
        })
      });
      rotulos.push(m);
    }
  }).addTo(STATE.map);

  STATE.layerRotulos = L.layerGroup(rotulos).addTo(STATE.map);
}

function adicionarLegenda() {
  const legenda = L.control({ position: "bottomright" });
  legenda.onAdd = () => {
    const div = L.DomUtil.create("div", "map-legend");
    const itens = [
      ["Risco Baixo", "≤ -501", CORES_RISCO["Risco Baixo"]],
      ["Risco Medio", "-501 a 0", CORES_RISCO["Risco Medio"]],
      ["Risco Alto", "0 a 624", CORES_RISCO["Risco Alto"]],
      ["Risco Muito Alto", "> 624", CORES_RISCO["Risco Muito Alto"]],
      ["Abrangência das Estações", "", "#d9d9d9"],
      ["Dados Insuficientes", "< 96 h", CORES_RISCO["Dados Insuficientes"]]
    ];
    div.innerHTML = `<div class="fw-bold mb-1">Legenda SAC Dengue</div>` + itens.map(([k, faixa, cor]) =>
      `<div class="map-legend-item"><span class="legend-color-box" style="background:${cor}"></span>
       ${rotuloRisco(k)} <small class="text-muted ms-auto">${faixa}</small></div>`).join("");
    return div;
  };
  legenda.addTo(STATE.map);
}

// ---------------------------------------------------------------------
// Bloco 3 - KPIs, alertas e gráficos (ranking e balanço hídrico)
// ---------------------------------------------------------------------
function renderizarPeriodo() {
  const p = STATE.dados.periodo;
  document.getElementById("periodoTitulo").textContent = p.descricao;
  document.getElementById("periodoSubtitulo").textContent = p.subtitulo || "";
  document.getElementById("lastUpdatedTime").textContent =
    "Atualizado: " + new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  const badge = document.getElementById("badgeFonteDados");
  if (badge) {
    if (STATE.modo === "previsao") {
      badge.className = "badge bg-info-subtle text-primary border border-primary";
      badge.innerHTML = `<i class="fa-solid fa-cloud-sun-rain me-1"></i> Previsão Open-Meteo Ativa`;
    } else {
      badge.className = "badge bg-success-subtle text-success border border-success";
      badge.innerHTML = `<i class="fa-solid fa-circle-check me-1"></i> API SIMEPAR Operacional`;
    }
  }
}

function renderizarKPIs() {
  const d = STATE.dados.resumo.distribuicao_risco || {};
  const elMuitoAlto = document.getElementById("kpiRiscoMuitoAlto");
  if (elMuitoAlto) elMuitoAlto.textContent = d["Risco Muito Alto"] || 0;
  document.getElementById("kpiRiscoAlto").textContent = d["Risco Alto"] || 0;
  document.getElementById("kpiRiscoMedio").textContent = d["Risco Medio"] || 0;
  document.getElementById("kpiRiscoBaixo").textContent = d["Risco Baixo"] || 0;

  const ok = STATE.dados.resultados.filter(r => r.status === "OK");
  const tMedia = ok.length ? ok.reduce((s, r) => s + (r.temp_media || 0), 0) / ok.length : null;
  const chuvaMedia = ok.length ? ok.reduce((s, r) => s + (r.chuva_total || 0), 0) / ok.length : null;
  document.getElementById("kpiClimaMedio").textContent = `${fmt(tMedia, 1, " °C")} / ${fmt(chuvaMedia, 1, " mm")}`;
  const res = STATE.dados.resumo;
  document.getElementById("kpiEstacoesContadas").textContent =
    `${res.estacoes_calculadas} de ${res.total_estacoes} estações analisadas`;
}

function renderizarAlertas() {
  const alertas = STATE.dados.alertas || [];
  const cont = document.getElementById("alertContainer");
  const lista = document.getElementById("listaCidadesAlerta");
  if (!alertas.length) {
    cont.classList.add("d-none");
    lista.innerHTML = "";
    return;
  }
  cont.classList.remove("d-none");
  lista.innerHTML = alertas.map(a =>
    `<span class="badge bg-warning-subtle text-dark border border-warning" title="${a.motivo || ""}">
       <i class="fa-solid fa-clock me-1"></i>${a.cidade}: ${a.horas_registradas ?? 0}/${a.horas_necessarias}h
     </span>`).join("");
}

function destruirChart(nome) {
  if (STATE.charts[nome]) { STATE.charts[nome].destroy(); STATE.charts[nome] = null; }
}

function configGraficoRanking(ok, tamanhoFonteY = 11) {
  return {
    type: "bar",
    data: {
      labels: ok.map(r => r.nome),
      datasets: [{
        label: "Índice de Risco",
        data: ok.map(r => r.k177),
        backgroundColor: ok.map(r => CORES_RISCO[normalizarRisco(r.risco)]),
        borderColor: "#555",
        borderWidth: 0.6,
        barPercentage: 0.78,
        categoryPercentage: 0.86
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => `Índice: ${fmt(c.raw, 2)} (${rotuloRisco(normalizarRisco(ok[c.dataIndex].risco))})` } }
      },
      scales: {
        y: { ticks: { font: { size: tamanhoFonteY }, autoSkip: false } },
        x: { grid: { color: c => (c.tick.value === 0 ? "#333" : "#eee") } }
      },
      onClick: (_, els) => { if (els.length) abrirModalEstacao(ok[els[0].index].api_city_id); }
    }
  };
}

function configGraficoBalanco(ok, tamanhoFonteX = 10) {
  return {
    type: "bar",
    data: {
      labels: ok.map(r => r.nome),
      datasets: [
        { label: "Chuva (mm)", data: ok.map(r => r.chuva_total), backgroundColor: "rgba(43,108,176,0.75)" },
        { label: "Evapotransp. (mm)", data: ok.map(r => r.evapotranspiracao), backgroundColor: "rgba(221,107,32,0.75)" }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { x: { ticks: { font: { size: tamanhoFonteX }, maxRotation: 65, minRotation: 45, autoSkip: false } } }
    }
  };
}

function renderizarGraficoRanking() {
  destruirChart("ranking");
  const ok = STATE.dados.resultados
    .filter(r => r.status === "OK")
    .sort((a, b) => b.k177 - a.k177);
  const ctx = document.getElementById("chartRanking");
  STATE.charts.ranking = new Chart(ctx, configGraficoRanking(ok, 11));
}

function renderizarGraficoBalanco() {
  destruirChart("balanco");
  const ok = STATE.dados.resultados
    .filter(r => r.status === "OK")
    .sort((a, b) => b.h180 - a.h180);
  const ctx = document.getElementById("chartBalanco");
  STATE.charts.balanco = new Chart(ctx, configGraficoBalanco(ok, 10));
}

function abrirModalGraficoLateral(tipo) {
  if (!STATE.dados) return;
  destruirChart("expandido");
  const modalEl = document.getElementById("modalGraficoExpandido");
  const titulo = document.getElementById("modalGraficoExpandidoTitulo");
  const sub = document.getElementById("modalGraficoExpandidoSubtitulo");
  const ctx = document.getElementById("chartGraficoExpandido");

  sub.textContent = `${STATE.dados.periodo.descricao} • Arraste os cantos ou bordas para redimensionar`;

  if (tipo === "ranking") {
    titulo.innerHTML = `<i class="fa-solid fa-chart-bar me-2"></i>Ranking de Risco por Estação`;
    const ok = STATE.dados.resultados
      .filter(r => r.status === "OK")
      .sort((a, b) => b.k177 - a.k177);
    STATE.charts.expandido = new Chart(ctx, configGraficoRanking(ok, 12));
  } else {
    titulo.innerHTML = `<i class="fa-solid fa-cloud-rain me-2"></i>Balanço Hídrico (Chuva vs Evapotranspiração)`;
    const ok = STATE.dados.resultados
      .filter(r => r.status === "OK")
      .sort((a, b) => b.h180 - a.h180);
    STATE.charts.expandido = new Chart(ctx, configGraficoBalanco(ok, 11));
  }

  bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

// ---------------------------------------------------------------------
// Bloco 4 - Tabela de indicadores e modal de evolução horária
// ---------------------------------------------------------------------
function avaliarFiltroNumerico(valorCelula, expressao) {
  if (!expressao) return true;
  if (valorCelula === null || valorCelula === undefined || Number.isNaN(Number(valorCelula))) return false;
  const v = Number(valorCelula);
  const expr = String(expressao).trim().replace(",", ".");
  const m = expr.match(/^(>=|<=|>|<|=)?\s*(-?\d+(?:\.\d+)?)$/);
  if (m) {
    const op = m[1] || "=";
    const alvo = parseFloat(m[2]);
    if (op === ">") return v > alvo;
    if (op === ">=") return v >= alvo;
    if (op === "<") return v < alvo;
    if (op === "<=") return v <= alvo;
    return Math.abs(v - alvo) < 0.05 || fmt(valorCelula, 2).replace(",", ".").includes(m[2]);
  }
  return fmt(valorCelula, 2).toLowerCase().includes(String(expressao).trim().toLowerCase());
}

function renderizarTabela() {
  if (!STATE.dados || !STATE.dados.resultados) return;
  const filtroGeral = normalizarTexto(document.getElementById("filtroTabela").value);
  const filtrosCol = {};
  document.querySelectorAll(".col-filter").forEach(el => {
    const val = el.value.trim();
    if (val) filtrosCol[el.dataset.col] = val;
    const btnIcon = document.querySelector(`.col-filter-btn[data-col="${el.dataset.col}"]`);
    if (btnIcon) {
      btnIcon.classList.toggle("text-primary", Boolean(val));
      btnIcon.classList.toggle("text-muted", !val);
    }
  });
  const qtdAtivos = Object.keys(filtrosCol).length + (filtroGeral ? 1 : 0);
  const badgeAtivos = document.getElementById("badgeFiltrosAtivos");
  if (badgeAtivos) {
    badgeAtivos.textContent = qtdAtivos;
    badgeAtivos.classList.toggle("d-none", qtdAtivos === 0);
  }
  const btnLimpar = document.getElementById("btnLimparFiltrosTabela");
  if (btnLimpar) btnLimpar.classList.toggle("d-none", qtdAtivos === 0);

  const linhas = [...STATE.dados.resultados]
    .filter(r => {
      const ok = r.status === "OK";
      const riscoNorm = ok ? normalizarRisco(r.risco) : "Dados Insuficientes";
      if (filtroGeral) {
        const textoLinha = normalizarTexto(`${r.nome} ${r.cod_ibge} ${rotuloRisco(riscoNorm)}`);
        if (!textoLinha.includes(filtroGeral)) return false;
      }
      if (filtrosCol.nome && !normalizarTexto(r.nome).includes(normalizarTexto(filtrosCol.nome))) return false;
      if (filtrosCol.cod_ibge && !String(r.cod_ibge).includes(filtrosCol.cod_ibge)) return false;
      if (filtrosCol.status) {
        if (filtrosCol.status === "OK" && !ok) return false;
        if (filtrosCol.status === "INSUF" && ok) return false;
      }
      if (filtrosCol.risco && riscoNorm !== filtrosCol.risco) return false;
      for (const colNum of ["temp_media", "chuva_total", "evapotranspiracao", "k176", "h180", "k177"]) {
        if (filtrosCol[colNum] && !avaliarFiltroNumerico(r[colNum], filtrosCol[colNum])) return false;
      }
      return true;
    })
    .sort((a, b) => {
      const col = STATE.sortCol;
      const mult = STATE.sortAsc ? 1 : -1;
      if (col === "nome") return mult * a.nome.localeCompare(b.nome, "pt-BR");
      if (col === "risco") {
        const ra = ORDEM_RISCO[a.status === "OK" ? normalizarRisco(a.risco) : "Dados Insuficientes"] ?? 0;
        const rb = ORDEM_RISCO[b.status === "OK" ? normalizarRisco(b.risco) : "Dados Insuficientes"] ?? 0;
        return mult * (ra - rb);
      }
      const va = a[col] ?? -999999;
      const vb = b[col] ?? -999999;
      return mult * (Number(va) - Number(vb));
    });

  const corpo = document.getElementById("tabelaCorpo");
  if (!linhas.length) {
    corpo.innerHTML = `<tr><td colspan="11" class="text-center text-muted py-3">Nenhum município encontrado para os filtros aplicados.</td></tr>`;
    return;
  }
  corpo.innerHTML = linhas.map(r => {
    const ok = r.status === "OK";
    const risco = ok ? normalizarRisco(r.risco) : "Dados Insuficientes";
    const status = ok
      ? `<span class="text-success"><i class="fa-solid fa-circle-check me-1"></i>${r.horas_validas}h</span>`
      : `<span class="text-danger" title="${r.motivo || ""}"><i class="fa-solid fa-triangle-exclamation me-1"></i>${r.horas_validas ?? 0}h</span>`;
    return `<tr>
      <td class="fw-semibold">${r.nome}</td>
      <td class="text-muted">${r.cod_ibge}</td>
      <td>${status}</td>
      <td>${fmt(r.temp_media, 1, " °C")}</td>
      <td>${fmt(r.chuva_total, 1, " mm")}</td>
      <td>${fmt(r.evapotranspiracao, 1, " mm")}</td>
      <td>${fmt(r.k176, 2)}</td>
      <td>${fmt(r.h180, 2)}</td>
      <td class="fw-bold">${fmt(r.k177, 2)}</td>
      <td><span class="badge ${badgeClasseRisco(risco)}">${rotuloRisco(risco)}</span></td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-secondary" title="Localizar no mapa" onclick="focarEstacaoMapa(${r.cod_ibge})">
          <i class="fa-solid fa-location-crosshairs"></i></button>
        <button class="btn btn-sm btn-outline-primary" title="Evolução horária" onclick="abrirModalEstacao(${r.api_city_id})">
          <i class="fa-solid fa-chart-line"></i></button>
      </td>
    </tr>`;
  }).join("");
}

function focarEstacaoMapa(codIbge) {
  if (!STATE.layerBuffers) return;
  let alvo = null;
  STATE.layerBuffers.eachLayer(l => {
    const r = resultadoDoBuffer(l.feature.properties);
    if (!alvo && r && String(r.cod_ibge) === String(codIbge)) alvo = l;
  });
  if (alvo) {
    document.getElementById("map").scrollIntoView({ behavior: "smooth", block: "center" });
    STATE.map.fitBounds(alvo.getBounds(), { maxZoom: 9, padding: [30, 30] });
    alvo.openPopup();
  }
}

async function abrirModalEstacao(cityId) {
  const r = STATE.dados.resultados.find(x => x.api_city_id === cityId);
  const nome = r ? r.nome : `Estação ${cityId}`;
  document.getElementById("modalEstacaoTitulo").textContent = `Evolução Meteorológica • ${nome}`;
  document.getElementById("modalEstacaoSubtitulo").textContent = "Carregando dados horários...";
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("modalEstacao"));
  modal.show();
  destruirChart("horario");

  try {
    const p = queryPeriodo();
    p.set("city_id", cityId);
    const resp = await fetchJSON(`/api/estacao_historico?${p.toString()}`);
    const dados = resp.dados || [];
    const sub = document.getElementById("modalEstacaoSubtitulo");
    if (!dados.length) {
      sub.textContent = "Não há registros horários para esta estação no período selecionado.";
      return;
    }
    const resumo = r && r.status === "OK"
      ? `<br>${rotuloRisco(normalizarRisco(r.risco))} (${fmt(r.k177, 2)})`
      : (r ? `<br>${r.motivo || "Dados insuficientes"}` : "");
    sub.innerHTML = `${STATE.dados.periodo.descricao}<br>${dados.length} registros horários${resumo}`;

    const labels = dados.map(d => new Date(d.datetime).toLocaleString("pt-BR", {
      day: "2-digit", month: "2-digit", hour: "2-digit"
    }));
    STATE.charts.horario = new Chart(document.getElementById("chartEstacaoHoraria"), {
      data: {
        labels,
        datasets: [
          { type: "line", label: "Temp. média (°C)", data: dados.map(d => d.tmed), borderColor: "#c53030",
            backgroundColor: "rgba(197,48,48,0.1)", pointRadius: 0, borderWidth: 1.5, yAxisID: "yT", tension: 0.25 },
          { type: "line", label: "Temp. máx (°C)", data: dados.map(d => d.tmax), borderColor: "rgba(237,137,54,0.6)",
            pointRadius: 0, borderWidth: 1, borderDash: [4, 3], yAxisID: "yT" },
          { type: "line", label: "Temp. mín (°C)", data: dados.map(d => d.tmin), borderColor: "rgba(66,153,225,0.6)",
            pointRadius: 0, borderWidth: 1, borderDash: [4, 3], yAxisID: "yT" },
          { type: "bar", label: "Chuva (mm/h)", data: dados.map(d => d.prec), backgroundColor: "rgba(43,108,176,0.6)", yAxisID: "yP" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { maxTicksLimit: 14, font: { size: 9 } } },
          yT: { position: "left", title: { display: true, text: "°C" } },
          yP: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, title: { display: true, text: "mm" } }
        }
      }
    });
  } catch (e) {
    document.getElementById("modalEstacaoSubtitulo").textContent = "Erro ao carregar dados: " + e.message;
  }
}

// Expor funções usadas em atributos onclick
window.abrirModalEstacao = abrirModalEstacao;
window.focarEstacaoMapa = focarEstacaoMapa;

// ---------------------------------------------------------------------
// Bloco 5 - Carregamento, controles, exportação QGIS e inicialização
// ---------------------------------------------------------------------
async function carregarConfig() {
  STATE.config = await fetchJSON("/api/config");
  const sel = document.getElementById("selectSE");
  const selExp = document.getElementById("selectSEExport");
  const semanas = STATE.config.semanas || [];
  const opcoesHtml = semanas.map(s =>
    `<option value="${s.ano}-${s.semana}">${s.label}${s.is_atual ? " • em andamento" : ""}</option>`).join("");
  sel.innerHTML = opcoesHtml;
  if (selExp) selExp.innerHTML = opcoesHtml;
  // Padrão: última SE completa (a primeira não-atual)
  const padrao = semanas.find(s => !s.is_atual) || semanas[0];
  if (padrao) {
    const val = `${padrao.ano}-${padrao.semana}`;
    sel.value = val;
    if (selExp) selExp.value = val;
    STATE.ano = padrao.ano;
    STATE.semana = padrao.semana;
  }
}

async function carregarDados() {
  if (STATE.carregando) return;
  STATE.carregando = true;
  document.getElementById("periodoTitulo").textContent = "Carregando dados do período...";
  try {
    STATE.dados = await fetchJSON(`/api/dados?${queryPeriodo().toString()}`);
    STATE.resultadosPorIbge = {};
    STATE.resultadosPorNome = {};
    for (const r of STATE.dados.resultados) {
      STATE.resultadosPorIbge[String(r.cod_ibge)] = r;
      STATE.resultadosPorNome[normalizarTexto(r.nome)] = r;
    }
    renderizarPeriodo();
    renderizarKPIs();
    renderizarAlertas();
    renderizarBuffers();
    renderizarGraficoRanking();
    renderizarGraficoBalanco();
    renderizarTabela();
  } catch (e) {
    document.getElementById("periodoTitulo").textContent = "Falha ao carregar dados";
    mostrarToast("Erro ao carregar dados: " + e.message, "erro");
  } finally {
    STATE.carregando = false;
  }
}

function definirModo(modo) {
  STATE.modo = modo;
  document.getElementById("btnModo7Dias").classList.toggle("active", modo === "7dias");
  const btnPrev = document.getElementById("btnModoPrevisao");
  if (btnPrev) btnPrev.classList.toggle("active", modo === "previsao");
  document.getElementById("btnModoSE").classList.toggle("active", modo === "se");
  document.getElementById("seSelectorContainer").classList.toggle("d-none", modo !== "se");
  const cardMapa = document.getElementById("cardMapaOficial");
  if (cardMapa) cardMapa.classList.toggle("d-none", modo !== "se");
  carregarDados();
}

function urlExportacao(download) {
  const p = new URLSearchParams({ tipo: "se" });
  if (STATE.ano && STATE.semana) {
    p.set("ano", STATE.ano);
    p.set("semana", STATE.semana);
  }
  if (download) p.set("download", "1");
  p.set("_", Date.now()); // evita cache do navegador
  return `/api/exportar_mapa?${p.toString()}`;
}

async function baixarMapaOficial(btn) {
  setBotaoCarregando(btn, true, "Gerando mapa oficial...");
  try {
    const resp = await fetch(urlExportacao(true));
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try { const j = await resp.json(); if (j.erro) msg = j.erro; } catch (_) {}
      throw new Error(msg);
    }
    const blob = await resp.blob();
    const disp = resp.headers.get("Content-Disposition") || "";
    const m = disp.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    const nome = m ? decodeURIComponent(m[1]) : "Mapa_SACDengue.jpg";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    mostrarToast(`Mapa oficial gerado: ${nome}`, "sucesso");
  } catch (e) {
    mostrarToast("Erro ao exportar mapa oficial: " + e.message, "erro");
  } finally {
    setBotaoCarregando(btn, false);
  }
}

function previsualizarMapa() {
  const img = document.getElementById("imgPreviewMapa");
  const loading = document.getElementById("previewLoading");
  const btnDl = document.getElementById("btnModalDownload");
  img.classList.add("d-none");
  loading.classList.remove("d-none");
  loading.innerHTML = `<div class="spinner-border text-light me-2"></div> Gerando mapa oficial em alta resolução...`;
  bootstrap.Modal.getOrCreateInstance(document.getElementById("modalPreviewMapa")).show();

  img.onload = () => { loading.classList.add("d-none"); img.classList.remove("d-none"); };
  img.onerror = () => { loading.innerHTML = `<span class="text-danger">Falha ao gerar o mapa oficial.</span>`; };
  img.src = urlExportacao(false);
  btnDl.href = urlExportacao(true);
}

async function sincronizarAPI(btn) {
  setBotaoCarregando(btn, true, "Sincronizando...");
  try {
    const r = await fetchJSON("/api/sincronizar", { method: "POST" });
    mostrarToast(`Sincronização concluída: ${r.registros_atualizados} registros atualizados.`, "sucesso");
    await carregarDados();
  } catch (e) {
    mostrarToast("Erro na sincronização com o SIMEPAR: " + e.message, "erro");
  } finally {
    setBotaoCarregando(btn, false);
  }
}

function registrarEventos() {
  document.getElementById("btnModo7Dias").addEventListener("click", () => definirModo("7dias"));
  const btnPrev = document.getElementById("btnModoPrevisao");
  if (btnPrev) btnPrev.addEventListener("click", () => definirModo("previsao"));
  document.getElementById("btnModoSE").addEventListener("click", () => definirModo("se"));
  document.getElementById("selectSE").addEventListener("change", e => {
    const [ano, semana] = e.target.value.split("-").map(Number);
    STATE.ano = ano;
    STATE.semana = semana;
    const selExp = document.getElementById("selectSEExport");
    if (selExp) selExp.value = e.target.value;
    carregarDados();
  });
  const selExp = document.getElementById("selectSEExport");
  if (selExp) {
    selExp.addEventListener("change", e => {
      const [ano, semana] = e.target.value.split("-").map(Number);
      STATE.ano = ano;
      STATE.semana = semana;
      document.getElementById("selectSE").value = e.target.value;
      if (STATE.modo === "se") carregarDados();
    });
  }
  document.getElementById("filtroTabela").addEventListener("input", renderizarTabela);
  const linhaFiltros = document.getElementById("linhaFiltrosTabela");
  const btnToggleFiltros = document.getElementById("btnToggleFiltrosTabela");
  if (btnToggleFiltros && linhaFiltros) {
    btnToggleFiltros.addEventListener("click", () => {
      const oculta = linhaFiltros.classList.toggle("d-none");
      btnToggleFiltros.classList.toggle("active", !oculta);
    });
  }
  document.querySelectorAll(".col-filter-btn").forEach(icon => {
    icon.addEventListener("click", e => {
      e.stopPropagation();
      if (linhaFiltros) {
        linhaFiltros.classList.remove("d-none");
        if (btnToggleFiltros) btnToggleFiltros.classList.add("active");
        const input = linhaFiltros.querySelector(`.col-filter[data-col="${icon.dataset.col}"]`);
        if (input) setTimeout(() => input.focus(), 40);
      }
    });
  });
  document.querySelectorAll(".col-filter").forEach(el => {
    el.addEventListener("input", renderizarTabela);
    el.addEventListener("change", renderizarTabela);
  });
  document.querySelectorAll(".sortable-th").forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (STATE.sortCol === col) {
        STATE.sortAsc = !STATE.sortAsc;
      } else {
        STATE.sortCol = col;
        STATE.sortAsc = col === "nome";
      }
      document.querySelectorAll(".sortable-th .sort-icon").forEach(ic => {
        ic.className = "fa-solid fa-sort ms-1 text-muted sort-icon";
      });
      const ic = th.querySelector(".sort-icon");
      if (ic) {
        ic.className = `fa-solid ${STATE.sortAsc ? "fa-sort-up" : "fa-sort-down"} ms-1 text-primary sort-icon`;
      }
      renderizarTabela();
    });
  });
  const btnLimpar = document.getElementById("btnLimparFiltrosTabela");
  if (btnLimpar) {
    btnLimpar.addEventListener("click", () => {
      document.getElementById("filtroTabela").value = "";
      document.querySelectorAll(".col-filter").forEach(el => { el.value = ""; });
      STATE.sortCol = "k177";
      STATE.sortAsc = false;
      document.querySelectorAll(".sortable-th .sort-icon").forEach(ic => {
        ic.className = "fa-solid fa-sort ms-1 text-muted sort-icon";
      });
      const thDefault = document.querySelector('.sortable-th[data-col="k177"] .sort-icon');
      if (thDefault) thDefault.className = "fa-solid fa-sort-down ms-1 text-primary sort-icon";
      renderizarTabela();
    });
  }
  document.getElementById("btnResetMapZoom").addEventListener("click", () => STATE.map.fitBounds(PR_BOUNDS));
  document.getElementById("btnSincronizar").addEventListener("click", e => sincronizarAPI(e.currentTarget));
  document.getElementById("btnGerarBaixarMapa").addEventListener("click", e => baixarMapaOficial(e.currentTarget));
  document.getElementById("btnPreviewMapa").addEventListener("click", previsualizarMapa);
  const btnExpR = document.getElementById("btnExpandirRanking");
  if (btnExpR) btnExpR.addEventListener("click", () => abrirModalGraficoLateral("ranking"));
  const btnExpB = document.getElementById("btnExpandirBalanco");
  if (btnExpB) btnExpB.addEventListener("click", () => abrirModalGraficoLateral("balanco"));
  initModaisInterativos();
}

function initModaisInterativos() {
  const dirs = ["n", "s", "e", "w", "ne", "nw", "se", "sw"];
  document.querySelectorAll(".modal-resizable").forEach(content => {
    let tx = 0, ty = 0;

    // 1. Arrastar pelo cabeçalho
    const header = content.querySelector(".modal-draggable-header");
    if (header) {
      header.addEventListener("mousedown", e => {
        if (e.target.closest("button, a, input, select")) return;
        e.preventDefault();
        const startX = e.clientX - tx;
        const startY = e.clientY - ty;
        const onMove = ev => {
          tx = ev.clientX - startX;
          ty = ev.clientY - startY;
          content.style.transform = `translate(${tx}px, ${ty}px)`;
        };
        const onUp = () => {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });
    }

    // 2. Redimensionar puxando qualquer canto ou borda
    dirs.forEach(dir => {
      const h = document.createElement("div");
      h.className = `resizer-handle resizer-${dir}`;
      content.appendChild(h);

      h.addEventListener("mousedown", e => {
        e.preventDefault();
        e.stopPropagation();
        const startX = e.clientX;
        const startY = e.clientY;
        const rect = content.getBoundingClientRect();
        const startW = rect.width;
        const startH = rect.height;
        const startTx = tx;
        const startTy = ty;
        const minW = parseInt(content.style.minWidth, 10) || 420;
        const minH = parseInt(content.style.minHeight, 10) || 320;

        const onMove = ev => {
          const dx = ev.clientX - startX;
          const dy = ev.clientY - startY;
          let newW = startW;
          let newH = startH;

          if (dir.includes("e")) newW = Math.max(minW, startW + dx);
          if (dir.includes("w")) newW = Math.max(minW, startW - dx);
          if (dir.includes("s")) newH = Math.max(minH, startH + dy);
          if (dir.includes("n")) newH = Math.max(minH, startH - dy);

          // Compensa o deslocamento centralizado do flex para manter a borda oposta fixa
          const appliedDx = newW - startW;
          const appliedDy = newH - startH;
          if (dir.includes("e")) tx = startTx + appliedDx / 2;
          if (dir.includes("w")) tx = startTx - appliedDx / 2;
          if (dir.includes("s")) ty = startTy + appliedDy / 2;
          if (dir.includes("n")) ty = startTy - appliedDy / 2;

          content.style.width = `${newW}px`;
          content.style.height = `${newH}px`;
          content.style.transform = `translate(${tx}px, ${ty}px)`;
          if (STATE.charts.horario) STATE.charts.horario.resize();
          if (STATE.charts.expandido) STATE.charts.expandido.resize();
        };

        const onUp = () => {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    initMapa();
    registrarEventos();
    await Promise.all([carregarConfig(), carregarCamadasBase()]);
    await carregarDados();
  } catch (e) {
    console.error(e);
    mostrarToast("Erro ao inicializar o painel: " + e.message, "erro");
  }
});
