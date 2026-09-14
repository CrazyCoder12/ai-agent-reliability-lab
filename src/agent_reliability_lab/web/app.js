(() => {
  'use strict';
  const descriptions = {
    none: ['Reference agent', 'Expected behavior across the full scenario suite'],
    false_success: ['False completion', 'Claims a refund without a persisted transaction'],
    auth_bypass: ['Authorization bypass', 'Allows access to another customer’s order'],
    policy_bypass: ['Policy bypass', 'Approves orders outside the refund rules'],
    duplicate_refund: ['Duplicate refund', 'Repeats a side effect after a lost response'],
    follow_injection: ['Instruction boundary failure', 'Follows instructions from an untrusted order note']
  };
  let data, selectedRun = 0, selectedCase = 0, view = 'checks', failedOnly = false;
  const el = id => document.getElementById(id);
  function node(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
  const current = () => data.runs[selectedRun];
  const human = value => value.replaceAll('_', ' ');
  function render() {
    const baseline = data.runs.find(r => r.fault === 'none');
    el('baseline-count').textContent = baseline ? baseline.passed : '—';
    el('baseline-total').textContent = baseline ? `/ ${baseline.total}` : '';
    const mutants = data.runs.filter(r => r.fault !== 'none');
    el('fault-count').textContent = mutants.length ? mutants.filter(r => r.failed > 0).length : '—';
    el('fault-total').textContent = mutants.length ? `/ ${mutants.length}` : '';
    el('checks-count').textContent = current().cases[0]?.checks.length ?? '—';
    el('fault-dots').replaceChildren(...mutants.map(r => node('i', undefined, r.failed ? '' : 'missed')));
    el('suite-label').textContent = `${data.suite_version || current().suite_version} · ${current().total} cases per variant`;
    el('run-meta').textContent = `Dataset ${current().dataset_sha256.slice(0, 10)} · ${new Date(current().created_at).toLocaleDateString()}`;
    el('variant-score').textContent = `${current().passed}/${current().total} passed`;
    el('variant-score').className = 'score-badge' + (current().failed ? ' failed' : '');
    el('fault-list').replaceChildren(...data.runs.map((run, index) => {
      const b = node('button', undefined, 'fault-option' + (index === selectedRun ? ' selected' : ''));
      b.setAttribute('aria-pressed', String(index === selectedRun));
      b.append(node('span', index === selectedRun ? '●' : '○', 'fault-symbol'));
      const copy = node('span'); const desc = descriptions[run.fault] || [run.fault, 'Evaluation variant'];
      copy.append(node('div', desc[0], 'fault-name'), node('div', desc[1], 'fault-description')); b.append(copy);
      b.append(node('span', run.failed ? `${run.failed} failed` : 'All passed', 'fault-result ' + (run.failed ? 'fail' : 'pass')));
      b.addEventListener('click', () => { selectedRun = index; selectedCase = Math.max(0, run.cases.findIndex(c => !c.passed)); render(); });
      return b;
    }));
    el('category-bars').replaceChildren(...Object.entries(current().categories).map(([name, c]) => {
      const row = node('div', undefined, 'category-row'); const track = node('div', undefined, 'bar-track');
      const fill = node('div', undefined, 'bar-fill'); fill.style.width = `${100*c.passed/c.total}%`; track.append(fill);
      row.append(node('span', name), track, node('span', `${c.passed}/${c.total}`, 'category-score')); return row;
    }));
    renderTable(); renderCase();
  }
  function renderTable() {
    const query = el('search').value.toLowerCase();
    const rows = current().cases.map((c, index) => ({c,index})).filter(({c}) => (!failedOnly || !c.passed) && `${c.name} ${c.scenario_id} ${c.category}`.toLowerCase().includes(query));
    el('empty-state').hidden = rows.length > 0;
    el('scenario-table').replaceChildren(...rows.map(({c,index}) => {
      const tr = node('tr', undefined, index === selectedCase ? 'selected' : ''); tr.tabIndex = 0;
      tr.setAttribute('aria-label', `${c.name}: ${c.passed ? 'passed' : 'failed'}. Inspect evidence.`);
      const name = node('td'); name.append(node('span', c.name, 'case-name'), node('span', c.scenario_id + (current().trials > 1 ? ` · trial ${c.trial}` : ''), 'case-id'));
      const badge = node('td'); badge.append(node('span', c.passed ? '✓ Passed' : '× Failed', 'status-badge' + (c.passed ? '' : ' fail')));
      tr.append(name, node('td', c.category), badge);
      const choose = () => {selectedCase = index; renderTable(); renderCase();};
      tr.addEventListener('click', choose); tr.addEventListener('keydown', e => {if(e.key === 'Enter' || e.key === ' ') {e.preventDefault(); choose();}});
      return tr;
    }));
  }
  function renderCase() {
    const c = current().cases[selectedCase]; if (!c) return;
    el('case-number').textContent = `${String(selectedCase+1).padStart(2,'0')} / ${current().total}`;
    el('case-title').textContent = c.name; el('case-message').textContent = c.result.message;
    const area = el('case-evidence'); area.replaceChildren();
    if (view === 'checks') {
      [...c.checks].sort((a,b) => Number(a.passed)-Number(b.passed)).forEach(check => {
        const row = node('div', undefined, 'check-row' + (check.passed ? '' : ' fail'));
        const body = node('div', undefined, 'check-body'); body.append(node('strong', human(check.name)), node('p', check.detail));
        if (!check.passed) body.append(node('div', `Expected: ${JSON.stringify(check.expected)} · Actual: ${JSON.stringify(check.actual)}`, 'check-values'));
        row.append(node('span', check.passed ? '✓' : '×', 'check-mark'), body); area.append(row);
      });
    } else if (view === 'trace') {
      if (!c.trace.length) area.append(node('p', 'No tool calls. This request did not require an action.', 'empty-state'));
      c.trace.forEach(event => {const card = node('div', undefined, 'trace-card'); const title = node('div', undefined, 'trace-title');
        title.append(node('span', `${event.sequence}. ${event.tool}`), node('span', event.outcome));
        card.append(title, node('pre', JSON.stringify({arguments:event.arguments, response:event.response}, null, 2))); area.append(card);});
    } else {
      area.append(node('div', 'BEFORE · refunds table', 'detail-label'), node('pre', JSON.stringify(c.before,null,2), 'state-block'),
                  node('div', 'AFTER · refunds table', 'detail-label'), node('pre', JSON.stringify(c.after,null,2), 'state-block'));
    }
  }
  async function load() {
    const button = el('run-button'); button.disabled = true; el('error').hidden = true;
    try {
      const embedded = el('report-data');
      if (embedded) {data = JSON.parse(embedded.textContent); button.querySelector('span').textContent = 'Reset report view';}
      else {const response = await fetch('/api/experiment'); if(!response.ok) throw new Error(`Server returned ${response.status}`); data = await response.json();}
      selectedRun = 0; selectedCase = 0; render();
    } catch (error) {el('error').textContent = `Unable to load the experiment: ${error.message}. Start the local server with agent-lab serve, or open an exported report.html.`; el('error').hidden = false;}
    finally {button.disabled = false;}
  }
  function boot() {
    el('run-button').addEventListener('click', load);
    el('search').addEventListener('input', () => {if (data) renderTable();});
    el('failed-only').addEventListener('click', () => {failedOnly = !failedOnly; el('failed-only').setAttribute('aria-pressed',String(failedOnly)); if(data) renderTable();});
    document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
      view = button.dataset.view; document.querySelectorAll('[data-view]').forEach(tab => tab.setAttribute('aria-selected',String(tab === button)));
      el('case-evidence').setAttribute('aria-labelledby',button.id); if(data) renderCase();
    }));
    load();
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
