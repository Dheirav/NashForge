# Season 6 of the Chipzen arena, 15 to 20 September 2026: the record

NashForge won it. This page exists so that claim can be checked by someone who does not
take this repository's word for it. Chipzen's data sits behind a free login, so the
checkable things are: the platform's own pages, reproduced here as screenshots taken from
the logged-in dashboard on 21 September 2026; the identifiers of the bot and of the three
playoff matches, which the platform's match pages resolve for any logged-in user; and the
per-match records under `results/chipzen/ledger.md`, which are derived from the bot's own
logs and agree with the platform's pages hand for hand.

## What the platform shows

**The champion card** on the dashboard after the final (`champion-card.png`): "Season 6 ·
Finished · Champion NASHFORGE · Built by crimsy · Won the final vs Fold-ver-3", with the
podium (2 Fold-ver-3, 3 v003 and Blueprint) and the first prize.

**The bracket** (`bracket.png`): quarter-finals NashForge over mellyy, v003 over wsp,
Blueprint over PoetAndCoder, Fold-ver-3 over Shadow; semi-finals NashForge over v003,
Fold-ver-3 over Blueprint; final NashForge over Fold-ver-3, marked Champion.

**The standings** (`standings.png`): NashForge first at 8 played, 7 won, 1 lost. The loss is
a round-robin walkover on 17 September, a timer bug on my side; the bot won every match it
played.

## Identifiers

| what | value |
|---|---|
| the bot | `NashForge`, owner `crimsy`, bot id `29e73b2b-d349-4c60-b3d0-e9ddae8ae0f6`, remote (external API) track |
| the season | `chipzen.ai/season/6` |
| quarter-final, 19 Sep 23:30 IST, vs mellyy, 32 hands | match `259066b0-6b78-4aa2-a471-76dc1b8d5f03` |
| semi-final, 20 Sep 23:30 IST, vs v003, 22 hands | match `28af397b-89c3-413f-8d4d-17061cfd10dc` |
| final, 21 Sep 02:30 IST, vs Fold-ver-3, 67 hands | match `c27d352d-ee11-40b0-8f66-29a36344448f` |

Each match id resolves at `chipzen.ai/api/matches/<id>` for a logged-in user (the record
names both bots, the seats, the net chips and the hands won; NashForge is +10,000 in all
three), and at the platform's match viewer with a replay of every hand, hole cards shown.

## What the repository adds

`results/chipzen/ledger.md` has every rated match by version, with hands, net chips and
showdowns, computed from the bot's own per-decision logs; the season's three playoff lines
are the last entries under the `v7b` labels. The set that played the playoffs is
`results/cfr/ladder169l_v5c` with the one-raise primary (the composition is in the tree; the
solved strategies are not). The decision logs themselves are not published, because they
are the bot's play, but their totals are the ledger.
