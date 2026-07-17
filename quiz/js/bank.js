// bank.js - Load and index question pool
window.QuizBank = {
  pool: [],
  subjects: { '歷史': [], '地理': [], '公民': [] },
  focuses: {}, // '主題名稱': [questions]
  singles: [],
  groups: {},  // 'year_groupId': [questions]
  isLoaded: false,

  async init() {
    if (this.isLoaded) return;

    const years = ['111', '112', '113', '114', '115'];
    const loadPromises = years.map(async (year) => {
      try {
        const response = await fetch(`../data/${year}.json`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const qs = await response.json();
        
        // Load figures metadata if available
        let figMap = {};
        try {
          const fres = await fetch(`../data/${year}_figures.json`);
          if (fres.ok) figMap = await fres.json();
        } catch (_) {}

        qs.forEach(q => {
          q.year = year;
          q.figMap = figMap; // Attach figures mapping metadata
          this.pool.push(q);
        });
      } catch (err) {
        console.error(`Failed to load data for year ${year}:`, err);
      }
    });

    await Promise.all(loadPromises);

    // Build indices
    this.pool.forEach(q => {
      // 1. Subject index
      const sub = q.subject;
      if (this.subjects[sub]) {
        this.subjects[sub].push(q);
      }

      // 2. Learning Focuses (Topics) index
      if (q.learning_focuses && Array.isArray(q.learning_focuses)) {
        q.learning_focuses.forEach(focus => {
          if (!this.focuses[focus]) this.focuses[focus] = [];
          this.focuses[focus].push(q);
        });
      }

      // 3. Singles vs Groups
      if (q.type === '單題') {
        this.singles.push(q);
      } else if (q.type === '題組子題' && q.group_id) {
        const key = `${q.year}_${q.group_id}`;
        if (!this.groups[key]) this.groups[key] = [];
        this.groups[key].push(q);
      }
    });

    this.isLoaded = true;
    console.log(`Loaded ${this.pool.length} questions in total.`);
    console.log(`Singles: ${this.singles.length}, Groups: ${Object.keys(this.groups).length} groups.`);
  },

  getAllFocuses() {
    return Object.keys(this.focuses).sort();
  },

  getFocusesBySubject(subj) {
    return this.getAllFocuses().filter(f => f.startsWith(subj.substring(0, 1)));
  }
};
