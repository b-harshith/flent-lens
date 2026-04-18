# Flent Smart Home Finder
## Consumer Product Feature Specification
*Authored: April 2026 | Status: Concept / Pending Build*

---

## 1. Overview

### What is it?
A conversational, dialogue-driven apartment matching tool embedded on Flent's website. Instead of traditional filter-based search (bedrooms, area, price dropdowns), the Finder asks a curated sequence of lifestyle questions to deeply understand a user's actual needs and then surfaces a **personalised hit list** of Bengaluru areas and available Flent homes — with narrative explanations for every recommendation.

### Why build it?
Flent serves a high-trust, premium audience that often relocates to Bengaluru for work. These users frequently don't know Bengaluru's neighborhoods at all. They find area-filter search useless ("I don't know if I want HSR or Koramangala — that's what I'm trying to figure out"). A dialogue-driven finder reduces cognitive load, builds emotional connection with the brand, and drives higher conversion.

### Target Users
- Tech professionals relocating to Bengaluru
- PG-to-Flent upgrades (users tired of shared mess)
- Students joining IISc, IIIT, etc.
- Expats / international placements

---

## 2. Conversation Flow Design

The Finder is structured as a **9-step conversation**, displayed one question at a time with animated transitions. Each step has a "Skip" option where appropriate.

### Step 1 — Opening (Warm Welcome)
```
Screen text: "Let's find you a home you'll actually love."
Sub-text: "Answer a few questions — we'll do the thinking."
Input: First name only (single text field, large and centered)
CTA: "Let's go →"
```

### Step 2 — Workplace Anchor
```
Question: "Where do you spend most of your weekdays, {name}?"
Input: Searchable text field with Google Places Autocomplete
       Map pins suggested: major tech parks, hospitals, colleges, 
       banks, company campuses in Bengaluru
       Example chips: "Manyata Tech Park", "Electronic City", "Embassy Golf Links"
Purpose: Centroid distance scoring for all wards
```

### Step 3 — Commute Tolerance
```
Question: "How long a commute is okay for you?"
Input: Animated horizontal slider
       Labels: 10 min → 15 min → 20 min → 30 min → 45 min → "I'm flexible"
Sub-input: "How do you usually commute?"
       Icons: 🚇 Metro | 🚗 Own Car | 🛺 Auto | 🚌 Bus | 🛵 2-Wheeler
Purpose: Distance threshold + transit score weighting
```

### Step 4 — Budget
```
Question: "What's your comfortable monthly rent per room?"
Input: Pill button grid (tap to select):
       [ Under ₹15,000 ] [ ₹15k–20k ] [ ₹20k–30k ] [ ₹30k–40k ] [ ₹40k+ ]
Purpose: Budget-band filter against listings.csv median rents
```

### Step 5 — Living Arrangement
```
Question: "Are you looking for your own space, or open to flatmates?"
Input: Three illustrated cards (large, visual):
       🏠 Solo — "I want the place to myself"
       👥 1 Flatmate — "One other person works"
       🏘️ Multi-Share — "I'm fine with 2–3 flatmates, lower rent"
Purpose: BHK type and room-sharing preference mapping
```

### Step 6 — Lifestyle Vibe
```
Question: "What matters most about where you live? Pick up to 3."
Input: Multi-select tag cloud with icons:
       🌳 Green & Quiet       — Parks, tree-lined streets, low-noise
       🚇 Metro Connectivity  — Walking distance to metro stations
       ☕ Café & Work Culture — Good coffee shops, coworking nearby
       🛒 Daily Conveniences  — Supermarkets, pharmacies, restaurants
       🏋️ Active Lifestyle    — Gyms, sports courts, running tracks
       🎉 Social Scene        — Restaurants, bars, events
       🏢 Tech Hub Proximity  — Near SEZs / major tech parks
       🐾 Pet-Friendly Area   — Parks, open spaces, pet-tolerant community
       🌙 Night Life Access   — Active evenings, entertainment
       🛵 Easy Delivery Zone  — Swiggy/Zomato/quick commerce delivery
Purpose: Maps to ward-level signals (transit_score, sez_score, listing density, amenity tags)
```

