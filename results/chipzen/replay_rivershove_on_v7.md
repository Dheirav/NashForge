# Replay: results/cfr/ladder169l_v5c on the logged hands

3502 decisions from 2798 hands (matches labelled v7*); baseline results/cfr/ladder169l_v7.

## Coverage

logged misses 362, baseline lookup misses 362 (these should match), new-set misses 90 after its cap-2 companions answered 272 of the primary's 362; 3140 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 1977 | 0.59 | 0.59 | 0 (0%) |
| flop | 587 | 0.67 | 0.67 | 0 (0%) |
| turn | 342 | 0.62 | 0.62 | 0 (0%) |
| river | 234 | 0.70 | 0.69 | 2 (1%) |

Most common changes of most-likely action (baseline → new):

- check/call → fold: 1
- fold → check/call: 1

## Calls of a bet of the pot or more

39 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 56 | preflop | 8d 8c | - | 18,394 | 18,794 | 1.00 | 1.00 |
| 52 | flop | 8s As | 6d 3s 7c | 17,850 | 19,050 | 1.00 | 1.00 |
| 78 | preflop | 8c Th | - | 17,464 | 18,064 | 0.76 | 0.76 |
| 47 | preflop | 9s Qd | - | 17,050 | 17,450 | 0.20 | 0.20 |
| 83 | preflop | Ks 7h | - | 15,900 | 16,700 | 1.00 | 1.00 |
| 61 | preflop | 7c 5c | - | 15,800 | 16,400 | 0.72 | 0.72 |
| 21 | river | Qs 4s | Jc 9c Qc 9s 3d | 13,348 | 17,198 | 0.84 | 0.70 |
| 101 | preflop | 8s 8h | - | 12,050 | 13,250 | 1.00 | 1.00 |
| 42 | river | Ac As | Tc 3d Jd Kd 6s | 11,845 | 16,981 | 0.96 | 0.56 |
| 120 | flop | Ts 7s | 6s 9s Td | 11,150 | 13,550 | 1.00 | 1.00 |
| 112 | preflop | Jc Th | - | 9,925 | 11,125 | 0.38 | 0.38 |
| 104 | preflop | Kc Tc | - | 8,850 | 10,050 | 0.60 | 0.60 |
| 1 | river | 7h Js | Tc 8h 2h 9h As | 7,750 | 12,250 | 1.00 | 0.97 |
| 86 | river | Kd 3d | 3s Jc 8s 8h Qd | 6,350 | 9,550 | 0.53 | 0.14 |
| 98 | preflop | 5d 3d | - | 6,300 | 7,100 | 0.10 | 0.10 |
| 42 | river | 9d 8s | 9c 4d 3s Qs Qd | 6,300 | 7,900 | 1.00 | 1.00 |
| 105 | preflop | Kh Kc | - | 6,200 | 7,400 | 1.00 | 1.00 |
| 77 | preflop | 9d Kd | - | 5,525 | 6,125 | 0.60 | 0.60 |
| 67 | preflop | 9s Qh | - | 5,250 | 5,850 | 0.60 | 0.60 |
| 72 | preflop | Jh Ac | - | 5,225 | 5,825 | 1.00 | 1.00 |

