// sampler.js - Dynamic question sampling and scoring
window.QuizSampler = {
  sample(pool, options = {}) {
    const targetCount = options.count || 25;
    const selectedSubjects = options.subjects || ['歷史', '地理', '公民'];
    const selectedTopics = options.topics || []; // Array of learning focuses

    // 1. Filter pool by subjects and topics
    let matchingQuestions = pool.filter(q => {
      // Must match selected subjects
      if (!selectedSubjects.includes(q.subject)) return false;
      // If specific topics are selected, must match at least one
      if (selectedTopics.length > 0) {
        if (!q.learning_focuses) return false;
        return q.learning_focuses.some(f => selectedTopics.includes(f));
      }
      return true;
    });

    // 2. Identify singles and groups in the matching pool
    const matchingSingles = matchingQuestions.filter(q => q.type === '單題');
    
    // Find groups that have at least one sub-question in matchingQuestions
    const matchingGroupKeys = new Set();
    matchingQuestions.forEach(q => {
      if (q.type === '題組子題' && q.group_id) {
        matchingGroupKeys.add(`${q.year}_${q.group_id}`);
      }
    });
    const eligibleGroupKeys = Array.from(matchingGroupKeys);

    // 3. Fallback check: if there are not enough matching questions to make 25, backfill
    // We backfill from:
    //   a. Selected subjects (ignoring topic filter)
    //   b. Entire pool (ignoring subject filter)
    if (matchingQuestions.length < targetCount) {
      console.warn("Not enough matching questions for criteria. Backfilling...");
      
      // Backfill from selected subjects (ignoring topics)
      const subOnlyPool = pool.filter(q => selectedSubjects.includes(q.subject) && !matchingQuestions.some(mq => mq.number === q.number && mq.year === q.year));
      const needed1 = targetCount - matchingQuestions.length;
      const fill1 = this.shuffleArray(subOnlyPool).slice(0, needed1);
      matchingQuestions.push(...fill1);

      // If still not enough, backfill from entire pool
      if (matchingQuestions.length < targetCount) {
        const remainingPool = pool.filter(q => !matchingQuestions.some(mq => mq.number === q.number && mq.year === q.year));
        const needed2 = targetCount - matchingQuestions.length;
        const fill2 = this.shuffleArray(remainingPool).slice(0, needed2);
        matchingQuestions.push(...fill2);
      }

      // Re-calculate singles and groups after backfilling
      matchingSingles.length = 0;
      matchingGroupKeys.clear();
      matchingQuestions.forEach(q => {
        if (q.type === '單題') {
          matchingSingles.push(q);
        } else if (q.type === '題組子題' && q.group_id) {
          matchingGroupKeys.add(`${q.year}_${q.group_id}`);
        }
      });
      eligibleGroupKeys.push(...Array.from(matchingGroupKeys).filter(k => !eligibleGroupKeys.includes(k)));
    }

    // 4. Sample at least one group if available
    let finalQuestions = [];
    let selectedGroupKeys = [];

    if (eligibleGroupKeys.length > 0) {
      // Pick 1 group randomly
      const randomGroupKey = eligibleGroupKeys[Math.floor(Math.random() * eligibleGroupKeys.length)];
      selectedGroupKeys.push(randomGroupKey);
      
      // Optionally pick a 2nd group if we have many eligible groups and 50% chance
      if (eligibleGroupKeys.length > 1 && Math.random() > 0.5) {
        const otherGroups = eligibleGroupKeys.filter(k => k !== randomGroupKey);
        selectedGroupKeys.push(otherGroups[Math.floor(Math.random() * otherGroups.length)]);
      }
    }

    // Get all sub-questions of selected groups
    let groupSubQuestions = [];
    selectedGroupKeys.forEach(key => {
      const gqs = window.QuizBank.groups[key] || [];
      // Sort to make sure they are in order (e.g. 44, 45)
      groupSubQuestions.push([...gqs].sort((a, b) => a.number - b.number));
    });

    // Total sub-questions in groups
    const totalGroupQs = groupSubQuestions.reduce((sum, g) => sum + g.length, 0);
    
    // We need targetCount - totalGroupQs singles
    const neededSinglesCount = Math.max(0, targetCount - totalGroupQs);
    
    // Select singles (excluding any that are in the selected groups just in case)
    const groupQIds = new Set();
    groupSubQuestions.flat().forEach(q => groupQIds.add(`${q.year}_${q.number}`));
    
    const availableSingles = matchingSingles.filter(q => !groupQIds.has(`${q.year}_${q.number}`));
    
    // Shuffle and pick
    const shuffledSingles = this.shuffleArray(availableSingles);
    const selectedSingles = shuffledSingles.slice(0, neededSinglesCount);

    // If still not enough singles, we can draw from other singles in the whole bank
    if (selectedSingles.length < neededSinglesCount) {
      const restSingles = window.QuizBank.singles.filter(q => 
        !groupQIds.has(`${q.year}_${q.number}`) && 
        !selectedSingles.some(sq => sq.year === q.year && sq.number === q.number)
      );
      const moreSingles = this.shuffleArray(restSingles).slice(0, neededSinglesCount - selectedSingles.length);
      selectedSingles.push(...moreSingles);
    }

    // 5. Shuffle the entities (singles and group blocks) together so groups stay intact
    const entities = [
      ...selectedSingles.map(q => ({ type: 'single', data: q })),
      ...groupSubQuestions.map(g => ({ type: 'group', data: g }))
    ];
    
    const shuffledEntities = this.shuffleArray(entities);
    
    // Flatten entities into a final question list
    shuffledEntities.forEach(ent => {
      if (ent.type === 'single') {
        finalQuestions.push(ent.data);
      } else {
        finalQuestions.push(...ent.data);
      }
    });

    // Make sure we have exactly targetCount (e.g. if group sizes caused slight overflow/underflow)
    if (finalQuestions.length > targetCount) {
      finalQuestions = finalQuestions.slice(0, targetCount);
    }

    // 6. Assign dynamic scores (Summing to 100)
    const baseScore = Math.floor(100 / finalQuestions.length);
    const remainder = 100 - (baseScore * finalQuestions.length);
    
    const questionsWithScores = finalQuestions.map((q, idx) => {
      // Clone the question to avoid mutating the master bank
      const qClone = JSON.parse(JSON.stringify(q));
      qClone.score = idx < remainder ? baseScore + 1 : baseScore;
      // Add a virtual test number (1 to 25)
      qClone.testNumber = idx + 1;
      return qClone;
    });

    return questionsWithScores;
  },

  shuffleArray(arr) {
    const copy = [...arr];
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }
};
