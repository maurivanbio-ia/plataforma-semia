let selected = null;
let currentJob = null;
let currentReport = null;

const el = (id) => document.getElementById(id);
const fileInput = el('fileInput');
const dropzone = el('dropzone');
const analyzeBtn = el('analyzeBtn');
const resetBtn = el('resetBtn');
const statusBox = el('status');

function fmtBytes(n) {
  if (n == null) return '—';
  const units = ['B','KB','MB','GB'];
  let i = 0, v = Number(n);
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i ? 2 : 0)} ${units[i]}`;
}

function pretty(v) {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'Sim' : 'Não';
  if (Array.isArray(v)) return v.length ? v.join(', ') : '—';
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

function setStatus(text, visible = true) {
  statusBox.textContent = text;
  statusBox.classList.toggle('hidden', !visible);
}

function pick(file) {
  selected = file || null;
  if (selected) {
    el('selectedFile').textContent = `${selected.name} · ${fmtBytes(selected.size)}`;
    el('selectedFile').classList.remove('hidden');
    analyzeBtn.disabled = false;
    resetBtn.disabled = false;
  }
}

fileInput.addEventListener('change', () => pick(fileInput.files[0]));
['dragenter','dragover'].forEach(evt => dropzone.addEventListener(evt, e => {
  e.preventDefault(); dropzone.classList.add('drag');
}));
['dragleave','drop'].forEach(evt => dropzone.addEventListener(evt, e => {
  e.preventDefault(); dropzone.classList.remove('drag');
}));
dropzone.addEventListener('drop', e => pick(e.dataTransfer.files[0]));

resetBtn.addEventListener('click', () => {
  selected = null; currentJob = null; currentReport = null; fileInput.value = '';
  el('selectedFile').classList.add('hidden');
  el('results').classList.add('hidden');
  el('cleanResult').classList.add('hidden');
  analyzeBtn.disabled = true; resetBtn.disabled = true; setStatus('', false);
});

async function checkHealth() {
  const badge = el('healthBadge');
  try {
    const r = await fetch('/api/health');
    const j = await r.json();
    if (j.ok) {
      badge.textContent = 'Serviço operacional'; badge.className = 'health ok';
    } else {
      badge.textContent = 'Serviço indisponível'; badge.className = 'health error';
    }
  } catch {
    badge.textContent = 'Falha de conexão'; badge.className = 'health error';
  }
}

function renderKV(target, obj, labels = {}) {
  const node = el(target); node.innerHTML = '';
  const entries = Object.entries(obj || {});
  if (!entries.length) { node.innerHTML = '<div class="kv-row"><div class="kv-key">Sem dados</div><div class="kv-value">—</div></div>'; return; }
  entries.forEach(([k,v]) => {
    const row = document.createElement('div'); row.className = 'kv-row';
    const key = document.createElement('div'); key.className = 'kv-key'; key.textContent = labels[k] || k;
    const val = document.createElement('div'); val.className = 'kv-value'; val.textContent = pretty(v);
    row.append(key,val); node.appendChild(row);
  });
}

function renderFindings(items) {
  const node = el('findings'); node.innerHTML = '';
  (items || []).forEach(item => {
    const card = document.createElement('div'); card.className = `finding ${item.severity || 'info'}`;
    card.innerHTML = `<div class="finding-title"></div><div class="finding-detail"></div>`;
    card.children[0].textContent = item.title || 'Achado';
    card.children[1].textContent = item.detail || '';
    node.appendChild(card);
  });
}

function renderMedia(media) {
  el('mediaCount').textContent = String((media || []).length);
  const wrap = el('mediaTableWrap');
  if (!media || !media.length) { wrap.innerHTML = '<p class="subtitle">Nenhuma imagem incorporada listada.</p>'; return; }
  const rows = media.map(m => {
    const meta = m.metadata || {};
    const exif = m.exif || {};
    const software = m.software || meta.Software || meta.software || exif.Software || '—';
    return `<tr><td>${escapeHtml(m.name || '—')}</td><td>${escapeHtml(m.format || '—')}</td><td>${escapeHtml(`${m.width || '—'} × ${m.height || '—'}`)}</td><td>${escapeHtml(String(software))}</td><td>${escapeHtml(fmtBytes(m.bytes))}</td></tr>`;
  }).join('');
  wrap.innerHTML = `<table><thead><tr><th>Parte</th><th>Formato</th><th>Dimensões</th><th>Software/metadado</th><th>Tamanho</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function renderReport(j) {
  currentReport = j; currentJob = j.job_id;
  const forensic = j.forensic || {};
  const service = j.service || {};
  el('results').classList.remove('hidden');
  el('cleanResult').classList.add('hidden');
  el('resultTitle').textContent = j.original_name;
  el('metricStatus').textContent = j.summary?.status === 'atenção' ? 'Requer atenção' : 'Sem alertas verificáveis';
  el('metricHash').textContent = j.sha256;
  el('metricSize').textContent = fmtBytes(j.size_bytes);
  el('metricFormat').textContent = forensic.format || service.kind || '—';
  el('reportDownloadPdf').href = `/api/download/${j.job_id}/report.pdf`;
  el('reportDownload').href = `/api/download/${j.job_id}/report.json`;
  renderFindings(j.summary?.findings || []);
  el('disclaimer').textContent = j.summary?.disclaimer || '';

  renderKV('serviceSummary', {
    ok: service.ok,
    kind: service.kind,
    suspicious: service.suspicious,
    has_c2pa: service.report?.has_c2pa,
    has_ai_metadata: service.report?.has_ai_metadata,
  }, {ok:'Serviço OK', kind:'Tipo', suspicious:'Sinais suspeitos', has_c2pa:'C2PA', has_ai_metadata:'Metadado de IA'});

  renderKV('dlpSummary', forensic.dlp_findings || {}, {
    cpf: 'CPFs detectados',
    cnpj: 'CNPJs detectados',
    email: 'E-mails detectados',
    processo_judicial: 'Processos judiciais',
    coordenadas: 'Coordenadas GPS'
  });

  renderKV('coreProps', forensic.core_properties || {}, {
    creator:'Autor', last_modified_by:'Último modificador', created:'Criado', modified:'Modificado', revision:'Revisão', title:'Título', subject:'Assunto', keywords:'Palavras-chave', category:'Categoria'
  });

  const hist = forensic.revision_history || {};
  renderKV('docxHistory', {
    unique_rsids: hist.unique_rsids,
    track_revisions_enabled: hist.track_revisions_enabled,
    insertions: hist.insertions,
    deletions: hist.deletions,
    comments: forensic.comments?.count,
    content_controls: forensic.content_controls?.count,
    unicode_hits: Object.values(forensic.unicode_suspects || {}).reduce((a,b)=>a+Number(b||0),0),
    fields: forensic.fields || {},
  }, {unique_rsids:'RSIDs únicos', track_revisions_enabled:'Controle de alterações ativo', insertions:'Inserções rastreadas', deletions:'Exclusões rastreadas', comments:'Comentários', content_controls:'Controles de conteúdo', unicode_hits:'Unicode suspeito', fields:'Campos'});

  renderKV('customXml', {
    item_count: forensic.custom_xml?.item_count,
    sharepoint_indicators: forensic.custom_xml?.sharepoint_indicators,
    earliest_zip_timestamp: forensic.zip_timeline?.earliest,
    latest_zip_timestamp: forensic.zip_timeline?.latest,
  }, {item_count:'Itens custom XML', sharepoint_indicators:'Indicador SharePoint/Content Type', earliest_zip_timestamp:'Timestamp interno mais antigo', latest_zip_timestamp:'Timestamp interno mais recente'});

  renderMedia(forensic.media || []);
  el('rawReport').textContent = JSON.stringify(j, null, 2);
  window.scrollTo({top: el('results').offsetTop - 18, behavior:'smooth'});
}

