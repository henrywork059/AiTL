# PC Studio GUI Layout — V022 candidate

The established sidebar + page-content layout is retained. V022 extends existing Live AI, Zone Editor, Traffic Logic, and Traffic Analytics surfaces rather than adding another top-level page.

## Live AI

- camera/simulation image remains the canonical visual source;
- trained-model boxes/labels remain optional;
- supported traffic detections now show `track_id` beside class/confidence;
- saved polygon zones remain overlaid;
- two-point counting lines are drawn as dashed line overlays;
- signal-aware simulation overlay remains synchronized to the synthetic agents.

## Zone Editor

Existing polygon types remain unchanged. New `counting_line` geometry:

- choose `counting line` in Type;
- click exactly two distinct points;
- line uses the same 1280×720 reference coordinate system;
- line is analytics-only and never changes simulated traffic phase logic.

`counting_region` remains a polygon and continues to provide occupancy analytics; V022 additionally derives entry/exit/dwell from tracked movement through polygon regions.

## Traffic Logic

The current traffic state continues to display occupancy/decision information and now also surfaces active track counts. Counting-line flow remains analytics-only.

## Traffic Analytics

Two explicit modes prevent semantic mixing:

### Occupancy
- existing V021 whole-frame/region time series;
- current/average/peak/busiest-region metrics;
- phase-change context;
- occupancy CSV and independent clear action.

### Flow / Tracks
- selectable all events, one counting line, or one polygon region;
- optional class filter;
- unique tracked vehicle/pedestrian passages per minute for line scopes;
- entry/exit per minute for region scopes;
- directional passage totals;
- region entry/exit and dwell metrics;
- pedestrian waiting-zone dwell;
- recent event table;
- flow CSV and independent clear action.

## Safety presentation

Tracking and flow are labelled as prototype analytics. No page implies direct physical/public-road traffic-light control.