Mean call probability over all 39: baseline 0.86, new 0.84.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|
| 36 | preflop | 6d Ac | - | 18,550 | 19,450 | check/call | 12bb: check/call 1.00 | no entry |
| 76 | preflop | 5s 6h | - | 15,650 | 17,450 | check/call | 12bb: fold 0.50, check/call 0.50 | no entry |
| 83 | preflop | 7c Kd | - | 14,800 | 17,200 | check/call | 12bb: check/call 0.99 | no entry |
| 82 | preflop | Td 5s | - | 14,700 | 16,300 | fold | 12bb: fold 1.00 | no entry |
| 33 | turn | 2h Kc | Th 8s 5c Ad | 14,575 | 18,775 | fold | 25bb: fold 0.50, check/call 0.50 | no entry |
| 62 | preflop | 7c 5s | - | 14,200 | 15,400 | fold | 18bb: fold 1.00 | no entry |
| 89 | preflop | 8d 2d | - | 14,100 | 16,500 | check/call | 12bb: fold 0.50, check/call 0.50 | no entry |
| 78 | preflop | 8s Ts | - | 13,750 | 15,550 | fold | 18bb: check/call 1.00 | no entry |
| 98 | preflop | 8d Kh | - | 13,675 | 15,275 | check/call | 12bb: fold 0.50, check/call 0.50 | no entry |
| 52 | preflop | Qh 8c | - | 13,500 | 14,300 | fold | 35bb: fold 1.00 | no entry |
| 56 | preflop | 4h Jh | - | 13,450 | 14,250 | fold | 35bb: fold 1.00 | no entry |
| 40 | preflop | Kh 9d | - | 13,375 | 14,275 | fold | 35bb: fold 0.83, check/call 0.17 | no entry |
| 46 | preflop | 4s Ts | - | 13,225 | 14,025 | fold | 35bb: fold 1.00 | no entry |
| 50 | preflop | 5d Kd | - | 13,225 | 14,025 | fold | 35bb: fold 1.00 | no entry |
| 44 | preflop | 3s 9h | - | 13,150 | 13,950 | fold | 35bb: fold 1.00 | no entry |
| 88 | preflop | Ad Kc | - | 13,100 | 17,100 | check/call | 12bb: check/call 1.00 | no entry |
| 32 | preflop | Qc Kd | - | 13,000 | 13,900 | fold | 50bb: fold 0.98 | no entry |
| 59 | preflop | 8h 2d | - | 12,900 | 13,700 | fold | 35bb: fold 0.43, check/call 0.57 | no entry |
| 88 | preflop | 9d 2s | - | 12,300 | 13,900 | check/call | 18bb: fold 1.00 | no entry |
| 66 | flop | 4h Kh | 3d 8s Ts | 12,250 | 15,850 | fold | 18bb: fold 1.00 | no entry |
| 52 | preflop | 8c Jd | - | 12,150 | 12,950 | fold | 35bb: fold 1.00 | no entry |
| 60 | preflop | 5c Qd | - | 12,000 | 12,800 | fold | 35bb: fold 1.00 | no entry |
| 89 | preflop | 9d Qh | - | 11,825 | 13,425 | fold | 18bb: fold 1.00 | no entry |
| 15 | preflop | 4h Jh | - | 11,750 | 12,350 | fold | 70bb: fold 1.00 | no entry |
| 60 | river | Qh 7h | 7c 3h 2d 5s Ts | 11,450 | 13,850 | fold | 35bb: fold 0.95, check/call 0.05 | no entry |

Facing a bet of the pot or more on those lines (181): the companion calls with mean probability 0.19 and folds with 0.81.

## River shoves: the primary's answer against the companion's

35 river decisions faced an all-in with a primary node; the companion could answer 35. Net is the hand's result as played; a hand the companion would fold instead of calling loses only what was in before the shove.

