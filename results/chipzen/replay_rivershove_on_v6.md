# Replay: results/cfr/ladder169l_v5c on the logged hands

1438 decisions from 1121 hands (matches labelled v6*); baseline results/cfr/ladder169l_v6.

## Coverage

logged misses 33, baseline lookup misses 32 (these should match), new-set misses 31 after its cap-2 companions answered 154 of the primary's 185; 1406 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 873 | 0.58 | 0.36 | 499 (57%) |
| flop | 296 | 0.60 | 0.52 | 68 (23%) |
| turn | 148 | 0.64 | 0.47 | 72 (49%) |
| river | 89 | 0.69 | 0.58 | 30 (34%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 209
- check/call → raise pot: 97
- raise ½ → raise pot: 75
- fold → check/call: 43
- check/call → raise 2×: 40
- raise ½ → raise 2×: 35
- raise ½ → check/call: 29
- raise pot → raise ½: 28

## Calls of a bet of the pot or more

20 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 73 | preflop | 6d 6c | - | 18,050 | 18,650 | 1.00 | 1.00 |
| 60 | preflop | 6d Kd | - | 16,950 | 17,350 | 0.96 | 0.93 |
| 101 | preflop | Kh 4d | - | 16,300 | 17,500 | 1.00 | 1.00 |
| 73 | preflop | 2c 8h | - | 16,200 | 17,400 | 0.96 | 0.50 |
| 70 | preflop | Ad 9c | - | 15,975 | 16,575 | 1.00 | 1.00 |
| 75 | preflop | Kc Qc | - | 14,000 | 14,600 | 0.86 | 0.01 |
| 123 | preflop | As 4h | - | 13,800 | 15,400 | 1.00 | 1.00 |
| 87 | preflop | 7d 7h | - | 13,550 | 14,350 | 1.00 | 1.00 |
| 92 | preflop | Ks Td | - | 13,500 | 15,100 | 1.00 | 1.00 |
| 117 | preflop | Ah As | - | 13,500 | 14,700 | 1.00 | 1.00 |
| 61 | preflop | Js As | - | 12,000 | 12,600 | 1.00 | 0.74 |
| 43 | preflop | Qs Qc | - | 11,775 | 12,175 | 1.00 | 1.00 |
| 85 | turn | 4c Ks | Kh 6h 7h 9d | 11,300 | 15,300 | 0.96 | 0.37 |
| 12 | river | 7h Th | 7d 5s 3d Tc 5c | 10,100 | 13,100 | 1.00 | 1.00 |
| 19 | preflop | Kd Kh | - | 9,300 | 9,500 | 1.00 | 1.00 |
| 24 | preflop | Th Td | - | 8,300 | 8,900 | 1.00 | 1.00 |
| 71 | flop | 7h Kc | Th 7d 8s | 4,200 | 7,500 | 1.00 | 0.95 |
| 66 | preflop | As 4d | - | 4,100 | 7,100 | 1.00 | 1.00 |
| 44 | flop | As Qc | Kc Qh Kd | 3,550 | 4,350 | 1.00 | 1.00 |
| 5 | preflop | Kh Qh | - | 500 | 900 | 1.00 | 1.00 |

Mean call probability over all 20: baseline 0.99, new 0.87.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|
| 73 | preflop | 2c 8h | - | 16,200 | 17,400 | check/call | 12bb: fold 0.50, check/call 0.50 | check/call 0.96 |
| 100 | preflop | 4c Qd | - | 15,300 | 16,900 | fold | 12bb: fold 1.00 | fold 0.86, check/call 0.14 |
| 50 | flop | 3s 2d | Tc Qd 9c | 14,600 | 16,400 | fold | 25bb: fold 1.00 | fold 1.00 |
| 92 | preflop | Ks Td | - | 13,500 | 15,100 | check/call | 12bb: check/call 1.00 | check/call 1.00 |
| 38 | preflop | 8d Jd | - | 13,400 | 14,000 | fold | 50bb: fold 0.98 | fold 1.00 |
| 94 | preflop | 9h Js | - | 13,300 | 14,900 | fold | 18bb: fold 1.00 | fold 1.00 |
| 42 | preflop | 8s 4d | - | 13,275 | 14,075 | fold | 35bb: fold 1.00 | fold 1.00 |
| 69 | river | Jc 5d | 3h Js Qd 3d Qs | 13,275 | 16,275 | fold | 18bb: fold 0.67, check/call 0.33 | fold 0.66, check/call 0.34 |
| 38 | preflop | 5s 2c | - | 13,125 | 13,725 | fold | 50bb: fold 1.00 | fold 0.05, check/call 0.95 |
| 67 | flop | Jc 7c | Qs 9c 6h | 11,950 | 14,650 | fold | 25bb: fold 1.00 | fold 1.00 |
| 55 | preflop | 2d 9h | - | 11,725 | 12,525 | fold | 35bb: fold 1.00 | fold 0.11, check/call 0.89 |
| 35 | preflop | Js 7d | - | 11,550 | 12,150 | fold | 50bb: fold 1.00 | fold 1.00 |
| 30 | preflop | 2d 5s | - | 11,550 | 12,150 | fold | 50bb: fold 1.00 | fold 0.05, check/call 0.95 |
| 49 | river | Ad 4h | 3c 9d Jc 5s 5c | 11,500 | 15,500 | fold | 35bb: fold 0.93, check/call 0.07 | fold 0.85, check/call 0.15 |
| 51 | preflop | 6s 2s | - | 11,500 | 12,300 | fold | 35bb: fold 1.00 | fold 0.99 |
| 122 | preflop | 4d 9s | - | 11,400 | 14,600 | fold | 12bb: fold 0.50, check/call 0.50 | no entry |
| 85 | turn | 4c Ks | Kh 6h 7h 9d | 11,300 | 15,300 | check/call | 18bb: fold 0.63, check/call 0.37 | check/call 0.96 |
| 63 | preflop | Kd Jh | - | 10,750 | 11,950 | fold | 25bb: fold 0.72, check/call 0.28 | check/call 1.00 |
| 31 | preflop | 4h Ac | - | 10,675 | 11,575 | fold | 70bb: fold 1.00 | fold 1.00 |
| 34 | preflop | 4c 8h | - | 10,575 | 11,175 | fold | 70bb: fold 1.00 | fold 1.00 |
| 23 | preflop | 8s 8d | - | 10,525 | 11,125 | fold | 70bb: check/call 1.00 | fold 0.08, check/call 0.92 |
| 11 | turn | 4s 5h | Kd Th 9c 9d | 10,500 | 10,900 | fold | 100bb: fold 1.00 | fold 1.00 |
| 34 | turn | 7d Kc | Tc 3c 2h 4c | 10,225 | 13,925 | fold | 50bb: fold 1.00 | fold 0.99 |
| 24 | preflop | Kh 9s | - | 10,125 | 10,725 | fold | 70bb: fold 1.00 | fold 1.00 |
| 12 | river | 7h Th | 7d 5s 3d Tc 5c | 10,100 | 13,100 | check/call | 100bb: check/call 1.00 | check/call 1.00 |

Facing a bet of the pot or more on those lines (63): the companion calls with mean probability 0.28 and folds with 0.72.

## River shoves: the primary's answer against the companion's

9 river decisions faced an all-in with a primary node; the companion could answer 9. Net is the hand's result as played; a hand the companion would fold instead of calling loses only what was in before the shove.

| hand | ours | board | to call | pot | played | net | primary call | companion call |
|---|---|---|---|---|---|---|---|---|
| 69 | Jc 5d | 3h Js Qd 3d Qs | 13,275 | 16,275 | fold | -1,500 | 0.33 | 0.33 |
| 49 | Ad 4h | 3c 9d Jc 5s 5c | 11,500 | 15,500 | fold | -2,000 | 0.07 | 0.07 |
| 12 | 7h Th | 7d 5s 3d Tc 5c | 10,100 | 13,100 | check/call | -8,400 | 1.00 | 1.00 |
| 44 | 8s Jc | Qd 7h 7d 9d Kh | 8,525 | 11,525 | fold | -1,500 | 0.00 | 0.00 |
| 34 | 5d 5s | 3s 3c 7d Jc 3d | 7,450 | 15,950 | check/call | +8,300 | 0.46 | 0.46 |
| 28 | Qh 5h | Js 8h Kd Kc Kh | 7,100 | 7,700 | fold | -300 | 0.01 | 0.01 |
| 80 | Qd 7h | As 5h 8s 7d Qs | 5,900 | 14,900 | check/call | -9,600 | 1.00 | 1.00 |
| 29 | 4d Ad | 8d Tc 2s 3s Ks | 5,400 | 10,800 | fold | -2,700 | 0.00 | 0.00 |
| 55 | Kd Th | Kc Tc 9c 4s Js | 5,175 | 12,575 | check/call | -8,875 | 0.94 | 0.94 |

Calls that lost: -26,875 chips in total; of that, the companion would have folded calls worth +0 (the losing calls' own size where its call probability is under 0.5).

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
  - flop    board As 5h 8s       key `11/122` to call 300 → played **check/call**; new set: check/call 1.00
  - turn    board As 5h 8s 7d    key `11/1221/1` to call 0 → played **check/call**; new set: check/call 0.98, raise ½ 0.02
  - river   board As 5h 8s 7d Qs key `11/1221/11/1` to call 0 → played **raise 2×**; new set: raise ½ 0.17, raise pot 0.11, raise 2× 0.64, all-in 0.07
  - river   board As 5h 8s 7d Qs key `11/1221/11/145` to call 5,900 → played **check/call**; new set: check/call 1.00

**-9,425 vs Blueprint**, hand 26 (de569b42), we held 4s 4h, they showed Qd Qs.
  - preflop board -              key `3` to call 300 → played **all-in**; new set: check/call 1.00

**-8,875 vs Blueprint**, hand 55 (2bcaac39), we held Kd Th, they showed 2c Ac.
  - preflop board -              key `` to call 100 → played **raise ½**; new set: raise ½ 0.18, raise pot 0.68, raise 2× 0.14
  - flop    board Kc Tc 9c       key `21/1` to call 0 → played **raise ½**; new set: check/call 0.12, raise ½ 0.21, raise pot 0.54, raise 2× 0.12, all-in 0.01
  - flop    board Kc Tc 9c       key `21/122` to call 400 → played **check/call**; new set: check/call 1.00
  - turn    board Kc Tc 9c 4s    key `21/1221/1` to call 0 → played **raise ½**; new set: check/call 0.03, raise ½ 0.76, raise pot 0.21
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

