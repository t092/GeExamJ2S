// review.js - Quiz score calculation and review list rendering
window.QuizReview = {
  questions: [],
  userAnswers: {},

  init(questions, userAnswers) {
    this.questions = questions;
    this.userAnswers = userAnswers;

    this.calculateScores();
    this.renderReviewList();
    this.bindEvents();
  },

  calculateScores() {
    let totalScore = 0;
    let correctCount = 0;
    const totalCount = this.questions.length;

    const subjects = {
      '歷史': { total: 0, correct: 0 },
      '地理': { total: 0, correct: 0 },
      '公民': { total: 0, correct: 0 }
    };

    this.questions.forEach(q => {
      const isCorrect = this.userAnswers[q.testNumber] === q.answer;
      const sub = q.subject;
      
      if (subjects[sub]) {
        subjects[sub].total++;
        if (isCorrect) subjects[sub].correct++;
      }

      if (isCorrect) {
        totalScore += q.score;
        correctCount++;
      }
    });

    // 1. Render score ring
    document.getElementById('score-value').textContent = totalScore;
    const ring = document.getElementById('score-ring-fill');
    // Circumference = 2 * PI * r = 2 * 3.14159 * 70 = 439.8 => approx 440
    const circumference = 440;
    const strokeDashoffset = circumference - (circumference * (totalScore / 100));
    ring.style.strokeDashoffset = strokeDashoffset;

    // 2. Render counter & percent
    document.getElementById('correct-count').textContent = `${correctCount} / ${totalCount}`;
    const percent = Math.round((correctCount / totalCount) * 100);
    document.getElementById('correct-percent').textContent = `${percent}%`;

    // 3. Render subject stats
    const list = ['history', 'geography', 'citizenship'];
    const map = { history: '歷史', geography: '地理', citizenship: '公民' };

    list.forEach(key => {
      const data = subjects[map[key]];
      const valEl = document.getElementById(`sub-val-${key}`);
      const fillEl = document.getElementById(`sub-fill-${key}`);

      valEl.textContent = `${data.correct} / ${data.total}`;
      const percentage = data.total > 0 ? (data.correct / data.total) * 100 : 0;
      fillEl.style.width = `${percentage}%`;
    });
  },

  renderReviewList() {
    const listContainer = document.getElementById('review-list');
    listContainer.innerHTML = '';

    this.questions.forEach(q => {
      const userAns = this.userAnswers[q.testNumber] || null;
      const isCorrect = userAns === q.answer;

      const card = document.createElement('div');
      card.className = `review-item-card ${isCorrect ? 'is-correct' : 'is-incorrect'}`;
      card.dataset.correct = isCorrect ? 'true' : 'false';

      // Badge
      const badge = document.createElement('span');
      badge.className = 'review-item-badge';
      if (isCorrect) {
        badge.textContent = `答對 +${q.score}分`;
      } else if (userAns === null) {
        badge.textContent = `未作答 0 / ${q.score}分`;
      } else {
        badge.textContent = `答錯 0 / ${q.score}分`;
      }
      card.appendChild(badge);

      // Header block
      const h3 = document.createElement('h3');
      h3.style.fontSize = '1.1rem';
      h3.style.marginBottom = '0.5rem';
      h3.textContent = `第 ${q.testNumber} 題 (${q.subject})`;
      card.appendChild(h3);

      // Group Question Passage Section inside card (collapsible)
      if (q.type === '題組子題' && q.passage) {
        const passBox = document.createElement('div');
        passBox.className = 'q-group-passage';
        passBox.style.maxHeight = '200px';
        passBox.style.margin = '0.75rem 0';
        
        const passHeader = document.createElement('div');
        passHeader.className = 'q-group-passage-header';
        const pTitle = document.createElement('h4');
        pTitle.textContent = '閱讀選文';
        passHeader.appendChild(pTitle);
        
        const pToggle = document.createElement('span');
        pToggle.className = 'q-group-passage-toggle';
        pToggle.textContent = '展開';
        passHeader.appendChild(pToggle);
        
        const pBody = document.createElement('div');
        pBody.className = 'q-group-passage-body';
        pBody.textContent = q.passage;
        pBody.style.display = 'none';

        const pExcerpt = document.createElement('div');
        pExcerpt.className = 'q-group-passage-excerpt';
        pExcerpt.textContent = q.passage.slice(0, 80) + '…（展開全文）';
        pExcerpt.style.display = 'block';

        passHeader.addEventListener('click', () => {
          const isCollapsed = pBody.style.display === 'none';
          pBody.style.display = isCollapsed ? 'block' : 'none';
          pExcerpt.style.display = isCollapsed ? 'none' : 'block';
          pToggle.textContent = isCollapsed ? '收合' : '展開';
        });

        passBox.appendChild(passHeader);
        passBox.appendChild(pBody);
        passBox.appendChild(pExcerpt);
        card.appendChild(passBox);
      }

      // Question figures/tables block
      const hasPassageFigs = (q.passage_figures && q.passage_figures.length > 0) ||
                            (q.passage_tables && q.passage_tables.length > 0);
      const hasSubFigs = (q.figures && q.figures.length > 0) ||
                         (q.tables && q.tables.length > 0);
      const hasAnyFigs = hasPassageFigs || hasSubFigs;

      if (hasAnyFigs) {
        const figsWrapper = document.createElement('div');
        figsWrapper.style.display = 'flex';
        figsWrapper.style.flexDirection = 'column';
        figsWrapper.style.gap = '0.75rem';
        figsWrapper.style.margin = '1rem 0';
        figsWrapper.style.maxWidth = '400px';

        const addFig = (figId, page, pageMap, tableMap) => {
          const isTable = figId.startsWith('表');
          const n = figNum(figId);
          const prefix = isTable ? 't' : 'p';
          const cropSrc = `../web/pic/${q.year}${prefix}${String(n).padStart(2, '0')}.jpg`;
          const pageNum = pageMap && pageMap[figId];
          const pageSrc = pageNum ? `../assets/${q.year}/pages/page_${String(pageNum).padStart(2, '0')}.png` : null;

          const figDiv = document.createElement('div');
          figDiv.className = 'q-figure';

          if (cropSrc) {
            const label = document.createElement('div');
            label.className = 'q-figure-label';
            label.textContent = `${figId} — 點擊放大`;
            figDiv.appendChild(label);

            const img = document.createElement('img');
            img.src = cropSrc;
            img.alt = figId;
            img.addEventListener('click', () => {
              document.getElementById('lightbox').hidden = false;
              document.getElementById('lightbox-img').src = cropSrc;
            });
            figDiv.appendChild(img);
          }
          figsWrapper.appendChild(figDiv);
        };

        if (q.passage_figures) q.passage_figures.forEach(f => addFig(f, q.passage_figure_pages, q.passage_figure_pages, q.passage_table_pages));
        if (q.passage_tables) q.passage_tables.forEach(f => addFig(f, q.passage_table_pages, q.passage_figure_pages, q.passage_table_pages));
        if (q.figures) q.figures.forEach(f => addFig(f, q.figure_pages, q.figure_pages, q.table_pages));
        if (q.tables) q.tables.forEach(f => addFig(f, q.table_pages, q.figure_pages, q.table_pages));

        card.appendChild(figsWrapper);
      }

      // Stem text
      const stem = document.createElement('div');
      stem.className = 'q-stem';
      stem.textContent = q.stem;
      card.appendChild(stem);

      // Options
      if (q.image_options) {
        // Image option review block
        const imgopts = document.createElement('div');
        imgopts.className = 'q-imgopts';

        const optImageSrc = `../web/pic/item/${q.image_options}`;
        const img = document.createElement('img');
        img.className = 'q-imgopts-img';
        img.src = optImageSrc;
        img.alt = `選項圖片`;
        img.addEventListener('click', () => {
          document.getElementById('lightbox').hidden = false;
          document.getElementById('lightbox-img').src = optImageSrc;
        });
        imgopts.appendChild(img);

        const letters = document.createElement('div');
        letters.className = 'q-imgopts-letters';

        const optList = ['A', 'B', 'C'];
        if (q.image_options_full) optList.push('D');

        optList.forEach(letter => {
          const btn = document.createElement('div');
          btn.className = 'q-imgopt-btn';
          btn.textContent = letter;

          if (letter === q.answer) btn.classList.add('is-correct-ans');
          if (letter === userAns) btn.classList.add('is-user-ans');

          letters.appendChild(btn);
        });
        imgopts.appendChild(letters);

        if (!q.image_options_full && q.options['D']) {
          const dOpt = document.createElement('div');
          dOpt.className = 'q-imgopt-text-d';
          
          if (q.answer === 'D') dOpt.classList.add('is-correct-ans');
          if (userAns === 'D') dOpt.classList.add('is-user-ans');

          const letEl = document.createElement('div');
          letEl.className = 'q-option-letter';
          letEl.textContent = 'D';

          const txt = document.createElement('div');
          txt.className = 'q-option-text';
          txt.textContent = q.options['D'];

          dOpt.appendChild(letEl);
          dOpt.appendChild(txt);
          imgopts.appendChild(dOpt);
        }

        card.appendChild(imgopts);
      } else {
        // Standard option review block
        const opts = document.createElement('div');
        opts.className = 'q-options';

        ['A', 'B', 'C', 'D'].forEach(letter => {
          if (q.options[letter] === undefined) return;

          const opt = document.createElement('div');
          opt.className = 'q-option';
          
          if (letter === q.answer) opt.classList.add('is-correct-ans');
          if (letter === userAns) opt.classList.add('is-user-ans');

          const letEl = document.createElement('div');
          letEl.className = 'q-option-letter';
          letEl.textContent = letter;

          const txt = document.createElement('div');
          txt.className = 'q-option-text';
          txt.textContent = q.options[letter];

          opt.appendChild(letEl);
          opt.appendChild(txt);
          opts.appendChild(opt);
        });

        card.appendChild(opts);
      }

      // Meta info (Year source, original q num)
      const meta = document.createElement('div');
      meta.className = 'review-item-meta';

      const yearPill = document.createElement('span');
      yearPill.className = 'meta-pill';
      yearPill.textContent = `${q.year} 學年度會考第 ${q.number} 題`;
      meta.appendChild(yearPill);

      const focusPill = document.createElement('span');
      focusPill.className = 'meta-pill';
      focusPill.textContent = `主題：${(q.learning_focuses && q.learning_focuses[0]) || '未標註'}`;
      meta.appendChild(focusPill);

      const scorePill = document.createElement('span');
      scorePill.className = 'meta-pill meta-score';
      scorePill.textContent = `配分：${q.score} 分`;
      meta.appendChild(scorePill);

      card.appendChild(meta);

      // Explanation Box
      const expl = document.createElement('div');
      expl.className = 'review-explanation-box';
      
      const title = document.createElement('div');
      title.className = 'explanation-title';
      title.innerHTML = '💡 題目解析與解題思維';
      expl.appendChild(title);

      const body = document.createElement('div');
      body.className = 'explanation-body';
      body.textContent = q.explanation || '本題暫無詳細解析說明。';
      expl.appendChild(body);

      card.appendChild(expl);

      listContainer.appendChild(card);
    });
  },

  bindEvents() {
    // 1. Restart Button
    document.getElementById('restart-btn').addEventListener('click', () => {
      document.getElementById('review-stage').classList.remove('active');
      document.getElementById('setup-stage').classList.add('active');
      
      // Reset checkboxes or expander states
      document.getElementById('sub-history').checked = true;
      document.getElementById('sub-geography').checked = true;
      document.getElementById('sub-citizens').checked = true;
      
      const subjectList = ['history', 'geography', 'citizens'];
      subjectList.forEach(y => {
        const wrapper = document.querySelector(`.subject-topics[data-subject="${y === 'citizens' ? '公民' : (y === 'history' ? '歷史' : '地理')}"]`);
        if (wrapper) {
          wrapper.style.opacity = '1';
          wrapper.style.pointerEvents = 'auto';
        }
      });
      document.querySelectorAll('.topic-checkbox').forEach(cb => cb.checked = true);
    });

    // 2. Filters
    const btnAll = document.getElementById('filter-all-questions');
    const btnWrong = document.getElementById('filter-wrong-questions');

    btnAll.onclick = () => {
      btnAll.classList.add('btn-active');
      btnWrong.classList.remove('btn-active');

      document.querySelectorAll('.review-item-card').forEach(card => {
        card.style.display = 'block';
      });
    };

    btnWrong.onclick = () => {
      btnWrong.classList.add('btn-active');
      btnAll.classList.remove('btn-active');

      document.querySelectorAll('.review-item-card').forEach(card => {
        if (card.dataset.correct === 'true') {
          card.style.display = 'none';
        } else {
          card.style.display = 'block';
        }
      });
    };
  }
};
