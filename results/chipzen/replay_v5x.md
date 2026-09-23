# Replay: results/cfr/ladder169l_v5x on the logged hands

26682 decisions from 16731 hands; baseline results/cfr/ladder169l_v5i.

## Coverage

logged misses 1361, baseline lookup misses 1042 (these should match), new-set misses 1154 after its cap-2 companions answered 0 of the primary's 1154; 25491 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 13238 | 0.46 | 0.44 | 5025 (38%) |
| flop | 6034 | 0.59 | 0.59 | 1254 (21%) |
| turn | 3666 | 0.55 | 0.56 | 1464 (40%) |
| river | 2553 | 0.58 | 0.58 | 812 (32%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 3009
- raise ½ → check/call: 1283
- fold → check/call: 1003
- raise pot → raise ½: 977
- raise pot → check/call: 438
- check/call → raise pot: 320
- check/call → fold: 293
- raise 2× → check/call: 271

## Calls of a bet of the pot or more

296 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 16 | preflop | Qs 6c | - | 19,700 | 19,900 | 1.00 | 1.00 |
| 6 | preflop | Ad 7s | - | 19,500 | 19,700 | 1.00 | 1.00 |
| 38 | preflop | 7c Jc | - | 19,179 | 19,479 | 1.00 | 1.00 |
| 38 | preflop | 3h Th | - | 19,116 | 19,416 | 0.43 | 0.43 |
| 8 | preflop | 5c Tc | - | 19,000 | 19,200 | 0.72 | 0.72 |
| 18 | preflop | Jc 8s | - | 18,988 | 19,188 | 0.40 | 0.40 |
| 48 | preflop | Qh 2s | - | 18,808 | 19,208 | 0.99 | 0.99 |
| 48 | preflop | 9d Jh | - | 18,664 | 19,064 | 1.00 | 1.00 |
| 112 | preflop | Ts 7c | - | 18,550 | 19,750 | 1.00 | 1.00 |
| 56 | preflop | 8d 8c | - | 18,394 | 18,794 | 1.00 | 1.00 |
| 32 | preflop | Ac Ah | - | 18,250 | 18,550 | 1.00 | 1.00 |
| 68 | preflop | 6s Ah | - | 18,250 | 18,850 | 1.00 | 1.00 |
| 87 | preflop | Qd 9s | - | 18,250 | 19,050 | 1.00 | 1.00 |
| 73 | preflop | 6d 6c | - | 18,050 | 18,650 | 1.00 | 1.00 |
| 21 | river | Qd Jh | Jd 5d 8s 2d 6c | 18,018 | 19,218 | 1.00 | 1.00 |
| 50 | preflop | Ah Ac | - | 18,016 | 18,416 | 1.00 | 1.00 |
| 52 | flop | 8s As | 6d 3s 7c | 17,850 | 19,050 | 1.00 | 1.00 |
| 30 | preflop | 6c 6s | - | 17,725 | 18,025 | 1.00 | 1.00 |
| 86 | flop | 2s Td | Ac Tc 7d | 17,500 | 19,100 | 1.00 | 1.00 |
| 78 | preflop | 8c Th | - | 17,464 | 18,064 | 0.76 | 0.76 |

Mean call probability over all 296: baseline 0.75, new 0.77.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs hoops**, hand 1 (0b7e2f73), we held 9h Qs, they showed Kd Ks.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.01, raise ½ 0.99
  - preflop board -              key `25` to call 340 → played **check/call**; new set: fold 1.00
  - flop    board As 7s 2h       key `251/3` to call 610 → played **check/call**; new set: no entry
  - turn    board As 7s 2h 6d    key `251/21/1` to call 0 → played **raise ½**; new set: no entry
  - river   board As 7s 2h 6d 4c key `251/21/121/1` to call 0 → played **all-in**; new set: no entry

**-10,000 vs Blueprint**, hand 21 (25ad0f1b), we held Ts Td, they showed Ks Kh.
  - preflop board -              key `3` to call 300 → played **raise 2×**; new set: raise 2× 1.00
  - preflop board -              key `345` to call 7,750 → played **check/call**; new set: check/call 1.00

**-10,000 vs Blueprint**, hand 1 (7ab8614e), we held 7h Js, they showed Qh 5h.
  - preflop board -              key `` to call 50 → played **raise pot**; new set: check/call 0.02, raise ½ 0.92, raise pot 0.06
  - flop    board Tc 8h 2h       key `31/1` to call 0 → played **raise pot**; new set: raise ½ 0.90, raise pot 0.08, raise 2× 0.02
  - turn    board Tc 8h 2h 9h    key `31/131/2` to call 1,350 → played **check/call**; new set: check/call 1.00
  - river   board Tc 8h 2h 9h As key `31/131/31/5` to call 7,750 → played **check/call**; new set: check/call 1.00

**-10,000 vs Blueprint**, hand 11 (daa4c270), we held Kh Kc, they showed 8c 8s.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: check/call 0.01, raise ½ 0.94, raise pot 0.05
  - preflop board -              key `45` to call 9,500 → played **check/call**; new set: check/call 1.00

**-9,950 vs Blueprint**, hand 7 (cebbe08d), we held Qh Qs, they showed Kh As.
  - preflop board -              key `5` to call 9,950 → played **check/call**; new set: check/call 1.00

**-9,933 vs hoops**, hand 17 (13fbf84a), we held Th Kh, they showed Qh Qc.
  - preflop board -              key `` to call 50 → played **raise pot**; new set: check/call 0.01, raise ½ 0.99
  - preflop board -              key `35` to call 580 → played **check/call**; new set: fold 0.28, check/call 0.72
  - flop    board Tc 6d Ts       key `351/2` to call 1,046 → played **all-in**; new set: no entry

**-9,925 vs Blueprint**, hand 33 (507aa7aa), we held Qs Kh, they showed Js Jd.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.02, raise ½ 0.89, raise pot 0.09
  - preflop board -              key `15` to call 9,775 → played **check/call**; new set: fold 0.85, check/call 0.15

**-9,900 vs Blueprint**, hand 4 (4e1b0b4e), we held Jd Ts, they showed Kd Qh.
  - preflop board -              key `3` to call 200 → played **raise ½**; new set: check/call 1.00
  - preflop board -              key `325` to call 650 → played **check/call**; new set: no entry
  - flop    board Tc 7d Qs       key `3251/` to call 0 → played **raise pot**; new set: no entry
  - flop    board Tc 7d Qs       key `3251/35` to call 6,150 → played **check/call**; new set: no entry

