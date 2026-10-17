# Office Week Planner — project instructions

## Purpose
Decide each week which two days the user rides his motorbike (Honda CB600 Hornet) to the office from
's-Hertogenbosch, so that both rides are dry, not too windy and above freezing, and recommend the
time to leave home and the time to leave the office. On other days the NS train is the fallback.
Two office days a week are mandatory; the user is free to choose which.

## Routes (routes.json)
- Vathorst — Stater, Amersfoort Vathorst. 75 min via A2/A27/A28. Scan points: 's-Hertogenbosch 0,
  Zaltbommel +15, Culemborg +30, Utrecht +45, Zeist/Den Dolder +60, Amersfoort Vathorst +75 min.
- Eindhoven — 40 min via A2. Scan points: 's-Hertogenbosch 0, Vught +10, Boxtel +20, Best +30, Eindhoven +40.
- More routes can be added by editing routes.json (name, short, rideMinutes, via, ns text, waypoints
  with lat/lon and minutes after departure). The planner page shows a tab per route.

## Rules (routes.json → rules)
- Fit to ride at a point: 0 mm rain, wind ≤ 25 km/h, gusts ≤ 40 km/h (when published), temperature > 0 °C.
- Moving scan: each waypoint is checked at the 15-minute slot you pass it; evening ride in reverse order.
- Morning: leave between 06:00 and the latest departure that arrives before 09:15 (15-min steps).
  The latest clean departure is recommended; earlier only to stay dry.
- Shift: 8.5 h from arrival. Evening: from arrival + 8.5 h to 20:00; the earliest clean departure is recommended.
- Motorbike day = clean morning ride + matching clean evening ride. Otherwise train day.
- Week plan: the first two motorbike days of the remaining week; past days are skipped.

## Pieces and where they live
- Planner page (Claude artifact): https://claude.ai/artifact/USbR3ybajjfqUcburFLdHt
  Files published with it: index.html, routes.json, data.json. The page reads the two JSON files.
  Status strip at the top shows when the forecast was generated; lamp green = fresh (< 2.5 days), red = stale.
  "Update forecast now" button starts the Claude scheduled task (owner only).
- GitHub: https://github.com/analluran-alt/office-planner (public). A GitHub Action runs
  fetch_forecast.py every 3 hours and commits data.json (Open-Meteo, 15-minute resolution, free, no key).
  Raw data: https://raw.githubusercontent.com/analluran-alt/office-planner/main/data.json
  Manual run: Actions → Fetch forecast → Run workflow.
- Claude scheduled task "Office planner: publish forecast": Sunday, Tuesday and Thursday 20:30
  (Europe/Amsterdam). Downloads data.json from GitHub, publishes it to the artifact, reports the plan per route.
- Local project folder on the laptop "r21": C:\Users\anall\OneDrive\Documents\__R21\_R21 Weekplanner
  (copy of the repo files; edit routes.json here and ask Claude to push it).
- NS fallback (checked on ns.nl 17 Oct 2026): 's-Hertogenbosch 08:20 → Utrecht Centraal 08:46,
  change 5 min, Sprinter 08:51 → Amersfoort Vathorst 09:19 (pattern :20 and :50 each hour; earlier 07:50 → 08:49).

## Known limits
- Forecasts beyond ~2 days change; the Tuesday and Thursday runs exist to catch that.
- Open-Meteo gives 15-minute data for about the first 2–3 days, hourly beyond; the page uses whatever slot is there.
- The Claude cloud environment and the laptop shell cannot call weather APIs directly (network allowlist);
  that is why GitHub does the fetching.
- Later goal: host the page on reflow21.com so it can read data.json from GitHub directly without the Claude task.

## Working agreements with Claude
- Ask clarifying questions before detailed work; the user is new to coding, thinks in A3 / root cause.
- Keep index.html, routes.json and data.json in sync between the artifact, the GitHub repo and the local folder.
- Never invent forecast numbers; say when data is missing or stale.
