---
name: UrbanCare
description: Live stop crowding, wait time and ad audience, set as São Paulo bus-stop signage.
colors:
  totem-ink: "#16181B"
  ink-raised: "#24272B"
  ink-rule: "#3A3D42"
  ink-muted: "#55585E"
  ink-quiet: "#A9ACB2"
  concrete-rule: "#C9C7C0"
  concrete-ground: "#E4E3DE"
  concrete-raised: "#F2F1EC"
  plate-white: "#FFFFFF"
  signal-yellow: "#FFD200"
  warning-amber-text: "#8A5A00"
  status-green: "#00843D"
  status-green-on-ink: "#5FD39A"
  status-red: "#D52B1E"
  status-red-on-ink: "#FF8175"
  sptrans-blue: "#0055B8"
  info-blue-on-ink: "#8DB6F0"
  data-1: "#E1EAF5"
  data-2: "#B3CAE8"
  data-3: "#6F9BD6"
  data-4: "#2F6DBE"
  data-5: "#0A3F8C"
  map-ground: "#D5D3CC"
  map-park: "#D3E2CC"
typography:
  display:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "40px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.005em"
  heading:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "28px"
    fontWeight: 700
  kpi:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "44px"
    fontWeight: 600
    lineHeight: 1
  metric:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "24px"
    fontWeight: 700
  title:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    letterSpacing: "0.04em"
  body:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
  body-strong:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 600
  caption:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
  small:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 500
  small-strong:
    fontFamily: "Barlow, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 600
  button:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    letterSpacing: "0.05em"
  overline:
    fontFamily: "Barlow Semi Condensed, Barlow, Arial Narrow, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.08em"
rounded:
  bar: "1px"
  chip: "2px"
  plate: "3px"
spacing:
  "2": "2px"
  "4": "4px"
  "8": "8px"
  "12": "12px"
  "16": "16px"
  "20": "20px"
  "24": "24px"
  "32": "32px"
components:
  button-primary:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
    typography: "{typography.button}"
    rounded: "{rounded.plate}"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.ink-raised}"
    textColor: "{colors.plate-white}"
  button-primary-pressed:
    backgroundColor: "{colors.ink-rule}"
    textColor: "{colors.plate-white}"
  button-secondary:
    backgroundColor: "{colors.plate-white}"
    textColor: "{colors.totem-ink}"
    typography: "{typography.button}"
    rounded: "{rounded.plate}"
    height: "36px"
  plate-header:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
    typography: "{typography.title}"
    height: "44px"
  plate-body:
    backgroundColor: "{colors.plate-white}"
    textColor: "{colors.totem-ink}"
    rounded: "{rounded.plate}"
  kpi-cell:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
    typography: "{typography.kpi}"
  line-chip:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
    typography: "{typography.small-strong}"
    rounded: "{rounded.chip}"
  pill-normal:
    backgroundColor: "{colors.status-green}"
    textColor: "{colors.plate-white}"
    typography: "{typography.overline}"
    rounded: "{rounded.chip}"
  pill-atencao:
    backgroundColor: "{colors.signal-yellow}"
    textColor: "{colors.totem-ink}"
    typography: "{typography.overline}"
    rounded: "{rounded.chip}"
  pill-critico:
    backgroundColor: "{colors.status-red}"
    textColor: "{colors.plate-white}"
    typography: "{typography.overline}"
    rounded: "{rounded.chip}"
  pill-ao-vivo:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
    typography: "{typography.overline}"
    rounded: "{rounded.chip}"
  pill-destaque:
    backgroundColor: "{colors.sptrans-blue}"
    textColor: "{colors.plate-white}"
    typography: "{typography.overline}"
    rounded: "{rounded.chip}"
  nav-item:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.ink-quiet}"
    typography: "{typography.body}"
  nav-item-hover:
    backgroundColor: "{colors.ink-raised}"
    textColor: "{colors.plate-white}"
  nav-item-active:
    backgroundColor: "{colors.signal-yellow}"
    textColor: "{colors.totem-ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.chip}"
  toggle-on:
    backgroundColor: "{colors.status-green}"
    rounded: "{rounded.plate}"
    width: "40px"
    height: "22px"
  toggle-off:
    backgroundColor: "{colors.concrete-rule}"
    rounded: "{rounded.plate}"
    width: "40px"
    height: "22px"
  segmented:
    backgroundColor: "{colors.plate-white}"
    textColor: "{colors.totem-ink}"
    typography: "{typography.button}"
    rounded: "{rounded.plate}"
  segmented-selected:
    backgroundColor: "{colors.totem-ink}"
    textColor: "{colors.plate-white}"