| hand | ours | board | to call | pot | played | net | primary call | companion call |
|---|---|---|---|---|---|---|---|---|
| 31 | Qd 8d | 6s 7c Kd Tc 5d | 14,825 | 16,825 | fold | -1,000 | 0.00 | 0.00 |
| 29 | 5d 5s | 2h 6c 9c 6s 3c | 13,975 | 15,975 | fold | -1,000 | 0.14 | 0.10 |
| 21 | Qs 4s | Jc 9c Qc 9s 3d | 13,348 | 17,198 | check/call | -4,727 | 0.84 | 0.70 |
| 42 | Ac As | Tc 3d Jd Kd 6s | 11,845 | 16,981 | check/call | -5,587 | 0.96 | 0.56 |
| 60 | Qh 7h | 7c 3h 2d 5s Ts | 11,450 | 13,850 | fold | -1,200 | 0.05 | 0.05 |
| 71 | 5h 5d | Tc 7h 2s Td Qs | 10,200 | 15,000 | fold | -2,400 | 0.10 | 0.10 |
| 31 | Th Td | 7h 4h 3s Kc 2s | 9,700 | 10,900 | fold | -600 | 0.00 | 0.00 |
| 78 | 9h 6c | Qc Qs 6s 5d Ts | 9,250 | 16,450 | fold | -3,600 | 0.43 | 0.43 |
| 25 | 9c 5d | Kh 2s 2c Ac Qc | 8,875 | 10,075 | fold | -600 | 0.00 | 0.00 |
| 73 | 9c Ac | 6d 8c Kd 3c 8d | 8,725 | 12,325 | fold | -1,800 | 0.03 | 0.00 |
| 78 | 7d Kd | Jh Jd Kh 3c 9d | 8,250 | 11,850 | fold | -1,800 | 0.19 | 0.19 |
| 34 | 7c Jc | 7s 6h 3c Js 5h | 8,030 | 14,270 | fold | -3,120 | 0.15 | 0.15 |
| 1 | 7h Js | Tc 8h 2h 9h As | 7,750 | 12,250 | check/call | -10,000 | 1.00 | 0.97 |
| 75 | 5c 7d | 4d Td 3d As 4c | 7,550 | 16,550 | fold | -4,500 | 0.00 | 0.00 |
| 75 | 4c Js | Jc 9c Kd 9h Qd | 7,350 | 11,750 | fold | -2,200 | 0.00 | 0.00 |
| 83 | 5d Js | Ah 2h 3s 6h Kd | 7,250 | 14,450 | fold | -3,600 | 0.00 | 0.00 |
| 46 | 6c Kh | Qs Jh 7c 7h 9s | 6,975 | 9,375 | fold | -1,200 | 0.00 | 0.00 |
| 47 | Qd Js | Ah Kd 2s Kh Th | 6,875 | 11,875 | check/call | -9,375 | 1.00 | 1.00 |
| 45 | Qd Qs | Td 6h 3d Qh Ts | 6,550 | 13,750 | check/call | +9,850 | 1.00 | 1.00 |
| 86 | Kd 3d | 3s Jc 8s 8h Qd | 6,350 | 9,550 | check/call | -7,950 | 0.53 | 0.14 |
| 42 | 9d 8s | 9c 4d 3s Qs Qd | 6,300 | 7,900 | check/call | -7,100 | 1.00 | 1.00 |
| 6 | Js Kd | 2s Qd Jd 5d 5c | 5,192 | 9,352 | fold | -2,080 | 0.01 | 0.01 |
| 38 | Ks 8d | 6h 6s 2d 8s 9h | 5,168 | 9,670 | check/call | -7,419 | 0.47 | 0.65 |
| 99 | 7c 6s | Jd 2s 5h Ad 3s | 5,050 | 13,050 | fold | -4,000 | 0.00 | 0.00 |
| 71 | Ah 9h | 8c Ac Kd 6h Qd | 4,483 | 13,409 | check/call | -8,946 | 1.00 | 1.00 |
| 47 | 9s Jc | 9d Qs 5s 8s 4c | 4,150 | 8,950 | fold | -2,400 | 0.29 | 0.29 |
| 4 | 4c Kd | Jc Ks Ts 4s Js | 4,080 | 8,080 | fold | -2,000 | 0.06 | 0.06 |
| 71 | 7c 8h | 6c 9c Th Qd Qh | 3,400 | 8,600 | check/call | -6,000 | 1.00 | 1.00 |
| 89 | Ks 3h | 9c Ts 4c 7d 5h | 3,075 | 15,075 | fold | -6,000 | 0.00 | 0.00 |
| 47 | 6d 5d | 3s Ad Kc 4h Kh | 2,575 | 10,575 | fold | -4,000 | 0.00 | 0.00 |
| 48 | Kd Ah | 8s 8d Qd 6d 9c | 2,449 | 6,933 | check/call | -4,691 | 0.49 | 0.10 |
| 18 | 3c 7s | Th 8h 4s Kd 8c | 1,450 | 3,450 | fold | -1,000 | 0.00 | 0.00 |
| 55 | Js 3s | 3d 8c 9s 5h Kh | 1,446 | 4,532 | fold | -1,543 | 0.07 | 0.37 |
| 61 | 2h Ac | Qd Qs 7s 4c 3c | 1,300 | 3,700 | fold | -1,200 | 0.00 | 0.00 |
| 37 | 9s Qd | 4h 6c 4c 5h 8h | 750 | 2,550 | fold | -900 | 0.00 | 0.00 |

