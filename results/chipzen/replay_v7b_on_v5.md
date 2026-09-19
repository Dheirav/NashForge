# Replay: results/cfr/ladder169l_v5c on the logged hands

2565 decisions from 1110 hands (matches labelled v5*); baseline results/cfr/ladder169l.

## Coverage

logged misses 141, baseline lookup misses 143 (these should match), new-set misses 129 after its cap-2 companions answered 148 of the primary's 277; 2422 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 989 | 0.57 | 0.43 | 358 (36%) |
| flop | 629 | 0.63 | 0.58 | 145 (23%) |
| turn | 471 | 0.64 | 0.58 | 122 (26%) |
| river | 333 | 0.65 | 0.57 | 71 (21%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 237
- raise ½ → check/call: 69
- check/call → raise pot: 66
- fold → check/call: 63
- raise ½ → raise pot: 48
- raise pot → raise ½: 43
- check/call → raise 2×: 40
- raise pot → check/call: 24

## Calls of a bet of the pot or more

13 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 24 | river | 9h 9c | 6c 4c 7s 6s 4d | 12,184 | 15,580 | 0.21 | 0.21 |
| 8 | turn | Qs 7s | 2c 9s Qd Ts | 3,600 | 6,600 | 1.00 | 1.00 |
| 20 | flop | Ad 5c | Ks 7s 5s | 2,520 | 4,520 | 0.73 | 0.08 |
| 31 | flop | Ts Ac | 2s Th 8s | 1,980 | 3,780 | 1.00 | 1.00 |
| 94 | preflop | 5d Qc | - | 1,419 | 2,219 | 1.00 | 1.00 |
| 3 | preflop | As 5s | - | 800 | 1,200 | 0.99 | 1.00 |
| 43 | preflop | 6h 6c | - | 746 | 1,146 | 1.00 | 1.00 |
| 24 | preflop | 4h Jh | - | 509 | 809 | 0.97 | 0.97 |
| 40 | preflop | As Ad | - | 444 | 744 | 1.00 | 1.00 |
| 35 | preflop | 6d Qh | - | 300 | 600 | 0.28 | 1.00 |
| 38 | preflop | 7c Ac | - | 300 | 600 | 1.00 | 1.00 |
| 1 | preflop | 9c Tc | - | 217 | 417 | 0.48 | 1.00 |
| 13 | preflop | 9d Qd | - | 214 | 414 | 0.47 | 1.00 |

Mean call probability over all 13: baseline 0.78, new 0.87.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|
| 18 | river | Ac 3h | Jh Qh Qs 7h 9c | 10,258 | 15,098 | fold | 70bb: fold 1.00 | fold 0.97 |
| 15 | river | 3c As | Qs 7d 3s 5d 5h | 5,781 | 16,581 | fold | 100bb: fold 0.55, check/call 0.45 | fold 1.00 |
| 31 | turn | Ts Ac | 2s Th 8s 4s | 5,031 | 10,791 | check/call | 50bb: check/call 1.00 | check/call 1.00 |
| 35 | river | As 3d | 7s 5d Ad Jh Th | 4,739 | 15,323 | fold | 70bb: fold 0.98 | fold 0.84, check/call 0.16 |
| 1 | river | Qs 2s | 9h 2c Tc Kd 9c | 3,944 | 10,012 | fold | 100bb: fold 0.99 | fold 0.99 |
| 8 | turn | Qs 7s | 2c 9s Qd Ts | 3,600 | 6,600 | check/call | 50bb: check/call 1.00 | check/call 1.00 |
| 3 | turn | As 5s | 3s 2s 9h Ah | 3,320 | 6,640 | raise 2× | 100bb: check/call 0.97 | check/call 0.50, raise pot 0.27, raise 2× 0.13 |
| 12 | river | 2c 3s | Ks 2d 3c 6c 5d | 3,300 | 8,300 | check/call | 100bb: fold 0.16, check/call 0.64, raise 2× 0.17 | fold 0.20, check/call 0.58, raise pot 0.21 |
| 32 | turn | 7c As | 3c 5s Kh Jh | 2,597 | 7,319 | fold | 50bb: fold 1.00 | fold 1.00 |
| 20 | flop | Ad 5c | Ks 7s 5s | 2,520 | 4,520 | check/call | 50bb: fold 0.92, check/call 0.08 | fold 0.27, check/call 0.73 |
| 24 | river | Ts Kh | 3s 5s 5c 7s 8s | 2,457 | 4,977 | fold | 50bb: fold 1.00 | no entry |
| 8 | turn | Jh Jd | 8c 3d 5d 9c | 2,400 | 6,400 | all-in | 100bb: check/call 0.29, raise ½ 0.64 | check/call 0.12, raise ½ 0.60, raise pot 0.12, all-in 0.13 |
| 33 | river | Ks Ad | 6c 9d 4c Jd Qc | 2,376 | 6,336 | fold | 50bb: fold 0.99 | no entry |
| 48 | river | 5c Qh | 3c Qs Ks 7h 2d | 2,280 | 6,080 | check/call | 50bb: fold 0.36, check/call 0.64 | fold 0.07, check/call 0.92 |
| 40 | river | Kc Tc | Kd Jh 8s Jd Td | 2,249 | 13,049 | fold | 50bb: fold 0.44, check/call 0.56 | fold 0.43, check/call 0.57 |
| 31 | flop | Ts Ac | 2s Th 8s | 1,980 | 3,780 | check/call | 50bb: check/call 1.00 | check/call 1.00 |
| 10 | turn | 7s Ah | 9s Js Qd 2d | 1,869 | 4,989 | fold | 100bb: fold 1.00 | fold 1.00 |
| 11 | river | Jd Th | Qh 4c 5s 3s Jc | 1,860 | 4,860 | fold | 70bb: fold 1.00 | fold 0.96 |
| 56 | river | Jd Ac | 7c 6d Ts 5s 9h | 1,800 | 5,800 | fold | 50bb: fold 1.00 | no entry |
| 3 | turn | 8s As | 2h Jc 9c 7d | 1,756 | 4,008 | fold | 100bb: fold 0.90, check/call 0.10 | fold 0.93 |
| 52 | flop | Qh Kc | 3c 9c Ts | 1,632 | 4,032 | check/call | 50bb: check/call 1.00 | check/call 0.97 |
| 55 | preflop | Qc 3c | - | 1,500 | 3,500 | check/call | 50bb: fold 1.00 | no entry |
| 12 | turn | 2c 3s | Ks 2d 3c 6c | 1,500 | 3,500 | check/call | 100bb: check/call 1.00 | check/call 1.00 |
| 3 | river | 6s 5h | 5d Qd 9s Kd 4h | 1,420 | 3,572 | fold | 100bb: fold 1.00 | fold 1.00 |
| 35 | turn | As 3d | 7s 5d Ad Jh | 1,386 | 3,906 | raise ½ | 70bb: check/call 0.45, raise ½ 0.55 | check/call 0.57, raise ½ 0.39 |

Facing a bet of the pot or more on those lines (7): the companion calls with mean probability 0.63 and folds with 0.36.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-9,700 vs mr_hide**, hand 3 (6ca68beb), we held Kd 4d, they showed Td Ts.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.09, raise ½ 0.12, raise pot 0.42, raise 2× 0.37
  - preflop board -              key `22` to call 325 → played **check/call**; new set: check/call 1.00
  - flop    board 8d Kc 9h       key `231/1` to call 0 → played **raise ½**; new set: check/call 0.13, raise ½ 0.66, raise pot 0.20, raise 2× 0.01
  - turn    board 8d Kc 9h Tc    key `221/121/2` to call 1,386 → played **raise ½**; new set: check/call 0.55, raise ½ 0.41, raise pot 0.04
  - turn    board 8d Kc 9h Tc    key `221/121/225` to call 5,428 → played **check/call**; new set: no entry

**-9,638 vs mr_hide**, hand 75 (97131196), we held Qc 8c, they showed 2h As.
  - preflop board -              key `` to call 150 → played **raise pot**; new set: check/call 0.01, raise ½ 0.10, raise pot 0.87, raise 2× 0.02
  - flop    board 4c Ah 4d       key `31/2` to call 990 → played **check/call**; new set: check/call 1.00
  - turn    board 4c Ah 4d Ad    key `31/21/2` to call 2,494 → played **check/call**; new set: check/call 1.00
  - river   board 4c Ah 4d Ad Qs key `31/21/21/5` to call 5,254 → played **check/call**; new set: fold 0.38, check/call 0.62

**-9,146 vs hoops**, hand 12 (31567f79), we held 2d 2s, they showed 9s Tc.
  - preflop board -              key `2` to call 160 → played **check/call**; new set: check/call 1.00
  - flop    board 6h Qh 8d       key `31/` to call 0 → played **raise pot**; new set: check/call 0.47, raise ½ 0.38, raise pot 0.13, raise 2× 0.03
  - turn    board 6h Qh 8d Jc    key `31/31/` to call 0 → played **check/call**; new set: check/call 0.74, raise ½ 0.04, raise pot 0.21, raise 2× 0.01
  - turn    board 6h Qh 8d Jc    key `31/31/12` to call 1,149 → played **raise 2×**; new set: fold 0.98, check/call 0.02

**-9,144 vs r0ckGarden**, hand 9 (e4e642d7), we held Jc Jd, they showed Qs Js.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.43, raise ½ 0.21, raise pot 0.30, raise 2× 0.06
  - flop    board Kc Qd 9s       key `21/2` to call 312 → played **check/call**; new set: check/call 1.00
  - turn    board Kc Qd 9s 2c    key `21/31/2` to call 798 → played **raise ½**; new set: check/call 1.00
  - turn    board Kc Qd 9s 2c    key `21/31/225` to call 2,765 → played **check/call**; new set: no entry
  - river   board Kc Qd 9s 2c 5c key `21/31/3251/5` to call 5,471 → played **check/call**; new set: no entry

**-8,835 vs r0ckGarden**, hand 14 (27743fc0), we held 7c 9d, they showed Qh 7h.
  - preflop board -              key `1` to call 0 → played **check/call**; new set: check/call 0.66, raise ½ 0.06, raise pot 0.27, raise 2× 0.02
  - flop    board Kd 7s 9h       key `11/` to call 0 → played **raise 2×**; new set: check/call 0.73, raise ½ 0.09, raise pot 0.13, raise 2× 0.05
  - turn    board Kd 7s 9h Qc    key `11/41/` to call 0 → played **check/call**; new set: check/call 0.51, raise ½ 0.22, raise pot 0.20, raise 2× 0.08
  - turn    board Kd 7s 9h Qc    key `11/41/13` to call 780 → played **raise ½**; new set: check/call 1.00
  - turn    board Kd 7s 9h Qc    key `11/41/1225` to call 2,701 → played **raise pot**; new set: no entry

**-8,594 vs r0ckGarden**, hand 27 (27743fc0), we held 7c Qh, they showed 4c 6h.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.09, raise ½ 0.75, raise pot 0.15, raise 2× 0.01
  - flop    board 7s Ad 4s       key `11/1` to call 0 → played **check/call**; new set: check/call 0.40, raise ½ 0.51, raise pot 0.09
  - turn    board 7s Ad 4s 9h    key `11/11/1` to call 0 → played **raise ½**; new set: check/call 0.06, raise ½ 0.79, raise pot 0.15
  - river   board 7s Ad 4s 9h 4d key `11/11/121/2` to call 468 → played **raise 2×**; new set: fold 0.01, check/call 0.99
  - river   board 7s Ad 4s 9h 4d key `11/11/121/345` to call 4,754 → played **check/call**; new set: no entry

**-8,346 vs r0ckGarden**, hand 55 (524b6f3a), we held Qc 3c, they showed 8d 8s.
  - preflop board -              key `` to call 100 → played **raise 2×**; new set: raise ½ 0.13, raise pot 0.11, raise 2× 0.76
  - preflop board -              key `45` to call 1,500 → played **check/call**; new set: fold 1.00
  - flop    board Jd Ts 3h       key `451/2` to call 3,250 → played **check/call**; new set: no entry
  - turn    board Jd Ts 3h Th    key `451/21/5` to call 5,904 → played **check/call**; new set: no entry

**-7,500 vs mr_hide**, hand 5 (1e672f47), we held 7s 8d, they showed Tc 9d.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: raise ½ 0.02, raise pot 0.98, raise 2× 0.01
  - flop    board 6c 7d 3c       key `21/1` to call 0 → played **check/call**; new set: check/call 0.75, raise ½ 0.24, raise pot 0.01
  - turn    board 6c 7d 3c Jd    key `21/11/1` to call 0 → played **raise ½**; new set: check/call 0.06, raise ½ 0.82, raise pot 0.12
  - river   board 6c 7d 3c Jd 8c key `21/11/121/3` to call 528 → played **raise ½**; new set: check/call 1.00
  - river   board 6c 7d 3c Jd 8c key `21/11/121/225` to call 3,926 → played **raise pot**; new set: no entry

