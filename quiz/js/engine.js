// engine.js - Test controller and rendering logic
const CN_DIGIT = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'\u3127':1};

function figNum(figId) {
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

// Convert __markup__ to double-underline + bold
function renderStem(text) {
  if (!text || !text.includes('__')) return text;
  return text.replace(/__(.+?)__/g, '<u class=\"q-double\">$1</u>');
}

window.QuizEngine = {
  questions: [],
  currentIdx: 0,
  userAnswers: {}, // testNumber -> letter
  isTimerMode: false,
  timeLeft: 90,
  timerInterval: null,

  async init() {
    // 1. Initialize bank
    await window.QuizBank.init();
    
    // 2. Setup stage listeners & UI
    this.setupUI();
    this.bindSetupEvents();
  },

  setupUI() {
    // Populate topics in setup stage
    const subjects = ['歷史', '地理', '公民'];
    subjects.forEach(subj => {
      const el = document.querySelector(`.subject-topics[data-subject="${subj}"] .topic-list`);
      if (!el) return;

      const focuses = window.QuizBank.getFocusesBySubject(subj);
      el.innerHTML = '';
      
      focuses.forEach((focus, idx) => {
        const item = document.createElement('label');
        item.className = 'topic-item';
        item.htmlFor = `topic-${subj}-${idx}`;

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.id = `topic-${subj}-${idx}`;
        input.value = focus;
        input.className = 'topic-checkbox';
        input.checked = true; // Checked by default!

        const span = document.createElement('span');
        span.textContent = focus;

        item.appendChild(input);
        item.appendChild(span);
        el.appendChild(item);
      });
    });
  },

  bindSetupEvents() {
    // Subject checkboxes collapse/toggle topics
    const subCheckboxes = {
      '歷史': document.getElementById('sub-history'),
      '地理': document.getElementById('sub-geography'),
      '公民': document.getElementById('sub-citizens')
    };

    Object.entries(subCheckboxes).forEach(([subj, cb]) => {
      const wrapper = document.querySelector(`.subject-topics[data-subject="${subj}"]`);
      
      // 1. Sync Subject -> Child Topics
      cb.addEventListener('change', () => {
        if (cb.checked) {
          wrapper.style.opacity = '1';
          wrapper.style.pointerEvents = 'auto';
          wrapper.querySelectorAll('.topic-checkbox').forEach(chk => chk.checked = true);
        } else {
          wrapper.style.opacity = '0.5';
          wrapper.style.pointerEvents = 'none';
          wrapper.querySelectorAll('.topic-checkbox').forEach(chk => chk.checked = false);
        }
      });

      // 2. Sync Child Topics -> Subject
      wrapper.querySelectorAll('.topic-checkbox').forEach(chk => {
        chk.addEventListener('change', () => {
          const totalChecked = wrapper.querySelectorAll('.topic-checkbox:checked').length;
          cb.checked = totalChecked > 0;
          wrapper.style.opacity = cb.checked ? '1' : '0.5';
          wrapper.style.pointerEvents = cb.checked ? 'auto' : 'none';
        });
      });
    });

    // Start Button
    document.getElementById('start-btn').addEventListener('click', () => this.startQuiz());
  },

  startQuiz() {
    // 1. Gather choices
    const subjects = [];
    if (document.getElementById('sub-history').checked) subjects.push('歷史');
    if (document.getElementById('sub-geography').checked) subjects.push('地理');
    if (document.getElementById('sub-citizens').checked) subjects.push('公民');

    if (subjects.length === 0) {
      alert('請至少選擇一個科目！');
      return;
    }

    const topics = [];
    document.querySelectorAll('.topic-checkbox:checked').forEach(cb => {
      topics.push(cb.value);
    });

    this.isTimerMode = document.getElementById('timer-on').checked;

    // 2. Draw questions
    this.questions = window.QuizSampler.sample(window.QuizBank.pool, { subjects, topics });

    // 3. Reset test state
    this.currentIdx = 0;
    this.userAnswers = {};
    
    // 4. Transition to Testing stage
    document.getElementById('setup-stage').classList.remove('active');
    document.getElementById('testing-stage').classList.add('active');

    // 5. Setup controls in testing stage
    this.bindTestEvents();
    this.renderQuestion();
  },

  bindTestEvents() {
    // Re-bind to prevent double bindings
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-quiz-btn');

    // Clear old listeners by cloning
    const newPrev = prevBtn.cloneNode(true);
    const newNext = nextBtn.cloneNode(true);
    const newSubmit = submitBtn.cloneNode(true);

    prevBtn.replaceWith(newPrev);
    nextBtn.replaceWith(newNext);
    submitBtn.replaceWith(newSubmit);

    newPrev.addEventListener('click', () => this.go(-1));
    newNext.addEventListener('click', () => this.go(1));
    newSubmit.addEventListener('click', () => this.confirmSubmit());

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
      if (document.getElementById('testing-stage').classList.contains('active')) {
        if (e.key === 'ArrowLeft') this.go(-1);
        if (e.key === 'ArrowRight') this.go(1);
      }
    });

    // Lightbox close listener
    document.getElementById('lightbox').addEventListener('click', () => {
      document.getElementById('lightbox').hidden = true;
    });
  },

  go(delta) {
    const nextIndex = this.currentIdx + delta;
    if (nextIndex >= 0 && nextIndex < this.questions.length) {
      this.currentIdx = nextIndex;
      this.renderQuestion();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  renderQuestion() {
    const q = this.questions[this.currentIdx];
    if (!q) return;

    // Update progress bar
    const progress = ((this.currentIdx) / this.questions.length) * 100;
    document.getElementById('progress-bar').style.width = `${progress}%`;

    // Render navigation list
    this.renderNav();

    // Render Timer
    this.handleTimer();

    const root = document.getElementById('quiz');
    root.innerHTML = '';

    // Create question header
    const header = this.buildHeader(q);
    root.appendChild(header);

    // Group Layout vs Single Layout
    if (q.type === '題組子題') {
      this.renderGroupLayout(q, root);
    } else if (q.image_options) {
      this.renderImageOptionLayout(q, root);
    } else {
      this.renderStandardLayout(q, root);
    }

    // Update bottom controls
    document.getElementById('q-counter').textContent = `${this.currentIdx + 1} / ${this.questions.length}`;
    document.getElementById('prev-btn').disabled = this.currentIdx === 0;
    document.getElementById('next-btn').disabled = this.currentIdx === this.questions.length - 1;
  },

  renderNav() {
    const nav = document.getElementById('qnav');
    nav.innerHTML = '';

    this.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.className = 'qnav-btn';
      if (idx === this.currentIdx) btn.classList.add('active');
      if (this.userAnswers[q.testNumber]) btn.classList.add('answered');
      if (q.type === '題組子題') btn.classList.add('is-group');
      
      btn.textContent = q.testNumber;
      btn.title = `第 ${q.testNumber} 題 (${q.subject})`;

      btn.addEventListener('click', () => {
        this.currentIdx = idx;
        this.renderQuestion();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });

      nav.appendChild(btn);
    });
  },

  handleTimer() {
    clearInterval(this.timerInterval);
    const timerBadge = document.getElementById('test-timer');

    if (!this.isTimerMode) {
      timerBadge.hidden = true;
      return;
    }

    timerBadge.hidden = false;
    this.timeLeft = 90;
    document.getElementById('timer-sec').textContent = this.timeLeft;

    this.timerInterval = setInterval(() => {
      this.timeLeft--;
      document.getElementById('timer-sec').textContent = this.timeLeft;

      if (this.timeLeft <= 0) {
        clearInterval(this.timerInterval);
        this.handleTimeOut();
      }
    }, 1000);
  },

  handleTimeOut() {
    // Save blank or current selection, then move next
    const q = this.questions[this.currentIdx];
    if (!this.userAnswers[q.testNumber]) {
      this.userAnswers[q.testNumber] = null; // Marked as skipped
    }

    if (this.currentIdx < this.questions.length - 1) {
      alert(`第 ${q.testNumber} 題時間到！已自動儲存並前往下一題。`);
      this.go(1);
    } else {
      alert(`最後一題作答時間到！請點擊「交卷」以結束測驗。`);
      this.renderQuestion(); // Re-render to show timeout state
    }
  },

  buildHeader(q) {
    const header = document.createElement('div');
    header.className = 'q-header';

    const left = document.createElement('div');
    left.className = 'q-header-left';

    const num = document.createElement('div');
    num.className = 'q-number';
    num.textContent = q.testNumber;
    left.appendChild(num);

    const type = document.createElement('span');
    type.className = 'q-type' + (q.type === '題組子題' ? ' group' : '');
    type.textContent = q.type === '題組子題' ? '題組子題' : '單題';
    left.appendChild(type);

    if (q.group_range) {
      const range = document.createElement('span');
      range.className = 'q-group-range';
      // In the quiz bank, they refer to the original ranges, which is fine
      range.textContent = `原卷第 ${q.group_range[0]}–${q.group_range[1]} 題`;
      left.appendChild(range);
    }
    header.appendChild(left);

    // Header Toolbar
    const toolbar = document.createElement('div');
    toolbar.className = 'q-header-toolbar';

    const prevBtn = document.createElement('button');
    prevBtn.className = 'q-toolbar-btn';
    prevBtn.innerHTML = '&#x2190;';
    prevBtn.disabled = this.currentIdx === 0;
    prevBtn.addEventListener('click', () => this.go(-1));
    toolbar.appendChild(prevBtn);

    const counter = document.createElement('span');
    counter.className = 'q-toolbar-counter';
    counter.textContent = `${this.currentIdx + 1} / ${this.questions.length}`;
    toolbar.appendChild(counter);

    const nextBtn = document.createElement('button');
    nextBtn.className = 'q-toolbar-btn';
    nextBtn.innerHTML = '&#x2192;';
    nextBtn.disabled = this.currentIdx === this.questions.length - 1;
    nextBtn.addEventListener('click', () => this.go(1));
    toolbar.appendChild(nextBtn);

    header.appendChild(toolbar);
    return header;
  },

  renderStandardLayout(q, container) {
    const hasVisuals = (q.figures && q.figures.length > 0) || (q.tables && q.tables.length > 0);

    if (hasVisuals) {
      const layout = document.createElement('div');
      layout.className = 'q-layout';

      const contentCol = document.createElement('div');
      contentCol.className = 'q-content';

      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      contentCol.appendChild(stem);

      const opts = this.buildStandardOptions(q);
      contentCol.appendChild(opts);
      layout.appendChild(contentCol);

      const figCol = this.buildFiguresColumn(q);
      layout.appendChild(figCol);
      container.appendChild(layout);
    } else {
      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      container.appendChild(stem);

      const opts = this.buildStandardOptions(q);
      container.appendChild(opts);
    }
  },

  renderImageOptionLayout(q, container) {
    const hasVisuals = (q.figures && q.figures.length > 0) || (q.tables && q.tables.length > 0);

    if (hasVisuals) {
      const layout = document.createElement('div');
      layout.className = 'q-layout';

      const contentCol = document.createElement('div');
      contentCol.className = 'q-content';

      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      contentCol.appendChild(stem);

      const opts = this.buildImageOptions(q);
      contentCol.appendChild(opts);
      layout.appendChild(contentCol);

      const figCol = this.buildFiguresColumn(q);
      layout.appendChild(figCol);
      container.appendChild(layout);
    } else {
      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.innerHTML = renderStem(q.stem);
      container.appendChild(stem);

      const opts = this.buildImageOptions(q);
      container.appendChild(opts);
    }
  },

  renderGroupLayout(q, container) {
    const layout = document.createElement('div');
    layout.className = 'q-group-layout';

    const hasPassageFigs = (q.passage_figures && q.passage_figures.length > 0) ||
                          (q.passage_tables && q.passage_tables.length > 0);
    const hasSubFigs = (q.figures && q.figures.length > 0) ||
                       (q.tables && q.tables.length > 0);
    const hasAnyFigs = hasPassageFigs || hasSubFigs;

    if (!hasAnyFigs) {
      layout.classList.add('no-group-fig');
    }

    // Passage box
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
    passageHeader.appendChild(toggleBtn);
    
    passageHeader.addEventListener('click', () => {
      passageDiv.classList.toggle('collapsed');
      toggleBtn.textContent = passageDiv.classList.contains('collapsed') ? '展開' : '收合';
    });
    passageDiv.appendChild(passageHeader);

    const passageBody = document.createElement('div');
    passageBody.className = 'q-group-passage-body';
    passageBody.textContent = q.passage || '';
    passageDiv.appendChild(passageBody);

    const passageExcerpt = document.createElement('div');
    passageExcerpt.className = 'q-group-passage-excerpt';
    passageExcerpt.textContent = (q.passage || '').slice(0, 80) + '…（展開全文）';
    passageDiv.appendChild(passageExcerpt);

    layout.appendChild(passageDiv);

    // Figures Column
    if (hasAnyFigs) {
      const figsDiv = document.createElement('div');
      figsDiv.className = 'q-group-figures';

      // Passage figures
      if (q.passage_figures) {
        q.passage_figures.forEach(figId => {
          const page = q.passage_figure_pages && q.passage_figure_pages[figId];
          figsDiv.appendChild(this.buildFigureBlock(q, figId, page));
        });
      }
      if (q.passage_tables) {
        q.passage_tables.forEach(figId => {
          const page = q.passage_table_pages && q.passage_table_pages[figId];
          figsDiv.appendChild(this.buildFigureBlock(q, figId, page));
        });
      }

      // Sub-question figures
      if (q.figures) {
        q.figures.forEach(figId => {
          const page = q.figure_pages && q.figure_pages[figId];
          figsDiv.appendChild(this.buildFigureBlock(q, figId, page));
        });
      }
      if (q.tables) {
        q.tables.forEach(figId => {
          const page = q.table_pages && q.table_pages[figId];
          figsDiv.appendChild(this.buildFigureBlock(q, figId, page));
        });
      }

      layout.appendChild(figsDiv);
    }

    // Stem and Options column
    const stemDiv = document.createElement('div');
    stemDiv.className = 'q-group-stem';

    const stem = document.createElement('div');
    stem.className = 'q-stem';
    stem.innerHTML = renderStem(q.stem);
    stemDiv.appendChild(stem);

    const opts = q.image_options ? this.buildImageOptions(q) : this.buildStandardOptions(q);
    stemDiv.appendChild(opts);

    layout.appendChild(stemDiv);
    container.appendChild(layout);
  },

  buildStandardOptions(q) {
    const opts = document.createElement('div');
    opts.className = 'q-options';

    ['A', 'B', 'C', 'D'].forEach(letter => {
      if (q.options[letter] === undefined) return;

      const opt = document.createElement('div');
      opt.className = 'q-option';
      opt.dataset.letter = letter;

      if (this.userAnswers[q.testNumber] === letter) {
        opt.classList.add('selected');
      }

      const letEl = document.createElement('div');
      letEl.className = 'q-option-letter';
      letEl.textContent = letter;

      const txt = document.createElement('div');
      txt.className = 'q-option-text';
      txt.textContent = q.options[letter];

      opt.appendChild(letEl);
      opt.appendChild(txt);

      opt.addEventListener('click', () => {
        this.selectAnswer(q.testNumber, letter);
        opts.querySelectorAll('.q-option').forEach(el => el.classList.remove('selected'));
        opt.classList.add('selected');
      });

      opts.appendChild(opt);
    });

    return opts;
  },

  buildImageOptions(q) {
    const container = document.createElement('div');
    container.className = 'q-imgopts';

    const src = `../web/pic/item/${q.image_options}`;
    const img = document.createElement('img');
    img.className = 'q-imgopts-img';
    img.src = src;
    img.alt = `第 ${q.testNumber} 題選項 (圖片)`;
    img.addEventListener('click', () => this.openLightbox(src));
    container.appendChild(img);

    const letters = document.createElement('div');
    letters.className = 'q-imgopts-letters';

    const optList = ['A', 'B', 'C'];
    if (q.image_options_full) optList.push('D');

    optList.forEach(letter => {
      const btn = document.createElement('div');
      btn.className = 'q-imgopt-btn';
      btn.dataset.letter = letter;
      btn.textContent = letter;

      if (this.userAnswers[q.testNumber] === letter) {
        btn.classList.add('selected');
      }

      btn.addEventListener('click', () => {
        this.selectAnswer(q.testNumber, letter);
        container.querySelectorAll('.q-imgopt-btn, .q-imgopt-text-d').forEach(el => el.classList.remove('selected'));
        btn.classList.add('selected');
      });

      letters.appendChild(btn);
    });
    container.appendChild(letters);

    // If D option is not image, it's text
    if (!q.image_options_full && q.options['D']) {
      const dOpt = document.createElement('div');
      dOpt.className = 'q-imgopt-text-d';
      dOpt.dataset.letter = 'D';

      if (this.userAnswers[q.testNumber] === 'D') {
        dOpt.classList.add('selected');
      }

      const letEl = document.createElement('div');
      letEl.className = 'q-option-letter';
      letEl.textContent = 'D';

      const txt = document.createElement('div');
      txt.className = 'q-option-text';
      txt.textContent = q.options['D'];

      dOpt.appendChild(letEl);
      dOpt.appendChild(txt);

      dOpt.addEventListener('click', () => {
        this.selectAnswer(q.testNumber, 'D');
        container.querySelectorAll('.q-imgopt-btn, .q-imgopt-text-d').forEach(el => el.classList.remove('selected'));
        dOpt.classList.add('selected');
      });

      container.appendChild(dOpt);
    }

    return container;
  },

  buildFiguresColumn(q) {
    const figsDiv = document.createElement('div');
    figsDiv.className = 'q-figures';

    const allVisuals = (q.figures || []).concat(q.tables || []);
    allVisuals.forEach(figId => {
      const page = q.figure_pages && q.figure_pages[figId];
      figsDiv.appendChild(this.buildFigureBlock(q, figId, page));
    });

    return figsDiv;
  },

  buildFigureBlock(q, figId, page) {
    const figDiv = document.createElement('div');
    figDiv.className = 'q-figure';

    const isTable = figId.startsWith('表');
    const n = figNum(figId);
    const prefix = isTable ? 't' : 'p';
    const cropSrc = `../web/pic/${q.year}${prefix}${String(n).padStart(2, '0')}.jpg`;
    const pageSrc = page ? `../assets/${q.year}/pages/page_${String(page).padStart(2, '0')}.png` : null;

    if (cropSrc) {
      const label = document.createElement('div');
      label.className = 'q-figure-label';
      label.textContent = `${figId} — 點擊放大`;
      figDiv.appendChild(label);

      const img = document.createElement('img');
      img.src = cropSrc;
      img.alt = figId;
      img.addEventListener('click', () => this.openLightbox(cropSrc));
      
      // Right click helper to view original page
      if (pageSrc) {
        img.addEventListener('contextmenu', (e) => {
          e.preventDefault();
          this.openLightbox(pageSrc);
        });
        const hint = document.createElement('div');
        hint.className = 'q-figure-label';
        hint.style.cssText = 'font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;';
        hint.textContent = '🖱️ 右鍵查看原始頁面';
        figDiv.appendChild(img);
        figDiv.appendChild(hint);
      } else {
        figDiv.appendChild(img);
      }
    } else if (pageSrc) {
      const label = document.createElement('div');
      label.className = 'q-figure-label';
      label.textContent = `${figId}（第 ${page} 頁）— 點擊放大`;
      figDiv.appendChild(label);

      const img = document.createElement('img');
      img.src = pageSrc;
      img.alt = figId;
      img.addEventListener('click', () => this.openLightbox(pageSrc));
      figDiv.appendChild(img);
    }

    return figDiv;
  },

  selectAnswer(testNumber, letter) {
    this.userAnswers[testNumber] = letter;
    // Highlight completed in nav list
    this.renderNav();
  },

  openLightbox(src) {
    const lb = document.getElementById('lightbox');
    document.getElementById('lightbox-img').src = src;
    lb.hidden = false;
  },

  confirmSubmit() {
    clearInterval(this.timerInterval);
    const totalQs = this.questions.length;
    const answeredCount = Object.keys(this.userAnswers).filter(k => this.userAnswers[k] !== null).length;
    const unansweredCount = totalQs - answeredCount;

    const modal = document.getElementById('confirm-modal');
    const textEl = document.getElementById('confirm-text');
    
    if (unansweredCount > 0) {
      textEl.textContent = `您還有 ${unansweredCount} 題尚未作答！確定現在要交卷嗎？`;
    } else {
      textEl.textContent = `您已完成所有題目作答。點擊「確定交卷」進行計分與檢討。`;
    }

    // Set actions
    document.getElementById('confirm-cancel-btn').onclick = () => {
      modal.hidden = true;
      if (this.isTimerMode) {
        // Resume timer
        this.timerInterval = setInterval(() => {
          this.timeLeft--;
          document.getElementById('timer-sec').textContent = this.timeLeft;
          if (this.timeLeft <= 0) {
            clearInterval(this.timerInterval);
            this.handleTimeOut();
          }
        }, 1000);
      }
    };

    document.getElementById('confirm-ok-btn').onclick = () => {
      modal.hidden = true;
      this.submitQuiz();
    };

    modal.hidden = false;
  },

  submitQuiz() {
    clearInterval(this.timerInterval);
    document.getElementById('testing-stage').classList.remove('active');
    document.getElementById('review-stage').classList.add('active');

    // Run review display
    window.QuizReview.init(this.questions, this.userAnswers);
  }
};

window.onload = () => {
  window.QuizEngine.init();
};