Calls that lost: -71,795 chips in total; of that, the companion would have folded calls worth -3,842 (the losing calls' own size where its call probability is under 0.5).

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs Blueprint**, hand 1 (7ab8614e), we held 7h Js, they showed Qh 5h.
  - preflop board -              key `` to call 50 → played **raise pot**; new set: raise ½ 0.22, raise pot 0.64, raise 2× 0.14
  - flop    board Tc 8h 2h       key `31/1` to call 0 → played **raise pot**; new set: check/call 0.22, raise ½ 0.65, raise pot 0.13, raise 2× 0.01
  - turn    board Tc 8h 2h 9h    key `31/131/2` to call 1,350 → played **check/call**; new set: check/call 1.00
  - river   board Tc 8h 2h 9h As key `31/131/31/5` to call 7,750 → played **check/call**; new set: fold 0.03, check/call 0.97

**-9,475 vs Blueprint**, hand 112 (a2371738), we held Jc Th, they showed Ah Qs.
  - preflop board -              key `5` to call 9,925 → played **check/call**; new set: fold 0.62, check/call 0.38

**-9,375 vs Blueprint**, hand 47 (2d0dab50), we held Qd Js, they showed Kc Ts.
  - preflop board -              key `3` to call 300 → played **check/call**; new set: check/call 1.00
  - flop    board Ah Kd 2s       key `31/` to call 0 → played **check/call**; new set: check/call 0.64, raise ½ 0.34, raise pot 0.02
  - turn    board Ah Kd 2s Kh    key `31/11/` to call 0 → played **check/call**; new set: check/call 0.31, raise ½ 0.69
  - river   board Ah Kd 2s Kh Th key `31/11/11/` to call 0 → played **raise 2×**; new set: check/call 0.24, raise 2× 0.74, all-in 0.02
  - river   board Ah Kd 2s Kh Th key `31/11/11/45` to call 6,875 → played **check/call**; new set: check/call 1.00

**-9,200 vs Blueprint**, hand 108 (b6764645), we held 9d Kd, they showed 9s 8s.
  - preflop board -              key `` to call 300 → played **raise ½**; new set: raise ½ 0.62, raise pot 0.37
  - preflop board -              key `25` to call 9,600 → played **check/call**; new set: fold 0.02, check/call 0.98

**-8,946 vs hoops**, hand 71 (94fea99e), we held Ah 9h, they showed 6d Ks.
  - preflop board -              key `` to call 150 → played **check/call**; new set: check/call 0.10, raise ½ 0.05, raise pot 0.54, raise 2× 0.23, all-in 0.08
  - preflop board -              key `13` to call 630 → played **check/call**; new set: check/call 1.00
  - flop    board 8c Ac Kd       key `131/2` to call 937 → played **check/call**; new set: check/call 1.00
  - turn    board 8c Ac Kd 6h    key `131/21/3` to call 2,596 → played **check/call**; new set: check/call 1.00
  - river   board 8c Ac Kd 6h Qd key `131/21/31/5` to call 4,483 → played **check/call**; new set: check/call 1.00

**-8,775 vs Blueprint**, hand 44 (fa481050), we held 9c Qc, they showed Kd Kh.
  - preflop board -              key `` to call 100 → played **raise ½**; new set: check/call 0.04, raise ½ 0.68, raise pot 0.12, raise 2× 0.16
  - preflop board -              key `25` to call 500 → played **check/call**; new set: fold 0.95, check/call 0.05
  - flop    board 6d 5d Qh       key `251/3` to call 1,050 → played **raise ½**; new set: no entry
  - flop    board 6d 5d Qh       key `251/255` to call 4,875 → played **check/call**; new set: no entry

**-7,950 vs Blueprint**, hand 86 (212fe636), we held Kd 3d, they showed Qs 4s.
  - preflop board -              key `2` to call 400 → played **check/call**; new set: check/call 1.00
  - flop    board 3s Jc 8s       key `21/` to call 0 → played **check/call**; new set: check/call 0.53, raise ½ 0.43, raise pot 0.04
  - turn    board 3s Jc 8s 8h    key `21/11/` to call 0 → played **raise ½**; new set: check/call 0.09, raise ½ 0.91
  - river   board 3s Jc 8s 8h Qd key `21/11/21/` to call 0 → played **check/call**; new set: check/call 0.46, raise ½ 0.54
  - river   board 3s Jc 8s 8h Qd key `21/11/21/15` to call 6,350 → played **check/call**; new set: fold 0.86, check/call 0.14

**-7,419 vs hoops**, hand 38 (d1bb5228), we held Ks 8d, they showed Jc Jh.
  - preflop board -              key `2` to call 240 → played **check/call**; new set: check/call 1.00
  - flop    board 6h 6s 2d       key `31/` to call 0 → played **check/call**; new set: check/call 0.64, raise ½ 0.34, raise pot 0.02
  - flop    board 6h 6s 2d       key `21/13` to call 559 → played **check/call**; new set: check/call 1.00
  - turn    board 6h 6s 2d 8s    key `31/131/` to call 0 → played **check/call**; new set: check/call 0.62, raise ½ 0.35, raise pot 0.03
  - turn    board 6h 6s 2d 8s    key `21/131/12` to call 1,302 → played **check/call**; new set: check/call 1.00
  - river   board 6h 6s 2d 8s 9h key `21/131/121/` to call 0 → played **check/call**; new set: check/call 0.79, raise ½ 0.21
  - river   board 6h 6s 2d 8s 9h key `31/131/131/15` to call 5,168 → played **check/call**; new set: fold 0.35, check/call 0.65

