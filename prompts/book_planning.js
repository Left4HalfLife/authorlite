export const BOOK_PLANNING = [
// ═══════════════════════════════════════════════════════════
    // Template 1: Book Planning
    // ═══════════════════════════════════════════════════════════
    {
        type: 'book-planning',
        label: 'Book Planning',
        description: 'Market analysis, premise development, characters, chapter outline, and synopsis',
        steps: [
            {
                label: 'Develop premise',
                skill: 'premise',
                taskType: 'general',
                promptTemplate: `Develop a commercially viable premise for: {{description}}

Using the market analysis, create:
1. **Logline**: 1-2 sentences that sell the book
2. **What-If question**: The central hook
3. **Core conflict**: Internal and external
4. **Stakes**: What happens if the protagonist fails? (personal, professional, global)
5. **Theme statement**: The book's deeper argument about life
6. **Unique hook**: What makes THIS book stand out from the comp titles?
7. **Genre promise**: What emotional experience are we delivering?
8. **Plot threads and story flow to preserve**: Identify any specific plot threads, scene flow, escalation path, reveals, relationship turns, or ending trajectory explicitly mentioned in the source idea. List them as concrete threads the later planning stages must maintain.

Make this premise commercially compelling AND creatively exciting.
If the source idea includes specific plot flow or thread progression, surface it explicitly rather than abstracting it away.`,
            },
            {
                label: 'Character profiles',
                skill: 'book-bible',
                taskType: 'book_bible',
                promptTemplate: `Create detailed character profiles for: {{description}}

Build out:
**Protagonist**: Full name, age, backstory, motivation (want vs need), fatal flaw, emotional wound, strengths, appearance, speech patterns, character arc
**Antagonist**: Motivation, backstory, why they believe they're right, how they challenge the protagonist, fatal flaw, strengths, apperance, speech patterns, character arc
**3-4 Supporting characters**: Name, role, relationship to protagonist, how they advance/challenge the arc

Each character should feel real — contradictions, desires, fears. Write 800+ words total.`,
            },
            {
                label: 'Chapter-by-chapter outline',
                skill: 'outline',
                taskType: 'outline',
                promptTemplate: `Create a detailed chapter-by-chapter outline for: {{description}}

For each chapter include:
- **Chapter number & title**
- **POV character**
- **Key beats** (3-5 per chapter)
- **Turning points** and revelations
- **Tension level** (1-10)
- **Chapter ending hook**

Structure using three-act beats:
- Act 1 (25%): Setup, inciting incident, debate/refusal
- Act 2A (25%): Rising action, fun & games, midpoint shift
- Act 2B (25%): Complications, all-is-lost moment
- Act 3 (25%): Climax sequence, resolution

Target number of chapters based on the project settings. If none, default to 15-20. Number EVERY chapter.`,
            },
            {
                label: 'Synopsis generation',
                skill: 'outline',
                taskType: 'general',
                promptTemplate: `Generate professional synopses for: {{description}}

Create two versions:
1. **One-page synopsis** (~500 words): Complete story arc including the ending. Professional query format.
2. **Three-page synopsis** (~1500 words): Expanded with character arcs, key scenes, and emotional beats.

Both should:
- Reveal the entire plot (including ending — this is for industry professionals)
- Show the character's emotional journey
- Demonstrate clear story structure
- Be written in present tense, third person
- Feel compelling to read, not just dutiful`,
            },
            {
                label: 'Review & refine plan',
                skill: 'revise',
                taskType: 'revision',
                promptTemplate: `Review the complete book plan we've built. Check for:

1. **Plot holes**: Any logical gaps in the outline?
2. **Character consistency**: Do motivations and arcs make sense?
3. **Pacing issues**: Any dead zones or rushed sections in the outline?
4. **Theme coherence**: Does every subplot reinforce the theme?
6. **Genre compliance**: Are all genre promises being fulfilled?

Provide specific improvements, not vague suggestions. Reference chapter numbers and character names.`,
            },
            {
                label: 'Contradiction checks',
                skill: 'continuity-check',
                taskType: 'revision',
                promptTemplate: `Run contradiction checks on the complete book plan for: {{description}}

Using continuity-check principles, verify:
1. **Character consistency**: Traits, motivations, abilities, and relationship logic remain coherent.
2. **Timeline logic**: Sequence, travel/time assumptions, and cause-effect progression remain plausible.
3. **World/setting consistency**: Rules, geography, naming, and terminology do not drift.
4. **Plot thread continuity**: Setup/payoff, unresolved threads, and object tracking stay consistent.
5. **Information flow**: Characters only know what they should know at each stage.

Categorize findings as ERROR, WARNING, or INFO with evidence and suggested fixes, then provide a corrected integrated plan draft.`,
            },
        ],
    }

]