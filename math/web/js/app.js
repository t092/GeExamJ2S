// JHexam Math Viewer — read-only question bank viewer
const CN_DIGIT = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '\u3127': 1 };

function figNum(figId) {
  // 圖(一) → 1, 圖(十二) → 12, 表(一) → 1
  const m = figId.match(/[圖表]\((.+)\)/);
  if (!m) return null;
  const cn = m[1];
  if (cn === '十') return 10;
  if (cn.startsWith('十')) return 10 + (CN_DIGIT[cn[1]] || 0);
  if (cn.endsWith('十')) return (CN_DIGIT[cn[0]] || 1) * 10;
  if (cn.includes('十')) {
    const [a, b] = cn.split('十');
    return (CN_DIGIT[a] || 1) * 10 + (CN_DIGIT[b] || 0);
  }
  return CN_DIGIT[cn] || parseInt(cn) || null;
}

function figFile(figId, year) {
  // 圖(一) → 115p01.jpg, 表(一) → 115t01.jpg
  const n = figNum(figId);
  if (n === null) return null;
  const prefix = figId.startsWith('表') ? 't' : 'p';
  return `../pic/${year}${prefix}${String(n).padStart(2, '0')}.jpg`;
}

const App = {
  questions: [],
  filtered: [],
  currentIdx: 0,
  year: '115',
  // 日後新增年份時，加入此陣列並放入 data/<year>.json
  availableYears: ['115'],

  // ── boot ──────────────────────────────────────
  async init() {
    this.buildYearSelect();
    this.bindViewer();
    const ok = await this.loadYear(this.year);
    if (ok) this.showViewer();
  },

  // ── year selector ─────────────────────────────
  buildYearSelect() {
    const sel = document.getElementById('year-select');
    sel.innerHTML = this.availableYears
      .map(y => `<option value="${y}">${y}年</option>`)
      .join('');
    sel.value = this.year;
  },

  async switchYear(year) {
    if (year === this.year) return;
    const ok = await this.loadYear(year);
    if (!ok) {
      document.getElementById('year-select').value = this.year;
      return;
    }
    this.year = year;
    this.showViewer();
  },

  showViewer() {
    document.getElementById('year-select').value = this.year;
    this.applyFilter();
    this.render();
  },

  // ── data loading ──────────────────────────────
  async loadYear(year) {
    try {
      const res = await fetch(`../data/${year}.json`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.questions = await res.json();
      return true;
    } catch (e) {
      alert(`無法載入題庫 data/${year}.json\n\n請從專案根目錄啟動 server：\npython -m http.server 8000\n\n再開啟 http://localhost:8000/math/web/index.html`);
      return false;
    }
  },

  // ── filter ────────────────────────────────────
  applyFilter() {
    const filter = document.getElementById('filter-select').value;
    this.filtered = this.questions.filter(q => {
      if (filter === 'choice') return q.type === '選擇題';
      if (filter === 'group') return q.type === '題組子題';
      if (filter === 'noncalc') return q.type === '非選擇題';
      return true;
    });
    this.currentIdx = 0;
    this.buildQnav();
  },

  // ── question nav drawer ───────────────────────
  buildQnav() {
    const grid = document.getElementById('qnav-grid');
    grid.innerHTML = '';
    this.filtered.forEach((q, i) => {
      const b = document.createElement('button');
      b.className = 'qnav-num' + (q.type === '非選擇題' ? ' qnav-noncalc' : '');
      b.textContent = q.type === '非選擇題' ? `非選${q.number}` : q.number;
      if (i === this.currentIdx) b.classList.add('active');
      b.addEventListener('click', () => {
        this.currentIdx = i;
        this.render();
        this.closeQnav();
      });
      grid.appendChild(b);
    });
  },

  openQnav() {
    document.getElementById('qnav').classList.add('open');
    document.getElementById('qnav-backdrop').hidden = false;
  },
  closeQnav() {
    document.getElementById('qnav').classList.remove('open');
    document.getElementById('qnav-backdrop').hidden = true;
  },

  // ── viewer events ─────────────────────────────
  bindViewer() {
    document.getElementById('year-select').addEventListener('change', async (e) => {
      await this.switchYear(e.target.value);
    });
    document.getElementById('filter-select').addEventListener('change', () => {
      this.applyFilter();
      this.render();
    });
    document.getElementById('qnav-toggle-btn').addEventListener('click', () => this.openQnav());
    document.getElementById('qnav-close-btn').addEventListener('click', () => this.closeQnav());
    document.getElementById('qnav-backdrop').addEventListener('click', () => this.closeQnav());

    document.getElementById('prev-btn').addEventListener('click', () => this.move(-1));
    document.getElementById('next-btn').addEventListener('click', () => this.move(1));

    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') this.move(-1);
      if (e.key === 'ArrowRight') this.move(1);
      if (e.key === 'Escape') this.closeQnav();
    });

    // lightbox
    document.getElementById('lightbox').addEventListener('click', () => {
      document.getElementById('lightbox').hidden = true;
    });
  },

  move(delta) {
    const next = this.currentIdx + delta;
    if (next < 0 || next >= this.filtered.length) return;
    this.currentIdx = next;
    this.render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  // ── rendering ─────────────────────────────────
  render() {
    const root = document.getElementById('quiz');
    const q = this.filtered[this.currentIdx];
    if (!q) {
      root.innerHTML = '<div class="q-card">此分類沒有題目。</div>';
      document.getElementById('q-counter').textContent = '0 / 0';
      return;
    }

    const total = this.filtered.length;
    document.getElementById('q-counter').textContent = `${this.currentIdx + 1} / ${total}`;
    document.getElementById('prev-btn').disabled = this.currentIdx === 0;
    document.getElementById('next-btn').disabled = this.currentIdx === total - 1;

    // update nav highlight
    document.querySelectorAll('.qnav-num').forEach((el, i) => {
      el.classList.toggle('active', i === this.currentIdx);
    });

    root.innerHTML = this.buildQuestionHtml(q);
    this.renderMath(root);
    this.bindFigures(root);
  },

  buildQuestionHtml(q) {
    const isNoncalc = q.type === '非選擇題';
    const badgeClass = q.type === '題組子題' ? 'badge-group' : (isNoncalc ? 'badge-noncalc' : '');
    const numLabel = isNoncalc ? `非選擇題 ${q.number}` : `第 ${q.number} 題`;

    let html = `<div class="q-card">`;

    // header
    html += `<div class="q-header">
      <span class="q-number">${numLabel}</span>
      <span class="q-type-badge ${badgeClass}">${q.type}</span>
      ${q.group_id ? `<span class="q-group-tag">題組 ${q.group_id}</span>` : ''}
    </div>`;

    // passage (group questions)
    if (q.passage) {
      const passageText = q.passage_latex || q.passage;
      html += `<div class="passage-box">
        <div class="passage-label">閱讀選文（第 ${q.group_range[0]}～${q.group_range[1]} 題共用）</div>
        <div class="passage-text">${this.markBold(this.esc(passageText))}</div>`;
      html += this.buildFiguresHtml(q.passage_figures || []);
      html += `</div>`;
    }

    // stem
    const stemText = q.stem_latex || q.stem;
    html += `<div class="q-stem">${this.esc(stemText)}</div>`;

    // sub-questions (非選擇題 only)
    if (q.sub_questions && q.sub_questions.length > 0) {
      html += `<div class="q-sub-questions">`;
      const subTexts = q.sub_questions_latex || q.sub_questions;
      for (let i = 0; i < subTexts.length; i++) {
        const sq = subTexts[i];
        if (!sq) continue;
        html += `<div class="q-sub-question">
          <span class="q-sub-q-marker">❓</span>
          <span class="q-sub-q-text">${this.markBold(this.esc(sq))}</span>
        </div>`;
      }
      html += `</div>`;
    }

    // question figures
    html += this.buildFiguresHtml(q.figures || []);
    html += this.buildFiguresHtml(q.tables || []);

    // options (choice questions only)
    if (q.options) {
      html += `<div class="q-options">`;
      for (const letter of ['A', 'B', 'C', 'D']) {
        const raw = (q.options_latex && q.options_latex[letter]) || q.options[letter];
        if (raw === undefined || raw === null || raw === '') continue;
        html += `<div class="q-option">
          <span class="q-option-label">${letter}</span>
          <span class="q-option-text">${this.esc(raw)}</span>
        </div>`;
      }
      html += `</div>`;
    }

    // answer / explanation placeholder (reserved for future)
    html += `<div class="answer-placeholder">
      <div class="answer-placeholder-title">答案與解析</div>
      <div class="answer-placeholder-sub">（預留區塊，日後擴充顯示參考答案與詳解）</div>
    </div>`;

    html += `</div>`;
    return html;
  },

  buildFiguresHtml(figIds) {
    if (!figIds || figIds.length === 0) return '';
    let html = `<div class="q-figures">`;
    for (const fid of figIds) {
      const src = figFile(fid, this.year);
      if (!src) continue;
      html += `<figure class="q-figure">
        <img src="${src}" alt="${fid}" data-fig="${fid}">
        <figcaption class="q-figure-caption">${fid}</figcaption>
      </figure>`;
    }
    html += `</div>`;
    return html;
  },

  bindFigures(root) {
    root.querySelectorAll('.q-figure img').forEach(img => {
      img.addEventListener('click', () => {
        const lb = document.getElementById('lightbox');
        document.getElementById('lightbox-img').src = img.src;
        lb.hidden = false;
      });
      img.addEventListener('error', () => {
        img.closest('.q-figure').style.display = 'none';
      });
    });
  },

  renderMath(root) {
    if (typeof renderMathInElement !== 'function') return;
    renderMathInElement(root, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '$', right: '$', display: false },
      ],
      throwOnError: false,
    });
  },

  esc(s) {
    if (s === null || s === undefined) return '';
    // Escape HTML but keep $ delimiters for KaTeX
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  },

  markBold(s) {
    // Convert **text** to <strong>text</strong> for bold rendering
    if (s === null || s === undefined) return '';
    return String(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