---

# Design System: UrbanCare

## Overview

**Creative North Star: "Placa de Ponto"**

UrbanCare is drawn as São Paulo bus-stop signage. Every panel is an enamel stop plate: a white body under a heavy ink header band carrying a condensed uppercase title. Every line number is a small ink plate chip. The sidebar is the stop totem, an ink column whose navigation reads as stops strung along a thin line, with the current stop lit in signage yellow. The page sits on concrete grey, the way a plate sits on a pavement pole.

The density is that of a working operations tool, not a showcase. A single ink departure-board strip carries the live KPIs, and rows of equal-height plates below it say where the network hurts and what to do about it. Colour is signage colour: yellow marks brand and "here/now", green, yellow and red carry status (always paired with a shape), SPTrans blue carries audience and info data on a locked five-step ramp. Depth comes from ink against white against concrete, never from shadow.

The world rejects the dark SaaS card grid with a neon accent (direction contract THESIS). Operação and Publicidade use the same plates and vocabulary, because one sensor serves both buyers.

**Key Characteristics:**
- Concrete ground, white plates, ink header bands; flat, no soft shadows.
- Barlow Semi Condensed for plate titles, figures and buttons; Barlow for sentences.
- Status is shape-coded: circle normal, triangle atenção, square crítico.
- Red reserved for crítico; yellow marks brand, active stop and "now".
- Audience data on a stepped five-level blue ramp; no gradients anywhere.
- Tight corners: 3px plates, 2px chips, 1px bars.

## Colors

A signage palette: ink, concrete and white carry the structure; four saturated signal hues each hold one job.

### Primary
- **Totem Ink** (totem-ink): sidebar, plate header bands, KPI strip, primary buttons, line chips, dialog and toast headers, primary text on white. It is the brand colour as well as the structural one.
- **Signage Yellow** (signal-yellow): logo plate, active nav plate, the "Agora" marker on charts, the 3px hover rule under primary buttons, the atenção pill and bars, "Ver todos" links on ink. Also the atenção status hue, always with a triangle.

### Secondary
- **SPTrans Blue** (sptrans-blue): the info status and the Destaque pill; the dashed "média" line on the hourly chart; the ad-panel block in the detection scene.
- **Audience Ramp** (data-1 to data-5): the five locked steps for audience intensity (heatmap cells, legend "menos → mais"). White figures sit only on data-5.

### Tertiary (status)
- **Stop Green** (status-green): normal status (circle), toggle on, dwell-time bars under threshold, campaign delivery bar, privacy plate top rule.
- **Crítico Red** (status-red): crítico status (square), the recommendation plate band and outline, the over-limit line segment and "limite" chip. Nothing else.
- **On-ink twins** (status-green-on-ink, status-red-on-ink, info-blue-on-ink): the same three meanings when text sits on ink (KPI deltas, detection boxes).
- **Warning Amber Text** (warning-amber-text): atenção meaning as text on white, where yellow would fail contrast.

