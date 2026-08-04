export const WRITE_POLISH = [
// ═══════════════════════════════════════════════════════════
    // Template 3: Book Production (stub — chapters generated dynamically)
    // ═══════════════════════════════════════════════════════════
    {
        type: 'book-production',
        label: 'Book Production',
        description: 'Write chapters sequentially with full context injection — write, self-review, and compile',
        steps: [
            {
                label: 'Write Chapter {{chapterNumber}}',
                skill: 'write',
                taskType: 'general',
                promptTemplate: `Write Chapter {{chapterNumber}} of {{totalChapters}}.
                                Use only these story sources as canon:
                                - BOOK_PLAN.md (chapter beats and arc progression)
                                - SYNOPSIS.md (plot intent and pacing)
                                - CHARACTER_PROFILES.md (voice, motives, relationships)
                                - Previous chapter text (continuity anchor)

                                Requirements:
                                1. Execute this chapter's assigned beats from BOOK_PLAN.md.
                                2. Keep POV, tense, tone, and character voice consistent.
                                3. Preserve continuity with prior events, facts, and emotional state.
                                4. Advance plot and character arcs; end with momentum into next chapter.
                                5. Target about {{targetWordCount}} words (soft range +/-20%).

                                Output rules:
                                - Output chapter prose only.
                                - No notes, analysis, summaries, or instruction restatement.
                                - No markdown preface beyond the chapter heading.`,
            },
        ],
    },
    // ═══════════════════════════════════════════════════════════
    // Template 4: Deep Revision (21 steps, 3 passes)
    // ═══════════════════════════════════════════════════════════
    {
        type: 'deep-revision',
        label: 'Deep Revision',
        description: '21-step, 3-pass manuscript revision — macro (structural), medium (scene-level), micro (line-level) + beta reader panel',
        steps: [
            // ── Pass 1: Macro / Structural (7 steps) ──
            {
                label: 'Plot structure analysis',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Analyze the plot structure of this manuscript:

**Manuscript**: "{{title}}" — {{description}}

Evaluate:
1. **Three-act structure compliance**: Is there a clear setup, confrontation, and resolution?
2. **Inciting incident**: When does it occur? Is it strong enough? Too early/late?
3. **Midpoint shift**: Is there a genuine reversal or revelation at the midpoint?
4. **All-is-lost moment**: Does the 75% mark deliver real despair?
5. **Climax**: Is it earned? Does it resolve the central conflict?
6. **Resolution**: Is it satisfying without being too neat?
7. **Hero's journey beats**: Which archetypes are present? Which are missing?

Rate structural integrity: 1-10. Provide specific chapter references for every issue.`,
            },
            {
                label: 'Pacing audit',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Create a chapter-by-chapter pacing heatmap for:

**Manuscript**: "{{title}}" — {{description}}

For EACH chapter: Tension (1-10) | Pacing (Too Fast/Fast/Good/Slow/Draggy) | Scene types | Energy

Then analyze:
- Where are the energy valleys? Should chapters be cut or combined?
- Do climactic moments land with proper setup?
- Is the action-to-reflection ratio balanced?
- Are chapter lengths consistent? Do variations serve the story?
- Do the first 3 chapters build enough momentum?

End with top 3 pacing fixes, prioritized by impact.`,
            },
            {
                label: 'Character arc consistency',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Check character arc consistency across:

**Manuscript**: "{{title}}" — {{description}}

For each major character:
1. **Arc mapping**: Where they start → key turning points → where they end
2. **Growth evidence**: What specific scenes show change?
3. **Regression moments**: Are setbacks believable?
4. **Arc completion**: Does the ending deliver on the character's promise?
5. **Motivation consistency**: Do they ever act out of character for plot convenience?

Flag any character who doesn't change, changes too abruptly, or acts inconsistently.`,
            },
            {
                label: 'Theme coherence review',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Analyze thematic coherence in:

**Manuscript**: "{{title}}" — {{description}}

1. **Central theme identification**: What is this book really about beneath the plot?
2. **Theme in subplots**: Does each subplot reinforce or contrast the central theme?
3. **Thematic drift**: Are there sections where the theme gets lost?
4. **Theme in character arcs**: How does each character's journey explore the theme?
5. **Thematic resolution**: Does the ending make a clear statement about the theme?
6. **Heavy-handedness**: Are there moments where theme becomes preachy?`,
            },
            {
                label: 'World-building continuity scan',
                skill: 'revise',
                taskType: 'consistency',
                promptTemplate: `Run a world-building continuity scan on:

**Manuscript**: "{{title}}" — {{description}}

Check for:
1. **Setting contradictions**: Room layouts, geography, distances between locations
2. **Rule violations**: Magic/tech/social rules that get broken without explanation
3. **Timeline errors**: Days, dates, seasons, time-of-day inconsistencies
4. **Character knowledge**: Does anyone know something they shouldn't?
5. **Dead/missing characters**: Anyone disappears without explanation?
6. **Object tracking**: Important items that appear/disappear without logic

For each issue: where it appears, what the contradiction is, and how to fix it. Organized by severity.`,
            },
            {
                label: 'Stakes escalation verification',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Verify that stakes escalate properly in:

**Manuscript**: "{{title}}" — {{description}}

Analyze:
1. **Personal stakes**: What does the protagonist personally lose if they fail? Does this deepen?
2. **External stakes**: How do consequences widen over the story?
3. **Urgency**: Is there a ticking clock? Does time pressure increase?
4. **Cost of action**: Does pursuing the goal cost more as the story progresses?
5. **Point of no return**: When can the protagonist no longer walk away?
6. **Stakes at climax**: Are the final stakes the highest they've been?

Flag any moment where stakes plateau, decrease, or feel artificial.`,
            },
            {
                label: 'Subplot tracking & resolution',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Track all subplots in:

**Manuscript**: "{{title}}" — {{description}}

For each subplot found:
1. **Introduction**: When and how is it introduced?
2. **Purpose**: How does it serve the main plot or theme?
3. **Key beats**: Major developments (with chapter references)
4. **Resolution**: How and when is it resolved?
5. **Dropped threads**: Was anything set up but never paid off?

Also check:
- Are any subplots redundant? Do two accomplish the same thing?
- Are any subplots underdeveloped?
- Do subplots interfere with pacing?`,
            },
            // ── Pass 2: Medium / Scene-Level (7 steps) ──
            {
                label: 'Dialogue authenticity pass',
                skill: 'dialogue',
                taskType: 'revision',
                promptTemplate: `Perform a dialogue authenticity audit on:

**Manuscript**: "{{title}}" — {{description}}

1. **Voice distinctiveness**: Rate each major character's voice uniqueness (1-10). Can you tell them apart?
2. **Info-dumping**: Flag "As you know, Bob..." moments
3. **Subtext quality**: Best and worst examples of saying vs meaning
4. **Speech patterns**: Note unique patterns per character
5. **Tag vs action beat ratio**: Are they balanced?
6. **Emotional authenticity**: Do emotional conversations ring true?

Suggest rewrites for the 5 worst dialogue passages.`,
            },
            {
                label: 'Show-don\'t-tell audit',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Scan for show vs tell issues in:

**Manuscript**: "{{title}}" — {{description}}

Flag: emotional telling, character description telling, backstory dumps, motivation telling, atmosphere telling.

For the 10 worst offenders: quote the original → write a "showing" rewrite → explain why it's stronger.

Note: some telling is FINE. Only flag cases where showing would genuinely improve the experience.`,
            },
            {
                label: 'Scene tension & conflict check',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Check every scene for tension and conflict:

**Manuscript**: "{{title}}" — {{description}}

For each scene:
- **Goal**: What does the POV character want in this scene?
- **Obstacle**: What's preventing them from getting it?
- **Stakes**: What happens if they fail?
- **Outcome**: Do they succeed, fail, or get a complicated result?

Flag any scene where:
- The character has no goal
- There's no opposition
- Nothing changes by the end
- The tension is purely internal with no external manifestation

These are scenes that may need to be cut or strengthened.`,
            },
            {
                label: 'Transition smoothness review',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Review all transitions in:

**Manuscript**: "{{title}}" — {{description}}

Check:
1. **Chapter transitions**: Does each chapter end with a hook and begin with orientation?
2. **Scene breaks**: Are time/location jumps clear?
3. **POV shifts**: If multi-POV, are switches smooth and clearly signaled?
4. **Timeline jumps**: Are flashbacks/flash-forwards handled well?
5. **Tone shifts**: Do tonal changes feel intentional or jarring?

Flag the 5 roughest transitions and suggest smoother alternatives.`,
            },
            {
                label: 'Emotional beat mapping',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Map the emotional journey in:

**Manuscript**: "{{title}}" — {{description}}

Chapter by chapter, identify:
- **Dominant emotion**: What should the reader feel?
- **Emotional high point**: The strongest moment
- **Emotional low point**: The most vulnerable/sad moment
- **Emotional variety**: Does each chapter offer a different emotional flavor?

Then assess:
- Is there enough emotional variety or does it feel monotone?
- Do big emotional moments land? Are they properly set up?
- Is the emotional climax the strongest moment in the book?
- Are there enough quiet, intimate moments between action?`,
            },
            {
                label: 'Sensory detail enhancement',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Audit sensory details in:

**Manuscript**: "{{title}}" — {{description}}

1. **Sense inventory**: Which of the 5 senses are used? Which are underused?
2. **Visual-heavy check**: Is the writing too visual with not enough sound, smell, touch, taste?
3. **Key scenes**: Are pivotal scenes richly grounded in sensory experience?
4. **Setting atmosphere**: Do locations have distinctive sensory signatures?
5. **Character-filtered**: Are sensory details filtered through the POV character's personality?

Identify 5-10 scenes that would benefit most from sensory enrichment and suggest specific details.`,
            },
            {
                label: 'Info-dump & exposition detection',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Scan for info-dumps and exposition problems in:

**Manuscript**: "{{title}}" — {{description}}

Flag every instance of:
1. **Backstory dumps**: Paragraphs of history interrupting the action
2. **World-building lectures**: Characters explaining things the reader doesn't need yet
3. **As-you-know-Bob dialogue**: Characters telling each other things they already know
4. **Mirror descriptions**: Character describing their own appearance while looking in a mirror
5. **Prologue info-dump**: Does the opening front-load too much context?

For each: quote the passage, explain why it's a problem, and suggest how to weave the information in naturally (through action, dialogue subtext, or gradual revelation).`,
            },
            // ── Pass 3: Micro / Line-Level (5 steps) ──
            {
                label: 'Copy edit pass',
                skill: 'revise',
                taskType: 'final_edit',
                promptTemplate: `Perform a copy edit pass on:

**Manuscript**: "{{title}}" — {{description}}

Check for:
- Grammar errors
- Punctuation issues (especially dialogue punctuation)
- Spelling mistakes
- Homophone errors (their/there/they're, its/it's)
- Subject-verb agreement
- Tense consistency
- Comma splices and run-on sentences

List all errors found with chapter/location and correction.`,
            },
            {
                label: 'Line edit pass',
                skill: 'revise',
                taskType: 'final_edit',
                promptTemplate: `Perform a line edit pass on:

**Manuscript**: "{{title}}" — {{description}}

Focus on:
- **Prose rhythm**: Sentence length variety, flow, musicality
- **Word choice**: Precision, specificity, avoiding generic words
- **Verb strength**: Replace weak verbs (was, had, got) with vivid ones
- **Clarity**: Any confusing sentences or ambiguous references?
- **Redundancy**: Phrases that say the same thing twice

Show 10 before/after examples of line-level improvements.`,
            },
            {
                label: 'Repetition finder',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Find overused words and phrases in:

**Manuscript**: "{{title}}" — {{description}}

Report on:
1. **Overused words**: Adverbs, weak verbs, filler words with frequency
2. **Crutch phrases**: Repeated constructions the author leans on
3. **AI-sounding words**: delve, tapestry, testament, visceral, nuanced, multifaceted, resonate, paradigm, myriad, beacon, realm
4. **Repetitive openers**: Sentence-starting patterns
5. **Passive voice frequency** (target: <10%)
6. **Adverb density** (target: <5 per 1000 words)

For each: word/phrase, frequency, example, and suggested alternatives.`,
            },
            {
                label: 'Crutch word elimination',
                skill: 'revise',
                taskType: 'final_edit',
                promptTemplate: `Eliminate crutch words from:

**Manuscript**: "{{title}}" — {{description}}

Specific targets:
- **Just, really, very, quite, actually, basically, literally** — flag every instance, suggest which to cut
- **Suddenly** — almost always cuttable, show the action instead
- **Felt/feeling** — usually telling, show the sensation
- **Started to / began to** — just do the action
- **Seemed / appeared** — be more direct
- **That** — flag unnecessary instances
- **Nodded/shrugged/sighed** — overused physical beats

Provide a prioritized cut list with estimated word savings.`,
            },
            {
                label: 'Sensitivity read',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Perform a sensitivity read on:

**Manuscript**: "{{title}}" — {{description}}

Check for:
1. **Cultural representation**: Are characters from diverse backgrounds portrayed authentically?
2. **Stereotypes**: Any characters reduced to stereotypes?
3. **Language sensitivity**: Outdated or potentially offensive terms?
4. **Power dynamics**: Are marginalized characters given agency?
5. **Historical accuracy**: If set in a real period/place, are cultural details accurate?
6. **Unconscious bias**: Any patterns in which characters are villains, heroes, or victims?

Note: This is a preliminary read. For publication, a human sensitivity reader is recommended. Flag potential issues for professional review.`,
            },
            // ── Final: Beta Readers + Synthesis ──
            {
                label: 'Beta reader panel',
                skill: 'beta-reader',
                taskType: 'revision',
                promptTemplate: `You are a panel of 5 beta readers with different perspectives. Read and respond:

**Manuscript**: "{{title}}" — {{description}}

**Reader 1 — The Casual Reader**: Gut reactions, where you got bored, enjoyment rating 1-10
**Reader 2 — The Genre Expert**: Genre compliance, trope execution, market positioning, rating 1-10
**Reader 3 — The Harsh Critic**: Plot holes, weak motivations, clichés, the single biggest problem
**Reader 4 — The Target Reader**: Emotional journey, favorite scenes, would you recommend? Rating 1-10
**Reader 5 — The Romance/Thriller Super-Fan**: What made you keep reading? What almost made you stop? Pre-order the sequel?

Keep each reader's response to 200-300 words. Be specific with chapter references.`,
            },
            {
                label: 'Final revision action plan',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Synthesize ALL 20 prior revision passes into a final action plan:

**Manuscript**: "{{title}}" — {{description}}

Create:
1. **Overall Grade**: A-F with justification
2. **Top 5 Strengths**: What to keep and amplify
3. **Critical Fixes** (5-7 must-do items, ranked by priority)
4. **Important Improvements** (5-7 should-do items)
5. **Polish Items** (3-5 nice-to-have refinements)
6. **Revision Roadmap**: Pass 1 → Pass 2 → Pass 3 order of operations
7. **Market Readiness**: Ready for beta readers? Agent? Self-publishing?
8. **Encouraging Close**: What makes this book worth finishing

Make every recommendation specific and actionable with chapter references.`,
            },
            // ══ Pass 4: APPLY the revisions — produce a REAL revised manuscript ══
            // These steps (phase: 'revision_apply') actually rewrite the manuscript
            // instead of just analyzing it. Without these steps, users got 21
            // analysis reports and no revised book.
            {
                label: 'Apply macro revisions (full manuscript rewrite)',
                skill: 'revise',
                taskType: 'revision',
                phase: 'revision_apply',
                promptTemplate: `Rewrite the FULL uploaded manuscript applying the Pass 1 (macro/structural) revision notes from prior steps.

**Manuscript**: "{{title}}" — {{description}}

You have access to the FULL uploaded manuscript plus the analyses from 7 prior macro passes covering plot structure, pacing, character arcs, theme, world-building, stakes, and subplots.

## YOUR TASK
Output the COMPLETE revised manuscript — every chapter, in full — with the macro/structural fixes applied:

- Tighten plot structure where analysis flagged weakness
- Fix pacing sags; cut or combine chapters only if analysis clearly said to
- Strengthen character arcs; add missing growth beats
- Reinforce theme where it drifted
- Resolve continuity/world-building contradictions
- Escalate stakes where they plateaued
- Close dropped subplot threads

## CRITICAL OUTPUT RULES
1. Output the ENTIRE revised manuscript, start to finish. Don't summarize. Don't say "Chapter 1 revised version would go here".
2. Preserve chapter structure. Start each chapter with "# Chapter N: Title" or "## Chapter N".
3. Write actual prose, not bullet points or change logs.
4. Keep the author's voice. Only change what the analysis specifically flagged.
5. If the manuscript is very long and you run out of space, stop at a chapter boundary — the system will ask you to continue from there.
6. Do NOT include any meta-commentary like "I revised this by...". Output ONLY the manuscript itself.`,
            },
            {
                label: 'Apply scene-level revisions (full manuscript rewrite)',
                skill: 'revise',
                taskType: 'revision',
                phase: 'revision_apply',
                promptTemplate: `Take the Pass-1-revised manuscript from the previous step and rewrite it AGAIN, this time applying Pass 2 (scene-level) revision notes.

**Manuscript**: "{{title}}" — {{description}}

## YOUR INPUT
- The Pass-1-revised manuscript from the previous "Apply macro revisions" step (in your context above)
- 7 scene-level analyses covering dialogue, show-vs-tell, scene tension, transitions, emotional beats, sensory detail, info-dumps

## YOUR TASK
Rewrite every chapter applying scene-level fixes:

- Tighten and distinctify dialogue; eliminate "as you know Bob" exposition
- Convert telling to showing for emotional beats the analysis flagged
- Give each scene a clear goal/obstacle/stakes/outcome
- Smooth the roughest transitions (flagged in prior analysis)
- Add sensory detail to pivotal scenes
- Break up info-dumps into action/dialogue/subtext

## CRITICAL OUTPUT RULES
1. Output the ENTIRE revised manuscript, not just flagged sections.
2. Preserve chapter structure.
3. Do NOT regress Pass-1 improvements. Keep the macro fixes from the prior step.
4. If you run out of space, stop at a chapter boundary — the system will continue from there.
5. Output ONLY the manuscript itself — no commentary.`,
            },
            {
                label: 'Apply line-level revisions (full manuscript rewrite)',
                skill: 'revise',
                taskType: 'final_edit',
                phase: 'revision_apply',
                promptTemplate: `Take the Pass-2-revised manuscript from the previous step and rewrite it ONE MORE TIME, this time applying Pass 3 (line-level / copy-edit) polish.

**Manuscript**: "{{title}}" — {{description}}

## YOUR INPUT
- The Pass-2-revised manuscript from the previous step (in your context above)
- 5 line-level analyses covering copy edits, line edits, repetition, crutch words, sensitivity

## YOUR TASK
Produce the FINAL polished manuscript by applying line-level fixes:

- Fix grammar, punctuation, spelling, homophone errors
- Tighten prose rhythm; vary sentence length
- Strengthen weak verbs; cut redundant phrases
- Remove crutch words flagged in prior analysis (just, really, very, actually, suddenly, started to, began to, felt, seemed)
- Cut overused adverbs; keep the ones that earn their place
- Address sensitivity concerns (where flagged) without losing the author's voice

## CRITICAL OUTPUT RULES
1. Output the ENTIRE polished manuscript.
2. Preserve all Pass-1 and Pass-2 improvements.
3. Preserve chapter structure with "# Chapter N: Title" or "## Chapter N" headers.
4. If you run out of space, stop at a chapter boundary — the system will continue.
5. This is the FINAL version. Make it publishable.
6. Output ONLY the manuscript — no commentary, no change logs.`,
            },
        ],
    }
]    