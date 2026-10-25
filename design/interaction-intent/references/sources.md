# Sources and evidence

The skill was distilled from the video *Why the best software must LIE to you* and checked against
outside sources. Use this file when a claim is questioned. Each entry says where a claim stands:

- **Documented** — stated in a standard, platform guideline, or the cited primary source.
- **Expert consensus** — repeated by credible practitioners and UX research groups; no controlled
  study located.
- **Speaker's claim** — from the video, not independently verified.
- **Corrected** — the video's version differs from the source.

## The core model

| Claim | Status | Source |
|---|---|---|
| Resolving ambiguous input costs time (wait), certainty (infer) or trust (act first); letting the user signal confidence avoids the guess | Speaker's synthesis — a framing, not a finding. The skill adds L0 (separate inputs) and L1 (compatible actions), which cost nothing and the video only touches in passing | Video |
| Double-click should extend the single-click, so the first click is right regardless | Documented | Apple, *Macintosh Human Interface Guidelines* (1992), archived; same rule says double-click must never be the only way to perform an action |
| Waiting out the double-click time before acting on single-click; single-clickers pay a ~0.5 s delay | Documented | Raymond Chen, "The Old New Thing", 2009-04-29 |
| Chen "first documented" the double-click wait for inline rename | **Corrected.** Chen's post is about debouncing users who double-click everything, so a stray second click doesn't land on a newly launched window. It does not discuss inline rename and is not the origin of the idea | Same post |

## Timing

| Claim | Status | Source |
|---|---|---|
| ~0.1 s feels instant, ~1 s keeps flow, ~10 s holds attention | Documented | Nielsen, "Response Times: The 3 Important Limits" (NN/g, 1993/2014) |
| Windows double-click time default 500 ms, user-configurable; tooltip initial 500 ms, reshow 100 ms, both derived from it | Documented | Microsoft Learn, `TTM_SETDELAYTIME` |
| AirPods wait 700 ms before pausing; phone pauses in under 300 ms | Speaker's measurement. Apple publishes no figure | Video |
| After one tooltip shows, neighbors show with no wait | **Corrected** in degree: Windows shows them after a much shorter reshow delay (100 ms), not zero | Microsoft Learn |

## Inference

| Claim | Status | Source |
|---|---|---|
| Triangle from cursor to submenu corners keeps the submenu open while the user aims at it | Documented | Ben Kamens, "Breaking down Amazon's mega dropdown" (2013); `kamens/jQuery-menu-aim` source |
| The triangle was "first documented in 2013 by Ben Kamens" | **Corrected.** Kamens himself writes that the problem was surely "solved years and years ago". Commenters and a 2013 Qt mailing-list thread credit Bruce Tognazzini and Jim Batson at Apple, 1986. That attribution is secondhand and unverified, but the 2013 date is certainly not the origin | Kamens; Qt interest list, May 2013 |
| Speed matters: move too slowly and the menu switches | Consistent with the reference implementation, which re-checks after 300 ms and switches if the pointer has stopped. The speaker's description of Linear, Notion and Attio is his own observation | `jquery.menu-aim.js` (`DELAY = 300`, `tolerance: 75`, 3 tracked points) |
| Ohio State paved students' desire paths (1914) | Analogy only, left out of the skill. Accounts date the Oval paving to the 1920s, and the page the video links is a 2025 art exhibition statement, not a history | uas.osu.edu "Desire Lines"; secondary accounts |
| The only way to get better at guessing intent is to study great products | Speaker's opinion. The skill adds measuring your own users' behavior (instrumentation, recordings, usability tests) as the stronger evidence | — |

## Acting first, undo, confirmation

| Claim | Status | Source |
|---|---|---|
| Habituation makes warnings fail; prefer undo ("never use a warning when you mean undo") | Expert consensus, widely cited | Aza Raskin, *A List Apart* (2007), building on Jef Raskin, *The Humane Interface* |
| Bare "Are you sure?" gives no protection; use confirmation for serious, irreversible or costly actions; offer undo where possible | Expert consensus | NN/g, "Confirmation Dialogs Can Prevent User Errors (If Not Overused)" |
| A modal makes "99%" confirm what they meant to protect "1%" | Speaker's rhetoric, not a measured ratio | Video |
| Gmail delays sending and shows "sent" so it can offer undo | Documented: default 5 s, configurable 5/10/20/30 s; it delays rather than recalls | Google Gmail help and university IT guides |
| Undo is hard on shared data and for time-sensitive sends; retention has privacy cost | Practitioner caveats | Comments on Raskin's article; optimistic-UI practitioner writing |
| No controlled study compares undo with confirmation directly | Noted gap — the preference for undo rests on expert consensus | — |
| Settings that save instantly and editors without Save have become common; version history replaces Save/Cancel | Speaker's observation of industry trend; consistent with practice but not quantified | Video |

## Commitment

| Claim | Status | Source |
|---|---|---|
| Buttons fire on release; pressing and sliding off cancels | Documented as an accessibility requirement | WCAG 2.2 SC 2.5.2 Pointer Cancellation (Level A) |
| Menus open on press so press-drag-release selects in one motion | Documented as classic Mac behavior; both press-drag-release and click-click must work | Mac OS X references; Mozilla bug 101472 discussion. WCAG 2.5.2 permits down-event actions that the up-event reverses |
| Threshold gestures (pull to refresh, swipe to delete) show progress and can be reversed before commit | Common platform practice | Platform conventions |
| Cmd-Tab: commit on release, Escape cancels | Documented macOS behavior | macOS |

## Accessibility additions (not in the video)

- WCAG 2.5.1 Pointer Gestures: path-based or multipoint gestures need a single-pointer alternative.
- WCAG 2.5.7 Dragging Movements (2.2, AA): dragging needs a non-drag alternative.
- WCAG 1.4.13 Content on Hover or Focus: hover content must be dismissible, hoverable and persistent.
- WCAG 2.2.1 Timing Adjustable: time limits must be adjustable, which applies by analogy to undo windows.
- Hover-based inference does nothing on touch screens and is invisible to keyboard users.