analyzeBtn.addEventListener('click', async () => {
  if (!selected) return;
  analyzeBtn.disabled = true;
  setStatus('Enviando e analisando o arquivo. Nenhuma alteração será feita no original…');
  try {
    const fd = new FormData(); fd.append('file', selected);
    const r = await fetch('/api/analyze', {method:'POST', body:fd});
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || 'Falha na análise.');
    renderReport(j); setStatus('Análise concluída.');
  } catch (err) {
    setStatus(`Erro: ${err.message}`);
  } finally { analyzeBtn.disabled = false; }
});

el('cleanBtn').addEventListener('click', async () => {
  if (!currentJob) return;
  const btn = el('cleanBtn'); btn.disabled = true; btn.textContent = 'Higienizando…';
  setStatus('Gerando uma nova cópia higienizada e executando inspeção pós-limpeza…');
  try {
    const r = await fetch(`/api/clean/${currentJob}`, {method:'POST'});
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || 'Falha na higienização.');
    const c = j.clean;
    el('cleanResult').classList.remove('hidden');
    el('cleanDownload').href = `/api/download/${currentJob}/cleaned`;
    renderKV('cleanMeta', {
      name: c.name,
      size_bytes: fmtBytes(c.size_bytes),
      sha256: c.sha256,
      size_delta: c.comparison?.size_delta,
      sha256_changed: c.comparison?.sha256_changed,
      post_suspicious: c.post_inspection?.suspicious,
    }, {name:'Arquivo', size_bytes:'Tamanho', sha256:'SHA-256', size_delta:'Diferença de bytes', sha256_changed:'Hash alterado', post_suspicious:'Sinais na reinspeção'});
    
    const diff = c.comparison?.diff_forensic || {};
    renderKV('cleanDiff', {
      comments_removed: diff.comments_removed,
      properties_cleaned: diff.properties_cleaned,
      unicode_suspects_removed: diff.unicode_suspects_removed,
      media_removed: diff.media_removed,
      custom_xml_removed: diff.custom_xml_removed,
      revision_history_cleaned: diff.revision_history_cleaned
    }, {
      comments_removed: 'Comentários removidos',
      properties_cleaned: 'Propriedades limpas',
      unicode_suspects_removed: 'Unicode suspeito removido',
      media_removed: 'Mídias removidas',
      custom_xml_removed: 'Custom XML removido',
      revision_history_cleaned: 'Histórico de revisão limpo'
    });
    
    setStatus('Cópia higienizada concluída. O original permaneceu preservado.');
    el('cleanResult').scrollIntoView({behavior:'smooth', block:'center'});
  } catch (err) {
    setStatus(`Erro: ${err.message}`);
  } finally { btn.disabled = false; btn.textContent = 'Gerar cópia higienizada'; }
});

checkHealth();