### Neutral
- **Concrete Ground** (concrete-ground): the app background behind every plate.
- **Plate White** (plate-white): plate bodies, title plate, dialog body, secondary buttons.
- **Concrete Raised** (concrete-raised): quiet raised fills inside plates.
- **Concrete Rule** (concrete-rule): dividers and borders on white; forecast bars; toggle off.
- **Ink Raised / Ink Rule** (ink-raised, ink-rule): hover fills and 1px cell dividers on ink.
- **Ink Muted** (ink-muted): secondary text on white. **Ink Quiet** (ink-quiet): secondary text and idle nav on ink.
- **Map Ground / Map Park** (map-ground, map-park): the street-map canvas only.

### Named Rules
**The Red Means Crítico Rule.** Red appears only where something is crítico or over its limit, and on the action that answers it. Never for emphasis, category or decoration.

**The On-Ink Twin Rule.** A status hue on ink uses its lighter on-ink twin; on white it uses the base hue (atenção text on white uses amber, not yellow).

**The Locked Ramp Rule.** Quantities use the five fixed blue steps. No gradients, no interpolated tints, no opacity ramps.

## Typography

**Display Font:** Barlow Semi Condensed (with Barlow, Arial Narrow)
**Body Font:** Barlow (with Arial)

**Character:** Barlow Semi Condensed is the plate lettering: narrow, bold, set uppercase with tracking for titles and buttons, and plainly for big figures. Barlow is the same family at normal width for sentences, so the pairing reads like a sign with small print.

### Hierarchy
- **Display** (700, 40px, 1.1, -0.5%): page titles on the title plate; dialog question.
- **Heading** (700, 28px): second-level headings; shipped as a style, rarely used on the four screens.
- **KPI** (600, 44px, 1.0): live figures in the departure strip and ink stat plates.
- **Metric** (700, 24px): secondary figures inside plates (12, -9%, 6m 50s).
- **Title** (700, 15px, uppercase, +4%): plate header band titles, always white on ink.
- **Body / Body Strong** (400 / 600, 14px, 1.4): sentences, row names, stop names.
- **Caption / Small / Small Strong** (400 / 500 / 600, 12px): meta lines, axis labels, chip text.
- **Button** (700, 14px, uppercase, +5%): every button and segmented option.
- **Overline** (700, 12px, uppercase, +8%): labels that name a value or column (KPI labels, table heads, pill text, sidebar group label).

### Named Rules
**The Plate Voice Rule.** Condensed uppercase is for things a sign would print: plate titles, buttons, labels, pills. Sentences stay in Barlow, sentence case.

**The Label, Not Kicker, Rule.** Overline names the value or column directly beneath or beside it. It never sits above a headline as a decorative eyebrow.

## Layout

A 1440px frame: a 240px ink sidebar, then a main column on concrete padded 32px top and 40px sides, with a 24px gap between rows. The main column always opens with the title plate (display title, meta line, live pill and timestamp or actions at right), then the full-width KPI strip: one ink plate split into four cells. Below it come rows of plates, usually two per row (a wide left plate, 656px on Visão geral, beside a narrower right one). Plates in a row share one height. Spacing follows the 2/4/8/12/16/20/24/32 scale; inside plates, 20px padding is typical. Alert and ranking rows are separated by 1px concrete rules; a pill that does not fit beside a long name wraps under it instead of truncating the name.

## Elevation & Depth

Flat. There are no soft shadows on plates, dialogs or toasts. Depth is tonal: concrete ground, white plate, ink band, and the ink sidebar as the tallest layer. Overlays sit on an ink backdrop at 62% opacity; the dialog itself is a plate with an ink header band and no shadow.

### Named Rules
**The Flat Plate Rule.** A plate is lifted by its ink band and its contrast with concrete, never by a shadow.

## Shapes

Tight, enamel-sign corners: plates, buttons, segmented controls and the toggle at 3px; pills, line chips, heatmap cells and the active nav plate at 2px; chart bars at 1px. Rules do the structural work: a 6px ink top rule on the title plate, a 3px green top rule on the privacy plate, a 3px yellow bottom rule on hovered primary buttons, a 1px ink-rule left divider between KPI cells, 1.5px ink strokes on secondary buttons and segmented controls. Status shapes are drawn geometry (circle, triangle, square), as are the lock and the logo mark.

