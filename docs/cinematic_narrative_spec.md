# Cinematic Narrative Redesign — "Apple Keynote / Netflix Doc" Style

Instead of a dense, data-heavy "dashboard tutorial," the story mode should feel like the intro sequence to a high-end documentary or a flagship Apple keynote presentation. 

## 1. Design Direction (The "How")

- **Kill the clutter:** Remove all "Chapter" labels, tiny data pills, complex equations, and technical jargon during the intro.
- **Massive Typography:** Use huge, elegant text (e.g., `Playfair Display` or `DM Serif Display` at `4vw` to `6vw`) centered perfectly on screen.
- **The "One Human Statement" Rule:** Each slide has exactly one bold, human-readable claim. 
- **Subtle Context:** Any data or subtext fades in slowly *below* the main statement, in a clean sans-serif (`system-ui` or `Helvetica`), much smaller, and slightly dimmed.
- **Cinematic Pacing:** Transitions shouldn't just "slide" — they should dissolve/fade over 1–1.5 seconds. The background should be pitch black (`#000000` or a very deep cinematic charcoal `#0a0a09`) so the text feels incredibly sharp.
- **Micro-animations:** Numbers shouldn't just appear; they should silently tick up in the background like a heartbeat.

---

## 2. Exact Content Copy (The "What")

Here is the exact frame-by-frame script for the narrative overlay. 

### Scene 1 (The Hook)
**Main Headline (Massive, White):** 
"Bengaluru has 198 wards."

**Subhead (Fades in 1 second later, Grey):** 
"Only a fraction are worth our capital."

---

### Scene 2 (The Input)
**Main Headline:**
"We stopped guessing. We started measuring."

**Subhead (Below):**
"Ingesting thousands of property listings, transit routes, and tech parks to find the city's true pulse."

*(Visual subtly behind the text: Large, faint counters ticking up: "42,000+ Listings" | "1,800+ Transit Nodes" | "140+ Tech Parks")*

---

### Scene 3 (The Noise)
**Main Headline:**
"The market is loud. We silence the noise."

**Subhead:**
"Stripping away luxury outliers, dead data, and statistical anomalies. Only the pure signal remains."

---

### Scene 4 (The Economics)
**Main Headline:**
"Rent a 3BHK. Monetize the rooms."

**Subhead:**
"The core arbitrage equation. If the margin isn't viable, the ward is dead to us. No exceptions."

---

### Scene 5 (The Gravity)
**Main Headline:**
"Proximity is power."

**Subhead:**
"Young professionals cluster near work and transit. Our gravity model mathematically scores every neighborhood's pull."

---

### Scene 6 (The Contagion)
**Main Headline:**
"Strength is contagious."

**Subhead:**
"A great neighborhood surrounded by greatness is defensible. An isolated one is a risk. We measure the aura of every ward."

---

### Scene 7 (The Reveal)
**Main Headline (Gold/Amber text):**
"The undeniable hotspots."

**Subhead:**
"{X} Tier 1 Wards discovered. The absolute best places in Bengaluru to build Flent homes."

---

### Scene 8 (The Handoff)
**Main Headline:**
"Now, the model is yours."

**Subhead:**
"Challenge our assumptions. Adjust the levers. Watch the city react."

*(A single, sleek button fades in: **"Enter the Dashboard"**)*

---

## 3. Implementation Changes Required in Code

When moving from the current "mid" version to this cinematic version, I will:

1. **Delete**: The `<div class="narr-equation">` and `<div class="narr-rule-pill">` CSS structures entirely.
2. **Rewrite CSS**: Shift `.narr-title` to be massive (`font-size: clamp(36px, 5vw, 72px)`), perfectly centered.
3. **Change Timing**: Increase CSS transition durations from `0.7s` to `1.2s` for that slow, breathy Apple-style fade. 
4. **Content Object**: Replace the dense 12-chapter JSON array in JS with this exact 8-scene copy. 
5. **Background Dynamics**: Ensure the background is pitch black, dropping the semi-transparent overlay look. When the user clicks "Enter Dashboard", the black fades away to reveal the brightly-lit cream/linen dashboard beneath it (like turning on the lights).
