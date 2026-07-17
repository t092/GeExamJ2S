// JHexam Quiz App — vanilla JS
const CN_DIGIT = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'\u3127':1};

function renderStem(text) {
  if (!text || !text.includes('__')) return text;
  return text.replace(/__(.+?)__/g, '<u class="q-double">$1</u>');
}

function figNum(figId) {
  // Extract number from 圖(一) → 1, 圖(十) → 10, 表(二) → 2
  const m = figId.match(/[圖表]\((.+)\)/);
  if (!m) return null;
  const cn = m[1];
  if (cn === '十') return 10;
  if (cn.startsWith('十')) return 10 + (CN_DIGIT[cn[1]] || 0);
  if (cn.endsWith('十')) return (CN_DIGIT[cn[0]] || 1) * 10;
  if (cn.includes('十')) {
    const [a, b] = cn.split('十');
    return (CN_DIGIT[a] || 0) * 10 + (CN_DIGIT[b] || 0);
  }
  return CN_DIGIT[cn] || parseInt(cn) || null;
}

const App = {
  questions: [],
  figMap: {},
  filtered: [],
  currentIdx: 0,
  selectedAnswers: {},
  year: '114',
  cacheBust: Date.now(),
  shouldGoNextOnClose: false,

  getBustedSrc(src) {
    if (!src) return src;
    return `${src}?t=${this.cacheBust}`;
  },

  async init() {
    const yearSelect = document.getElementById('year-select');
    if (yearSelect) {
      this.year = yearSelect.value;
    }
    await this.loadYear(this.year);
    this.bindEvents();
    this.render();
  },

  async loadYear(year) {
    this.year = year;
    document.getElementById('year-badge').textContent = `${year}年`;
    try {
      const qres = await fetch(this.getBustedSrc(`../data/${year}.json`));
      if (!qres.ok) throw new Error(`HTTP ${qres.status} — 找不到 data/${year}.json`);
      this.questions = await qres.json();
    } catch (e) {
      this.questions = [];
      this.showError(`無法載入題庫：${e.message}<br><br>
        請確認：<br>
        1. 從專案根目錄啟動 server：<code>cd C:\\Users\\grifo\\OneDrive\\AI\\VibeVoding\\JHexam; python -m http.server 8000</code><br>
        2. 瀏覽器開 <code>http://localhost:8000/web/index.html</code><br>
        3. 不要用 file:// 直接開 HTML（fetch 會被 CORS 擋）`);
      return;
    }
    try {
      const fres = await fetch(this.getBustedSrc(`../data/${year}_figures.json`));
      this.figMap = await fres.json();
    } catch (e) {
      this.figMap = {};
    }
    this.currentIdx = 0;
    this.selectedAnswers = {};
    this.applyFilter();
  },

  showError(msg) {
    const root = document.getElementById('quiz');
    root.innerHTML = `<div style="padding:24px;background:#fdedec;border-radius:8px;color:#c0392b;">
      <strong>⚠ 載入失敗</strong><br><br>${msg}</div>`;
    document.getElementById('qnav').innerHTML = '';
    document.getElementById('q-counter').textContent = '0 / 0';
  },

  applyFilter() {
    const filter = document.getElementById('filter-select').value;
    this.filtered = this.questions.filter(q => {
      if (filter === 'single') return q.type === '單題';
      if (filter === 'group') return q.type === '題組子題';
      if (filter === 'history') return q.subject === '歷史';
      if (filter === 'geography') return q.subject === '地理';
      if (filter === 'citizenship') return q.subject === '公民';
      return true;
    });
    if (this.currentIdx >= this.filtered.length) this.currentIdx = 0;
  },

  bindEvents() {
    document.getElementById('year-select').addEventListener('change', async (e) => {
      await this.loadYear(e.target.value);
      this.render();
    });
    document.getElementById('filter-select').addEventListener('change', () => {
      this.applyFilter();
      this.currentIdx = 0;
      this.render();
    });
    document.getElementById('prev-btn').addEventListener('click', () => this.go(-1));
    document.getElementById('next-btn').addEventListener('click', () => this.go(1));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') this.go(-1);
      if (e.key === 'ArrowRight') this.go(1);
    });
    document.getElementById('lightbox').addEventListener('click', () => {
      document.getElementById('lightbox').hidden = true;
    });
    const modalClose = document.getElementById('modal-close-btn');
    if (modalClose) {
      modalClose.addEventListener('click', () => {
        document.getElementById('result-modal').hidden = true;
        if (this.shouldGoNextOnClose) {
          this.go(1);
          this.shouldGoNextOnClose = false;
        }
      });
    }
    const resultModal = document.getElementById('result-modal');
    if (resultModal) {
      resultModal.addEventListener('click', (e) => {
        if (e.target === resultModal) {
          resultModal.hidden = true;
          if (this.shouldGoNextOnClose) {
            this.go(1);
            this.shouldGoNextOnClose = false;
          }
        }
      });
    }
  },

  go(delta) {
    const newIdx = this.currentIdx + delta;
    if (newIdx < 0 || newIdx >= this.filtered.length) return;
    this.currentIdx = newIdx;
    this.shouldGoNextOnClose = false;
    this.render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  render() {
    this.renderNav();
    this.renderQuestion();
    this.renderControls();
  },

  buildHeader(q) {
    const header = document.createElement('div');
    header.className = 'q-header';

    const left = document.createElement('div');
    left.className = 'q-header-left';

    const num = document.createElement('div');
    num.className = 'q-number';
    num.textContent = q.number;
    left.appendChild(num);

    const type = document.createElement('span');
    type.className = 'q-type' + (q.type === '題組子題' ? ' group' : '');
    type.textContent = q.type;
    left.appendChild(type);

    if (q.group_range) {
      const range = document.createElement('span');
      range.className = 'q-group-range';
      range.textContent = q.type === '題組子題' 
        ? `第 ${q.group_range[0]}–${q.group_range[1]} 題`
        : `題組第 ${q.group_range[0]}–${q.group_range[1]} 題`;
      left.appendChild(range);
    }
    header.appendChild(left);

    // Toolbar
    const toolbar = document.createElement('div');
    toolbar.className = 'q-header-toolbar';

    // Prev Button
    const prevBtn = document.createElement('button');
    prevBtn.className = 'q-toolbar-btn';
    prevBtn.innerHTML = '&#x2190;'; // Left Arrow
    prevBtn.title = '上一題';
    prevBtn.disabled = this.currentIdx === 0;
    prevBtn.addEventListener('click', () => this.go(-1));
    toolbar.appendChild(prevBtn);

    // Counter
    const counter = document.createElement('span');
    counter.className = 'q-toolbar-counter';
    counter.textContent = `${this.currentIdx + 1} / ${this.filtered.length}`;
    toolbar.appendChild(counter);

    // Next Button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'q-toolbar-btn';
    nextBtn.innerHTML = '&#x2192;'; // Right Arrow
    nextBtn.title = '下一題';
    nextBtn.disabled = this.currentIdx === this.filtered.length - 1;
    nextBtn.addEventListener('click', () => this.go(1));
    toolbar.appendChild(nextBtn);

    // Divider
    const divider = document.createElement('div');
    divider.style.width = '1px';
    divider.style.height = '20px';
    divider.style.background = '#e1e8ed';
    divider.style.margin = '0 8px';
    toolbar.appendChild(divider);

    // ABCD Options
    const optContainer = document.createElement('div');
    optContainer.className = 'q-toolbar-options';
    const saved = this.selectedAnswers[q.number];
    ['A', 'B', 'C', 'D'].forEach(letter => {
      const btn = document.createElement('button');
      btn.className = 'q-toolbar-opt-btn';
      if (saved === letter) btn.classList.add('selected');
      btn.textContent = letter;
      btn.dataset.letter = letter;
      btn.addEventListener('click', () => this.selectAnswerFromToolbar(q.number, letter));
      optContainer.appendChild(btn);
    });
    toolbar.appendChild(optContainer);

    // Submit button
    const submitBtn = document.createElement('button');
    submitBtn.className = 'q-toolbar-submit-btn';
    submitBtn.textContent = '送出答案';
    submitBtn.addEventListener('click', () => this.submitAnswer(q));
    toolbar.appendChild(submitBtn);

    header.appendChild(toolbar);
    return header;
  },

  selectAnswerFromToolbar(qnum, letter) {
    this.selectedAnswers[qnum] = letter;
    
    // Update toolbar
    const toolbar = document.querySelector('.q-header-toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('.q-toolbar-opt-btn').forEach(btn => {
        if (btn.dataset.letter === letter) {
          btn.classList.add('selected');
        } else {
          btn.classList.remove('selected');
        }
      });
    }
    
    // Update standard options
    document.querySelectorAll('.q-option').forEach(el => {
      if (el.dataset.letter === letter) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });

    // Update image options
    const imgopts = document.querySelector('.q-imgopts');
    if (imgopts) {
      imgopts.querySelectorAll('.q-imgopt-btn, .q-imgopt-text-d').forEach(e => {
        if (e.dataset.letter === letter) {
          e.classList.add('selected');
        } else {
          e.classList.remove('selected');
        }
      });
    }
  },

  submitAnswer(q) {
    const selected = this.selectedAnswers[q.number];
    if (!selected) {
      alert('請先選擇一個答案！');
      return;
    }
    
    const correctAns = q.answer;
    
    const modal = document.getElementById('result-modal');
    const header = document.getElementById('modal-header');
    const statusIcon = document.getElementById('modal-status-icon');
    const title = document.getElementById('modal-title');
    const answerInfo = document.getElementById('modal-answer-info');
    const explanation = document.getElementById('modal-explanation');
    
    if (!correctAns || correctAns.trim() === '') {
      this.shouldGoNextOnClose = false;
      header.className = 'modal-header warning';
      statusIcon.textContent = '⚠';
      title.textContent = '尚未建立答案與解析庫，請期待';
      answerInfo.textContent = `您的答案是 ${selected}，目前本題尚未建立標準答案。`;
      answerInfo.style.color = '#d68910';
      explanation.textContent = '答案與詳解內容正在整理中，敬請期待！';
    } else {
      const isCorrect = (selected === correctAns);
      if (isCorrect) {
        this.shouldGoNextOnClose = true;
        header.className = 'modal-header correct';
        statusIcon.textContent = '✓';
        title.textContent = '恭喜答對！';
        answerInfo.textContent = `您的答案是 ${selected}，正確答案是 ${correctAns}`;
        answerInfo.style.color = '#27ae60';
      } else {
        this.shouldGoNextOnClose = false;
        header.className = 'modal-header incorrect';
        statusIcon.textContent = '✗';
        title.textContent = '答案錯誤';
        answerInfo.textContent = `您的答案是 ${selected}，正確答案是 ${correctAns}`;
        answerInfo.style.color = '#c0392b';
      }
      explanation.textContent = q.explanation || '本題暫無解析說明。';
    }
    
    modal.hidden = false;
  },

  renderNav() {
    const nav = document.getElementById('qnav');
    nav.innerHTML = '';
    this.filtered.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.className = 'qnav-btn';
      if (idx === this.currentIdx) btn.classList.add('active');
      if ((q.figures && q.figures.length > 0) || (q.tables && q.tables.length > 0)) btn.classList.add('has-figure');
      if (q.type === '題組子題') btn.classList.add('is-group');
      btn.textContent = q.number;
      const hasVisual = (q.figures && q.figures.length) || (q.tables && q.tables.length);
      btn.title = `第 ${q.number} 題${hasVisual ? ' (含圖表)' : ''}`;
      btn.addEventListener('click', () => {
        this.currentIdx = idx;
        this.render();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      nav.appendChild(btn);
    });
  },

  renderQuestion() {
    const q = this.filtered[this.currentIdx];
    if (!q) {
      document.getElementById('quiz').innerHTML = '<p>無符合條件的題目</p>';
      return;
    }

    if (q.type === '題組子題' && q.group_id) {
      this.renderGroupQuestion(q);
      return;
    }

    // Image-option questions: all/triple options are images
    if (q.image_options) {
      this.renderImageOptionQuestion(q);
      return;
    }

    const root = document.getElementById('quiz');
    root.innerHTML = '';

    // Header
    root.appendChild(this.buildHeader(q));

    const hasFigures = q.figures && q.figures.length > 0;
    const hasTables = q.tables && q.tables.length > 0;
    const hasVisuals = hasFigures || hasTables;

    // Two-column layout for questions with figures
    if (hasVisuals) {
      const layout = document.createElement('div');
      layout.className = 'q-layout';

      const contentCol = document.createElement('div');
      contentCol.className = 'q-content';

      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      contentCol.appendChild(stem);

      const opts = document.createElement('div');
      opts.className = 'q-options';
      ['A', 'B', 'C', 'D'].forEach(letter => {
        if (!q.options[letter]) return;
        const opt = document.createElement('div');
        opt.className = 'q-option';
        opt.dataset.letter = letter;
        const letEl = document.createElement('div');
        letEl.className = 'q-option-letter';
        letEl.textContent = letter;
        const txt = document.createElement('div');
        txt.className = 'q-option-text';
        txt.textContent = q.options[letter];
        opt.appendChild(letEl);
        opt.appendChild(txt);
        opt.addEventListener('click', () => this.selectAnswer(q.number, letter, opt));
        opts.appendChild(opt);
      });
      contentCol.appendChild(opts);
      layout.appendChild(contentCol);

      const figCol = this.renderFiguresColumn(q);
      layout.appendChild(figCol);
      root.appendChild(layout);
    } else {
      // Single column for questions without figures
      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      root.appendChild(stem);

      const opts = document.createElement('div');
      opts.className = 'q-options';
      ['A', 'B', 'C', 'D'].forEach(letter => {
        if (!q.options[letter]) return;
        const opt = document.createElement('div');
        opt.className = 'q-option';
        opt.dataset.letter = letter;
        const letEl = document.createElement('div');
        letEl.className = 'q-option-letter';
        letEl.textContent = letter;
        const txt = document.createElement('div');
        txt.className = 'q-option-text';
        txt.textContent = q.options[letter];
        opt.appendChild(letEl);
        opt.appendChild(txt);
        opt.addEventListener('click', () => this.selectAnswer(q.number, letter, opt));
        opts.appendChild(opt);
      });
      root.appendChild(opts);
    }

    // Restore answer if already selected
    const saved = this.selectedAnswers[q.number];
    if (saved) {
      const optEl = root.querySelector(`.q-option[data-letter="${saved}"]`);
      if (optEl) optEl.classList.add('selected');
    }
  },

  renderGroupQuestion(q) {
    const groupQs = this.filtered.filter(
      item => item.group_id === q.group_id
    ).sort((a, b) => a.number - b.number);
    const groupPos = groupQs.findIndex(item => item.number === q.number);
    const groupSize = groupQs.length;
    const firstQ = groupQs[0];

    const root = document.getElementById('quiz');
    root.innerHTML = '';

    // Outer container (identifies the group for reuse detection)
    const container = document.createElement('div');
    container.className = 'q-group-layout';
    container.dataset.groupId = q.group_id;

    const hasPassageFigs = (firstQ.passage_figures && firstQ.passage_figures.length > 0) ||
                          (firstQ.passage_tables && firstQ.passage_tables.length > 0);
    const hasSubFigs = (q.figures && q.figures.length > 0) ||
                       (q.tables && q.tables.length > 0);
    const hasAnyFigs = hasPassageFigs || hasSubFigs;
    if (!hasAnyFigs) container.classList.add('no-group-fig');

    // ── passage section (collapsible) ──
    const passageDiv = document.createElement('div');
    passageDiv.className = 'q-group-passage';
    const passageHeader = document.createElement('div');
    passageHeader.className = 'q-group-passage-header';
    const passageTitle = document.createElement('h4');
    passageTitle.textContent = '閱讀選文';
    passageHeader.appendChild(passageTitle);
    const toggleBtn = document.createElement('span');
    toggleBtn.className = 'q-group-passage-toggle';
    toggleBtn.textContent = '收合';
    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.togglePassage(passageDiv);
    });
    passageHeader.appendChild(toggleBtn);
    passageHeader.addEventListener('click', () => this.togglePassage(passageDiv));
    passageDiv.appendChild(passageHeader);

    const passageBody = document.createElement('div');
    passageBody.className = 'q-group-passage-body';
    passageBody.textContent = firstQ.passage || '';
    passageDiv.appendChild(passageBody);

    const passageExcerpt = document.createElement('div');
    passageExcerpt.className = 'q-group-passage-excerpt';
    const excerptText = (firstQ.passage || '').slice(0, 80);
    passageExcerpt.textContent = excerptText + '…（展開全文）';
    passageDiv.appendChild(passageExcerpt);
    container.appendChild(passageDiv);

    // ── figures section ──
    if (hasAnyFigs) {
      const figsDiv = document.createElement('div');
      figsDiv.className = 'q-group-figures';

      // Passage figures (displayed for all sub-questions)
      if (firstQ.passage_figures) {
        firstQ.passage_figures.forEach(figId => {
          const page = firstQ.passage_figure_pages && firstQ.passage_figure_pages[figId];
          const figDiv = this.buildFigureBlock(figId, page);
          figsDiv.appendChild(figDiv);
        });
      }
      if (firstQ.passage_tables) {
        firstQ.passage_tables.forEach(figId => {
          const page = firstQ.passage_table_pages && firstQ.passage_table_pages[figId];
          const figDiv = this.buildFigureBlock(figId, page);
          figsDiv.appendChild(figDiv);
        });
      }
      // Current sub-question figures
      if (q.figures) {
        q.figures.forEach(figId => {
          const page = q.figure_pages && q.figure_pages[figId];
          const figDiv = this.buildFigureBlock(figId, page);
          figsDiv.appendChild(figDiv);
        });
      }
      if (q.tables) {
        q.tables.forEach(figId => {
          const page = q.table_pages && q.table_pages[figId];
          const figDiv = this.buildFigureBlock(figId, page);
          figsDiv.appendChild(figDiv);
        });
      }
      container.appendChild(figsDiv);
    }

    // ── stem section ──
    const stemDiv = document.createElement('div');
    stemDiv.className = 'q-group-stem';

    // Header within stem
    stemDiv.appendChild(this.buildHeader(q));

    const stem = document.createElement('div');
    stem.className = 'q-stem';
    stem.innerHTML = renderStem(q.stem);
    stemDiv.appendChild(stem);

    // Options
    const opts = document.createElement('div');
    if (q.image_options) {
      // Image-based options: show the cropped option image + letter buttons
      this.buildImageOptionsBlock(q, opts);
    } else {
      opts.className = 'q-options';
      ['A', 'B', 'C', 'D'].forEach(letter => {
        const optText = q.options[letter];
        if (optText === undefined) return;
        const opt = document.createElement('div');
      opt.className = 'q-option';
      opt.dataset.letter = letter;
      const letEl = document.createElement('div');
      letEl.className = 'q-option-letter';
      letEl.textContent = letter;
      const txt = document.createElement('div');
      txt.className = 'q-option-text';
      txt.textContent = optText;
      opt.appendChild(letEl);
      opt.appendChild(txt);
      opt.addEventListener('click', () => this.selectAnswer(q.number, letter, opt));
      opts.appendChild(opt);
      });
    }
    stemDiv.appendChild(opts);

    // Group-internal navigation
    const groupNav = document.createElement('div');
    groupNav.className = 'q-group-nav';
    const prevBtn = document.createElement('button');
    prevBtn.textContent = '← 上一題';
    prevBtn.disabled = groupPos === 0;
    prevBtn.addEventListener('click', () => this.goInGroup(-1));
    groupNav.appendChild(prevBtn);
    const posLabel = document.createElement('span');
    posLabel.className = 'q-group-pos';
    posLabel.textContent = `${groupPos + 1} / ${groupSize}`;
    groupNav.appendChild(posLabel);
    const nextBtn = document.createElement('button');
    nextBtn.textContent = '下一題 →';
    nextBtn.disabled = groupPos === groupSize - 1;
    nextBtn.addEventListener('click', () => this.goInGroup(1));
    groupNav.appendChild(nextBtn);
    stemDiv.appendChild(groupNav);

    container.appendChild(stemDiv);
    root.appendChild(container);

    // Restore answer if already selected
    const saved = this.selectedAnswers[q.number];
    if (saved) {
      const optEl = root.querySelector(`.q-option[data-letter="${saved}"]`);
      if (optEl) optEl.classList.add('selected');
    }
  },

  // ── Image-option question renderer (single questions) ──
  renderImageOptionQuestion(q) {
    const root = document.getElementById('quiz');
    root.innerHTML = '';

    // Header
    root.appendChild(this.buildHeader(q));

    const hasFigures = q.figures && q.figures.length > 0;
    const hasTables = q.tables && q.tables.length > 0;
    const hasVisuals = hasFigures || hasTables;

    if (hasVisuals) {
      const layout = document.createElement('div');
      layout.className = 'q-layout';

      const contentCol = document.createElement('div');
      contentCol.className = 'q-content';

      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      contentCol.appendChild(stem);

      const optsDiv = document.createElement('div');
      this.buildImageOptionsBlock(q, optsDiv);
      contentCol.appendChild(optsDiv);
      layout.appendChild(contentCol);

      const figCol = this.renderFiguresColumn(q);
      layout.appendChild(figCol);
      root.appendChild(layout);
    } else {
      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      root.appendChild(stem);

      // Option image
      const optsDiv = document.createElement('div');
      this.buildImageOptionsBlock(q, optsDiv);
      root.appendChild(optsDiv);
    }
  },

  // ── Shared: build the image-option block (image + letter buttons) ──
  buildImageOptionsBlock(q, container) {
    container.className = 'q-imgopts';

    const src = this.getBustedSrc('pic/item/' + q.image_options);
    const img = document.createElement('img');
    img.className = 'q-imgopts-img';
    img.src = src;
    img.alt = `第${q.number}題選項（圖片）`;
    img.addEventListener('click', () => this.openLightbox(src));
    container.appendChild(img);

    // Letter buttons
    const letters = document.createElement('div');
    letters.className = 'q-imgopts-letters';
    const hasOptions = ['A', 'B', 'C', 'D'];
    if (!q.image_options_full) {
      // Only A/B/C are images; D is regular text
      hasOptions.length = 3;
    }
    hasOptions.forEach(letter => {
      const btn = document.createElement('div');
      btn.className = 'q-imgopt-btn';
      btn.dataset.letter = letter;
      btn.textContent = letter;
      btn.addEventListener('click', () => this.selectImageAnswer(q.number, letter, btn, container));
      letters.appendChild(btn);
    });
    container.appendChild(letters);

    // If D is text-only (image_options_full=false), render D as regular text option
    if (!q.image_options_full && q.options['D']) {
      const dOpt = document.createElement('div');
      dOpt.className = 'q-imgopt-text-d';
      const letEl = document.createElement('div');
      letEl.className = 'q-option-letter';
      letEl.textContent = 'D';
      const txt = document.createElement('div');
      txt.className = 'q-option-text';
      txt.textContent = q.options['D'];
      dOpt.appendChild(letEl);
      dOpt.appendChild(txt);
      dOpt.dataset.letter = 'D';
      dOpt.addEventListener('click', () => this.selectImageAnswer(q.number, 'D', dOpt, container));
      container.appendChild(dOpt);
    }

    // Restore selection
    const saved = this.selectedAnswers[q.number];
    if (saved) {
      const btn = container.querySelector(`[data-letter="${saved}"]`);
      if (btn) btn.classList.add('selected');
    }
  },

  selectImageAnswer(qnum, letter, el, container) {
    this.selectedAnswers[qnum] = letter;
    container.querySelectorAll('.q-imgopt-btn, .q-imgopt-text-d').forEach(e => e.classList.remove('selected'));
    el.classList.add('selected');
    
    // Sync to toolbar
    const toolbar = document.querySelector('.q-header-toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('.q-toolbar-opt-btn').forEach(btn => {
        if (btn.dataset.letter === letter) {
          btn.classList.add('selected');
        } else {
          btn.classList.remove('selected');
        }
      });
    }
  },

  togglePassage(el) {
    el.classList.toggle('collapsed');
    const toggle = el.querySelector('.q-group-passage-toggle');
    toggle.textContent = el.classList.contains('collapsed') ? '展開' : '收合';
  },

  goInGroup(delta) {
    const q = this.filtered[this.currentIdx];
    if (!q || !q.group_id) return;
    const groupQs = this.filtered
      .filter(item => item.group_id === q.group_id)
      .sort((a, b) => a.number - b.number);
    const groupPos = groupQs.findIndex(item => item.number === q.number);
    const newPos = groupPos + delta;
    if (newPos < 0 || newPos >= groupQs.length) return;
    const newQ = groupQs[newPos];
    // Find index in filtered list
    const newIdx = this.filtered.findIndex(
      item => item.number === newQ.number && item.group_id === newQ.group_id
    );
    if (newIdx === -1) return;
    this.currentIdx = newIdx;
    this.render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  buildFigureBlock(figId, page) {
    const figDiv = document.createElement('div');
    figDiv.className = 'q-figure';
    const isTable = figId.startsWith('表');
    const n = figNum(figId);
    const prefix = isTable ? 't' : 'p';
    const cropSrc = `pic/${this.year}${prefix}${String(n).padStart(2, '0')}.jpg`;
    const pageSrc = page ? `../assets/${this.year}/pages/page_${String(page).padStart(2, '0')}.png` : null;
    const cropSrcBusted = this.getBustedSrc(cropSrc);
    const pageSrcBusted = this.getBustedSrc(pageSrc);

    if (cropSrc) {
      const label = document.createElement('div');
      label.className = 'q-figure-label';
      label.textContent = figId + ' — 點擊放大';
      figDiv.appendChild(label);
      const img = document.createElement('img');
      img.src = cropSrcBusted;
      img.alt = figId;
      img.addEventListener('click', () => this.openLightbox(cropSrcBusted));
      figDiv.appendChild(img);
    } else if (pageSrc) {
      const label = document.createElement('div');
      label.className = 'q-figure-label';
      label.textContent = figId + '（第 ' + page + ' 頁）— 點擊放大';
      figDiv.appendChild(label);
      const img = document.createElement('img');
      img.src = pageSrcBusted;
      img.alt = figId;
      img.addEventListener('click', () => this.openLightbox(pageSrcBusted));
      figDiv.appendChild(img);
    }
    return figDiv;
  },

  renderFiguresColumn(q) {
    const figsDiv = document.createElement('div');
    figsDiv.className = 'q-figures';
    const allVisuals = (q.figures || []).concat(q.tables || []);
    allVisuals.forEach(figId => {
      const page = q.figure_pages && q.figure_pages[figId];
      const figDiv = document.createElement('div');
      figDiv.className = 'q-figure';

      const isTable = figId.startsWith('表');
      const n = figNum(figId);
      const prefix = isTable ? 't' : 'p';
      const cropSrc = `pic/${this.year}${prefix}${String(n).padStart(2, '0')}.jpg`;
      const pageSrc = page ? `../assets/${this.year}/pages/page_${String(page).padStart(2, '0')}.png` : null;
      const cropSrcBusted = this.getBustedSrc(cropSrc);
      const pageSrcBusted = this.getBustedSrc(pageSrc);

      if (cropSrc) {
        const label = document.createElement('div');
        label.className = 'q-figure-label';
        label.textContent = `${figId} \u2014 \u9EDE\u64CA\u653E\u5927`;
        figDiv.appendChild(label);
        const img = document.createElement('img');
        img.src = cropSrcBusted;
        img.alt = figId;
        img.dataset.crop = cropSrcBusted;
        img.dataset.page = pageSrcBusted;
        img.addEventListener('click', () => this.openLightbox(cropSrcBusted));
        img.addEventListener('contextmenu', (e) => {
          e.preventDefault();
          this.openLightbox(pageSrcBusted || cropSrcBusted);
        });
        figDiv.appendChild(img);
        if (pageSrc) {
          const hint = document.createElement('div');
          hint.className = 'q-figure-label';
          hint.style.cssText = 'font-size:11px;color:#95a5a6;';
          hint.textContent = '\uD83D\uDDB1 \u53F3\u9375\u2192\u67E5\u770B\u539F\u59CB\u9801\u9762';
          figDiv.appendChild(hint);
        }
      } else if (pageSrc) {
        const label = document.createElement('div');
        label.className = 'q-figure-label';
        label.textContent = `${figId}\uFF08\u7B2C ${page} \u9801\uFF09\u2014 \u9EDE\u64CA\u653E\u5927`;
        figDiv.appendChild(label);
        const img = document.createElement('img');
        img.src = pageSrcBusted;
        img.alt = figId;
        img.addEventListener('click', () => this.openLightbox(pageSrcBusted));
        figDiv.appendChild(img);
      } else {
        const note = document.createElement('div');
        note.className = 'q-figure-label';
        note.textContent = `${figId}\uFF08\u9801\u9762\u5C0D\u61C9\u4E2D\u2026\uFF09`;
        figDiv.appendChild(note);
      }
      figsDiv.appendChild(figDiv);
    });
    return figsDiv;
  },

  selectAnswer(qnum, letter, optEl) {
    this.selectedAnswers[qnum] = letter;
    document.querySelectorAll('.q-option').forEach(el => el.classList.remove('selected'));
    optEl.classList.add('selected');
    
    // Sync to toolbar
    const toolbar = document.querySelector('.q-header-toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('.q-toolbar-opt-btn').forEach(btn => {
        if (btn.dataset.letter === letter) {
          btn.classList.add('selected');
        } else {
          btn.classList.remove('selected');
        }
      });
    }
  },

  renderControls() {
    const counter = document.getElementById('q-counter');
    counter.textContent = `${this.currentIdx + 1} / ${this.filtered.length}`;
    document.getElementById('prev-btn').disabled = this.currentIdx === 0;
    document.getElementById('next-btn').disabled = this.currentIdx === this.filtered.length - 1;
  },

  openLightbox(src) {
    const lb = document.getElementById('lightbox');
    document.getElementById('lightbox-img').src = src;
    lb.hidden = false;
  },
};

App.init();