## Components

### Buttons
Heavy, sign-lettered, rectangular.
- **Shape:** near-square corners (3px), 36px tall.
- **Primary:** ink fill, white Button type ("ENVIAR EXTRA", "CONFIRMAR ENVIO").
- **Hover / Pressed:** hover lifts to ink-raised with a 3px signal-yellow bottom rule; pressed drops to ink-rule.
- **Secondary:** white with a 1.5px ink stroke and ink text ("MONITORAR", "CANCELAR", "IGNORAR").

### Status Pills
- **Style:** 2px corners, Overline type, a drawn shape before the word. Normal green with white circle; Atenção yellow with ink triangle; Crítico red with white square; Ao vivo ink with green circle; Destaque blue with white circle.
- **Rule:** the shape carries the meaning as much as the hue.

### Line Chips
Ink plate chips (2px corners, white Small Strong) for every bus line number: 875A, 177H, 6450, 7272. They appear inline in meta lines and titles.

### Cards / Containers (Plates)
- **Corner Style:** 3px.
- **Background:** white body under a 44px ink header band with a white uppercase Title; header right side holds legends, a live pill, a toggle, a segmented control or a yellow "Ver todos" link.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Variants:** the recommendation plate swaps the band to crítico red with a red outline; ink stat plates put KPIs directly on ink with 1px ink-rule dividers.
- **Internal Padding:** 20px.

### KPI Strip
One ink plate holding four cells separated by 1px ink-rule left rules. Each cell: Overline label in ink-quiet, KPI figure in white, delta line coloured by trend (positive green-on-ink, negative red-on-ink, warning yellow, neutral ink-quiet, brand info-blue-on-ink).

### Navigation
The sidebar is an ink totem: yellow logo plate mark, an Overline group label, then items strung as stops on a 2px ink-rule vertical line with a ring marker each. Default text is ink-quiet; hover fills ink-raised; active becomes a signal-yellow plate with an ink square marker and ink text. A privacy plate (ink-raised, 3px green top rule, drawn lock, "Contagem anônima") anchors the bottom.

### Toggle and Segmented Control
Toggle is 40×22 at 3px, green when on, concrete-rule when off, with a white knob. Segmented control is a white strip with a 1.5px ink stroke; the selected option becomes an ink fill with white Button type.

### Charts
Bars are ink (today) and concrete-rule (forecast) with a yellow "Agora" tag on the current bar; averages are a dashed blue line; limits are a dashed red line with a red "limite" chip. Dwell bars go green under threshold and yellow at or over it. Heatmaps use only data-1 to data-5. Map markers are drawn status shapes on map-ground with a translucent halo of the same hue.

### Dialog and Toasts
Dialog: white plate, ink header band with a small yellow square and Title text, Display question, Body details, secondary then primary button right-aligned. Toasts are ink plates. Backdrop is ink at 62%.

## Do's and Don'ts

### Do:
- **Do** put every panel on a white plate with a 44px ink header band and a white uppercase Title, on concrete ground.
- **Do** pair every status hue with its shape: circle normal, triangle atenção, square crítico.
- **Do** set every bus line number as an ink line chip (2px corners).
- **Do** use the on-ink twin of a status hue when it sits on ink, and amber for atenção text on white.
- **Do** keep plates in a row at equal height and rows 24px apart.
- **Do** keep corners at 3px for plates and controls, 2px for chips and cells, 1px for bars.

### Don't:
- **Don't** use red for anything that is not crítico, over a limit, or the action that answers it.
- **Don't** add soft shadows to plates, dialogs or toasts; depth is ink against white against concrete.
- **Don't** use gradients or interpolated tints for data; use the five blue steps.
- **Don't** nest cards inside plates; the plate is the only enclosure.
- **Don't** put Overline text above a headline as an eyebrow; it labels a value or column only.
- **Don't** use typographic glyphs (▲ ▼ ● ■) as status or trend icons; draw the shape.