### Step 7 — Flat Preferences (Optional)
```
Question: "Any preferences for the flat itself?" (Skippable)
Input: Multi-select checkbox chips:
       [ North-facing ] [ Corner unit ] [ High floor ] [ Pool view ]
       [ Balcony ] [ Garden access ] [ Quiet street ]
Purpose: Filters against listing-level attributes in listings.csv
Note: If attribute not in dataset, shown grayed out with "Ask our team"
```

### Step 8 — Move-In Timeline
```
Question: "When are you planning to move in?"
Input: Large pill buttons (tap one):
       [ ASAP — I'm ready ] [ In 2 weeks ] [ Next month ] [ Just exploring ]
Purpose: Filters available_from date in Flent listing data
```

### Step 9 — Deal-Breakers (Optional)
```
Question: "Anything that's a hard no? (Your answers stay private)"
Input: Multi-select chips:
       [ Mixed gender flat ] [ Pets in the home ] [ 3+ flatmates ]
       [ Non-veg cooking ] [ Smokers ] [ Old building ]
Purpose: Exclusion filter — removes listings/wards violating these constraints
```

---

## 3. Matching & Scoring Engine

### 3.1 Input Profile → Score Vector
All user answers are converted to a scoring profile:

```python
profile = {
  "office_lat": float,        # from Step 2 geocoding
  "office_lon": float,
  "max_commute_min": int,     # from Step 3
  "commute_mode": str,        # metro/car/auto/bus/bike
  "budget_min": int,          # from Step 4
  "budget_max": int,
  "bhk_preference": int,      # from Step 5 → 1/2/3 BHK
  "lifestyle_tags": list[str],# from Step 6
  "flat_prefs": list[str],    # from Step 7
  "move_in": str,             # from Step 8
  "deal_breakers": list[str]  # from Step 9
}
```

### 3.2 Ward Scoring Dimensions

For each BBMP ward, compute:

| Dimension | Logic | Weight |
|---|---|---|
| **Proximity Score** | Haversine(ward_centroid, office_location) with commute decay | 35% |
| **Budget Fit** | % of ward listings within user's budget band | 25% |
| **Vibe Match** | Tag-to-ward-signal alignment (see mapping below) | 20% |
| **Availability** | Count of Flent homes available in timeline | 10% |
| **Baseline Quality** | Ward OPP_SCORE from pipeline (Tier 1/2/3) | 10% |

### 3.3 Vibe Tag → Ward Signal Mapping

```
"Metro Connectivity"    → transit_score > 0.65
"Tech Hub Proximity"    → sez_employment_score > 0.60
"Green & Quiet"         → low listing density + low transit_score (paradoxically)
"Café & Work Culture"   → Koramangala / Indiranagar / HSR weightmap (hardcoded known zones)
"Daily Conveniences"    → high listing_count (proxy for amenity density)
"Active Lifestyle"      → proximity to known gym/sports corridors
"Social Scene"          → Indiranagar / Koramangala / Whitefield social zones
"Tech Hub Proximity"    → sez_employment_score
"Pet-Friendly Area"     → ward_area_sqkm > 1.5 (larger wards with open space)
```

---

## 4. Results Presentation

### 4.1 Hit List Structure (3–5 results, ranked)

