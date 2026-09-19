# Replay: results/cfr/ladder169l_v7 on the logged hands

1438 decisions from 1121 hands (matches labelled v6*); baseline results/cfr/ladder169l_v6.

## Coverage

logged misses 33, baseline lookup misses 32 (these should match), new-set misses 54 after its cap-2 companions answered 131 of the primary's 185; 1384 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 861 | 0.58 | 0.35 | 493 (57%) |
| flop | 291 | 0.60 | 0.51 | 67 (23%) |
| turn | 145 | 0.64 | 0.46 | 70 (48%) |
| river | 87 | 0.70 | 0.58 | 27 (31%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 210
- check/call → raise pot: 97
- raise ½ → raise pot: 74
- fold → check/call: 43
- check/call → raise 2×: 40
- raise ½ → raise 2×: 35
- raise ½ → check/call: 28
- raise pot → raise ½: 28

## Calls of a bet of the pot or more

14 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 73 | preflop | 6d 6c | - | 18,050 | 18,650 | 1.00 | 1.00 |
| 60 | preflop | 6d Kd | - | 16,950 | 17,350 | 0.96 | 0.93 |
| 101 | preflop | Kh 4d | - | 16,300 | 17,500 | 1.00 | 1.00 |
| 70 | preflop | Ad 9c | - | 15,975 | 16,575 | 1.00 | 1.00 |
| 75 | preflop | Kc Qc | - | 14,000 | 14,600 | 0.86 | 0.01 |
| 123 | preflop | As 4h | - | 13,800 | 15,400 | 1.00 | 1.00 |
| 87 | preflop | 7d 7h | - | 13,550 | 14,350 | 1.00 | 1.00 |
| 117 | preflop | Ah As | - | 13,500 | 14,700 | 1.00 | 1.00 |
| 61 | preflop | Js As | - | 12,000 | 12,600 | 1.00 | 0.74 |
| 43 | preflop | Qs Qc | - | 11,775 | 12,175 | 1.00 | 1.00 |
| 12 | river | 7h Th | 7d 5s 3d Tc 5c | 10,100 | 13,100 | 1.00 | 1.00 |
| 19 | preflop | Kd Kh | - | 9,300 | 9,500 | 1.00 | 1.00 |
| 24 | preflop | Th Td | - | 8,300 | 8,900 | 1.00 | 1.00 |
| 5 | preflop | Kh Qh | - | 500 | 900 | 1.00 | 1.00 |

Mean call probability over all 14: baseline 0.99, new 0.91.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|
| 38 | preflop | 8d Jd | - | 13,400 | 14,000 | fold | 50bb: fold 1.00 | fold 1.00 |
| 42 | preflop | 8s 4d | - | 13,275 | 14,075 | fold | 50bb: fold 1.00 | fold 1.00 |
| 38 | preflop | 5s 2c | - | 13,125 | 13,725 | fold | 50bb: fold 0.05, check/call 0.95 | fold 0.05, check/call 0.95 |
| 55 | preflop | 2d 9h | - | 11,725 | 12,525 | fold | 50bb: fold 0.85, check/call 0.15 | fold 0.11, check/call 0.89 |
| 35 | preflop | Js 7d | - | 11,550 | 12,150 | fold | 50bb: fold 1.00 | fold 1.00 |
| 30 | preflop | 2d 5s | - | 11,550 | 12,150 | fold | 50bb: fold 0.05, check/call 0.95 | fold 0.05, check/call 0.95 |
| 49 | river | Ad 4h | 3c 9d Jc 5s 5c | 11,500 | 15,500 | fold | 50bb: fold 0.96 | fold 0.85, check/call 0.15 |
| 51 | preflop | 6s 2s | - | 11,500 | 12,300 | fold | 50bb: fold 1.00 | fold 0.99 |
| 63 | preflop | Kd Jh | - | 10,750 | 11,950 | fold | 50bb: fold 1.00 | check/call 1.00 |
| 31 | preflop | 4h Ac | - | 10,675 | 11,575 | fold | 70bb: fold 1.00 | fold 1.00 |
| 34 | preflop | 4c 8h | - | 10,575 | 11,175 | fold | 70bb: fold 1.00 | fold 1.00 |
| 23 | preflop | 8s 8d | - | 10,525 | 11,125 | fold | 70bb: fold 0.08, check/call 0.92 | fold 0.08, check/call 0.92 |
| 11 | turn | 4s 5h | Kd Th 9c 9d | 10,500 | 10,900 | fold | 100bb: fold 1.00 | fold 1.00 |
| 34 | turn | 7d Kc | Tc 3c 2h 4c | 10,225 | 13,925 | fold | 50bb: fold 0.99 | fold 0.99 |
| 24 | preflop | Kh 9s | - | 10,125 | 10,725 | fold | 70bb: fold 1.00 | fold 1.00 |
| 12 | river | 7h Th | 7d 5s 3d Tc 5c | 10,100 | 13,100 | check/call | 100bb: check/call 1.00 | check/call 1.00 |
| 16 | preflop | 5s Ts | - | 10,000 | 10,400 | fold | 100bb: fold 1.00 | fold 1.00 |
| 26 | preflop | Ad 8s | - | 9,850 | 10,450 | fold | 70bb: fold 1.00 | fold 1.00 |
| 11 | preflop | 2c 4c | - | 9,800 | 10,800 | fold | 100bb: fold 1.00 | fold 1.00 |
| 3 | preflop | 5d 6c | - | 9,700 | 10,300 | fold | 100bb: fold 1.00 | fold 1.00 |
| 4 | preflop | 2s 5s | - | 9,650 | 10,650 | fold | 100bb: fold 1.00 | fold 1.00 |
| 4 | preflop | 8s Qh | - | 9,650 | 10,050 | fold | 100bb: fold 1.00 | fold 1.00 |
| 12 | preflop | As 4c | - | 9,650 | 10,050 | fold | 100bb: fold 1.00 | fold 1.00 |
| 33 | preflop | 7c Td | - | 9,625 | 10,225 | fold | 70bb: fold 1.00 | fold 1.00 |
| 5 | preflop | 5h Th | - | 9,500 | 10,500 | fold | 100bb: fold 1.00 | fold 1.00 |

Facing a bet of the pot or more on those lines (50): the companion calls with mean probability 0.24 and folds with 0.76.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs Blueprint**, hand 21 (25ad0f1b), we held Ts Td, they showed Ks Kh.
  - preflop board -              key `3` to call 300 → played **raise 2×**; new set: check/call 1.00
  - preflop board -              key `345` to call 7,750 → played **check/call**; new set: no entry

**-9,700 vs Blueprint**, hand 11 (8f880777), we held Js Jh, they showed Ah Ac.
  - preflop board -              key `4` to call 300 → played **all-in**; new set: check/call 1.00

**-9,600 vs Blueprint**, hand 80 (250b315e), we held Qd 7h, they showed Ah 8h.
  - preflop board -              key `` to call 150 → played **check/call**; new set: check/call 0.01, raise ½ 0.24, raise pot 0.65, raise 2× 0.10
  - flop    board As 5h 8s       key `11/1` to call 0 → played **raise ½**; new set: check/call 0.52, raise ½ 0.43, raise pot 0.03, raise 2× 0.02
  - flop    board As 5h 8s       key `11/122` to call 300 → played **check/call**; new set: fold 0.09, check/call 0.91
  - turn    board As 5h 8s 7d    key `11/1221/1` to call 0 → played **check/call**; new set: check/call 0.98, raise ½ 0.02
  - river   board As 5h 8s 7d Qs key `11/1221/11/1` to call 0 → played **raise 2×**; new set: raise ½ 0.31, raise pot 0.15, raise 2× 0.51, all-in 0.03
  - river   board As 5h 8s 7d Qs key `11/1221/11/145` to call 5,900 → played **check/call**; new set: check/call 1.00

**-9,425 vs Blueprint**, hand 26 (de569b42), we held 4s 4h, they showed Qd Qs.
  - preflop board -              key `3` to call 300 → played **all-in**; new set: check/call 1.00

**-8,875 vs Blueprint**, hand 55 (2bcaac39), we held Kd Th, they showed 2c Ac.
  - preflop board -              key `` to call 100 → played **raise ½**; new set: raise ½ 0.18, raise pot 0.68, raise 2× 0.14
  - flop    board Kc Tc 9c       key `21/1` to call 0 → played **raise ½**; new set: check/call 0.12, raise ½ 0.21, raise pot 0.54, raise 2× 0.12, all-in 0.01
  - flop    board Kc Tc 9c       key `21/122` to call 400 → played **check/call**; new set: check/call 1.00
  - turn    board Kc Tc 9c 4s    key `21/1221/1` to call 0 → played **raise ½**; new set: check/call 0.11, raise ½ 0.72, raise pot 0.15, raise 2× 0.02
  - turn    board Kc Tc 9c 4s    key `21/1221/122` to call 1,300 → played **check/call**; new set: check/call 1.00
  - river   board Kc Tc 9c 4s Js key `21/1221/1221/5` to call 5,175 → played **check/call**; new set: fold 0.06, check/call 0.94

**-8,800 vs Blueprint**, hand 129 (52c6dea7), we held Ac 6s, they showed Qs Jd.
  - preflop board -              key `2` to call 800 → played **all-in**; new set: check/call 1.00

**-8,750 vs Blueprint**, hand 74 (93ed0bc2), we held Qc 5c, they showed Qh Jd.
  - preflop board -              key `2` to call 300 → played **check/call**; new set: check/call 1.00
  - flop    board Qs Ah 5d       key `21/` to call 0 → played **check/call**; new set: check/call 0.58, raise ½ 0.27, raise pot 0.14, raise 2× 0.01
  - flop    board Qs Ah 5d       key `21/12` to call 300 → played **raise ½**; new set: check/call 1.00
  - flop    board Qs Ah 5d       key `21/1225` to call 9,450 → played **check/call**; new set: no entry

**-8,400 vs Blueprint**, hand 12 (0d6469b1), we held 7h Th, they showed 3s 5h.
  - preflop board -              key `` to call 50 → played **check/call**; new set: raise ½ 0.24, raise pot 0.14, raise 2× 0.62
  - flop    board 7d 5s 3d       key `11/2` to call 100 → played **check/call**; new set: check/call 1.00
  - turn    board 7d 5s 3d Tc    key `11/21/2` to call 100 → played **check/call**; new set: check/call 1.00
  - river   board 7d 5s 3d Tc 5c key `11/21/21/1` to call 0 → played **raise 2×**; new set: raise pot 0.74, raise 2× 0.21, all-in 0.05
  - river   board 7d 5s 3d Tc 5c key `11/21/21/145` to call 10,100 → played **check/call**; new set: check/call 1.00

