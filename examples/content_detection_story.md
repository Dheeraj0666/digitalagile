Build a polished, responsive React + TypeScript frontend for a written-text authorship assessment tool.

Acceptance criteria:
1. User can paste or type text (at least 5000 characters) and see a character count.
2. A clear Analyze button invokes an asynchronous MOCK service (no real detection model, no backend yet).
3. Display loading, disabled, empty-state, and error states.
4. After analysis, show one of "AI-like", "Human-like", or "Inconclusive" as an illustrative mock result.
5. Include a visible disclaimer: text alone cannot reliably establish AI or human authorship; never present a definitive accusation.
6. Mobile-friendly UI, accessible labels, and keyboard interaction.
7. Put mock service logic in a separate TypeScript module so the backend agent can replace it later.
8. Add at least one automated component test for a core interaction.
9. Ensure npm build, lint/typecheck, and tests succeed.

Do not claim to provide a real AI detector. This is a frontend-only proof of concept.