Each result card shows:
```
┌──────────────────────────────────────────────────────────────┐
│  🏆  #1  Koramangala               ●●●●○  94% match          │
│  📍  12 min from your office (by metro)                      │
│                                                              │
│  WHY THIS WORKS FOR YOU                                      │
│  ✓ 3 Flent homes available in your budget                    │
│  ✓ One of Bengaluru's strongest metro corridors              │
│  ✓ Strong café and coworking culture                         │
│  ✓ Tier 1 investment ward — high market demand               │
│                                                              │
│  WORTH KNOWING                                               │
│  ⚠ Peak-hour traffic adds ~15 min on cab commute             │
│  ⚠ Higher price sensitivity — book early                     │
│                                                              │
│  FLENT HOMES HERE NOW                                        │
│  [Fairmont — 3BHK, ₹32k/room, Available Now →]             │
│  [Arbour — 2BHK, ₹36k/room, Apr 26 →]                      │
│                                                              │
│  [View Full Area →]   [Save This]   [Compare]               │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Micro-Map
Each card includes an embedded mini-map (Leaflet, 200px tall) showing:
- Ward boundary polygon (from GeoJSON)
- Pin for user's office
- Dashed line showing commute route direction

### 4.3 Compare Mode
Toggle to show 2–3 areas side by side in a comparison grid:

| | Koramangala | HSR Layout | Whitefield |
|---|---|---|---|
| Commute | 12 min 🟢 | 18 min 🟡 | 35 min 🔴 |
| Budget fit | 2/3 homes | 3/3 homes | 3/3 homes |
| Vibe match | 94% | 87% | 71% |
| Metro access | ✓ | partial | ✓ |

### 4.4 Share & Save
- **Share Link**: URL encodes profile as base64 JSON → `flent.in/finder?q=eyJvZmZpY2...`
- **WhatsApp Share**: Pre-formatted message with top 3 results (for sharing with partner/flatmate)
- **Email**: Compose pre-filled with results summary
- **Save for later**: Stores to localStorage, resurfaces on next visit

---

## 5. UI/UX Design Principles

### Visual Language
Match Flent.in exactly:
- **Background**: Cream `#F5F0EB` 
- **Cards**: Ivory `#FAFAF7` with `18px` border radius
- **Type**: `Playfair Display` italic for emotive question text; `DM Sans` for UI
- **Buttons**: Black pill CTAs (`#111111`, `border-radius: 50px`)
- **Progress**: Subtle dot indicators at top (9 dots, fill as user progresses)

### Animation Principles
- Each question slides in from right, exits to left (slide transition)
- Answer selecting triggers a gentle "confirmation pulse" on the selected option
- Typing in text fields shows a subtle "wave" on the input underline
- Results appear with staggered card reveals (cascade in from bottom, 100ms delay each)
- Match percentage counter animates up (0 → 94%) on result reveal

### Accessibility
- All interactive elements have ARIA labels
- Tab navigation works through the full flow
- Keyboard shortcuts: Enter to advance, Escape to go back, Space to toggle multi-select

---

## 6. Data Dependencies

| Data Needed | Source | Status |
|---|---|---|
| Ward boundaries + OPP_SCORE + tier | `output/ward_analysis.geojson` | ✅ Pipeline output |
| Median rents per ward + BHK type | `ward_analysis.geojson` (avg_rent_1bhk etc.) | ✅ Pipeline output |
| Transit score per ward | `data/processed/transit_processed.csv` | ✅ Pipeline output |
| SEZ employment score per ward | in geojson | ✅ Pipeline output |
| Current Flent listing availability | Manual entry or Flent CMS API | ❌ Needs integration |
| Google Places geocoding (office location) | Google Maps JS API | ❌ Needs API key |
| Known neighborhood vibes (café zones etc.) | Hardcoded knowledge map | 🔧 To be built |

---

## 7. Future Enhancements

1. **AI Narrative Generation**: Feed profile + top3 wards into Claude API to generate fully personalised 3-paragraph narrative explanations ("Here's what we think about Koramangala for you specifically...")
2. **Real-time Flent Availability**: Connect to Flent's CMS/Supabase to show live room availability
3. **Commute Simulation**: Google Maps API actual travel time (not just Haversine)
4. **Flent Score Badge**: Show Flent's curation quality badge on matching Flent homes
5. **Flatmate Compatibility**: Optional — describe your lifestyle, we match you with compatible existing flatmates
6. **Price Trend Alerts**: "This area is heating up — 3 homes just got taken this week"
7. **Save and Return**: Login-gated saved searches,  price alert subscriptions
8. **A/B Testing**: Two flows — dialogue vs. grid filter — measure conversion difference

---

## 8. Implementation Path

When ready to build, this feature requires:

1. **Backend**: Flask/FastAPI endpoint `POST /api/finder/match` 
   - Input: JSON profile from user's answers
   - Loads `output/ward_analysis.geojson`
   - Runs ward scoring algorithm
   - Returns ranked list of wards + matched Flent listing URLs

2. **Frontend**: Embeddable React component or standalone HTML page
   - Can be iframed into flent.in at `/finder`
   - Or built as a Next.js page added to Flent's existing web app

3. **Integration**: Flent's engineering team adds the embed to their website CMS

4. **Analytics**: Track funnel drop-off per step, most common preferences, conversion rate to booking

---

*This document is a living spec. Update as product requirements evolve.*
*See `implementation_plan.md` in the Antigravity conversation context for dashboard build context.*
