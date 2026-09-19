# Replay: results/cfr/ladder169l_10m on the logged hands

2559 decisions from 1107 hands (matches labelled v5*); baseline results/cfr/ladder169l.

## Coverage

logged misses 141, baseline lookup misses 143 (these should match), new-set misses 143; 2416 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 985 | 0.57 | 0.52 | 251 (25%) |
| flop | 628 | 0.63 | 0.62 | 75 (12%) |
| turn | 470 | 0.64 | 0.63 | 50 (11%) |
| river | 333 | 0.65 | 0.64 | 37 (11%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 99
- raise ½ → check/call: 82
- raise pot → raise ½: 49
- raise ½ → raise pot: 30
- check/call → raise pot: 29
- raise pot → check/call: 22
- check/call → fold: 17
- raise 2× → check/call: 16

## Calls of a bet of the pot or more

12 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 24 | river | 9h 9c | 6c 4c 7s 6s 4d | 12,184 | 15,580 | 0.21 | 0.21 |
| 8 | turn | Qs 7s | 2c 9s Qd Ts | 3,600 | 6,600 | 1.00 | 1.00 |
| 20 | flop | Ad 5c | Ks 7s 5s | 2,520 | 4,520 | 0.73 | 0.08 |
| 31 | flop | Ts Ac | 2s Th 8s | 1,980 | 3,780 | 1.00 | 1.00 |
| 94 | preflop | 5d Qc | - | 1,419 | 2,219 | 1.00 | 1.00 |
| 43 | preflop | 6h 6c | - | 746 | 1,146 | 1.00 | 1.00 |
| 24 | preflop | 4h Jh | - | 509 | 809 | 0.97 | 0.97 |
| 40 | preflop | As Ad | - | 444 | 744 | 1.00 | 1.00 |
| 35 | preflop | 6d Qh | - | 300 | 600 | 0.28 | 0.03 |
| 38 | preflop | 7c Ac | - | 300 | 600 | 1.00 | 1.00 |
| 1 | preflop | 9c Tc | - | 217 | 417 | 0.48 | 0.55 |
| 13 | preflop | 9d Qd | - | 214 | 414 | 0.47 | 0.72 |

Mean call probability over all 12: baseline 0.76, new 0.71.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-9,700 vs mr_hide**, hand 3 (6ca68beb), we held Kd 4d, they showed Td Ts.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.49, raise ½ 0.32, raise pot 0.19, raise 2× 0.01
  - preflop board -              key `22` to call 325 → played **check/call**; new set: check/call 1.00
  - flop    board 8d Kc 9h       key `231/1` to call 0 → played **raise ½**; new set: check/call 0.21, raise ½ 0.48, raise pot 0.28, raise 2× 0.03
  - turn    board 8d Kc 9h Tc    key `221/121/2` to call 1,386 → played **raise ½**; new set: check/call 0.78, raise ½ 0.21
  - turn    board 8d Kc 9h Tc    key `221/121/225` to call 5,428 → played **check/call**; new set: no entry

**-9,638 vs mr_hide**, hand 75 (97131196), we held Qc 8c, they showed 2h As.
  - preflop board -              key `` to call 150 → played **raise pot**; new set: check/call 0.01, raise ½ 0.10, raise pot 0.87, raise 2× 0.02
  - flop    board 4c Ah 4d       key `31/2` to call 990 → played **check/call**; new set: check/call 1.00
  - turn    board 4c Ah 4d Ad    key `31/21/2` to call 2,494 → played **check/call**; new set: check/call 1.00
  - river   board 4c Ah 4d Ad Qs key `31/21/21/5` to call 5,254 → played **check/call**; new set: fold 0.38, check/call 0.62

**-9,146 vs hoops**, hand 12 (31567f79), we held 2d 2s, they showed 9s Tc.
  - preflop board -              key `2` to call 160 → played **check/call**; new set: check/call 0.89, raise ½ 0.03, raise pot 0.08
  - flop    board 6h Qh 8d       key `31/` to call 0 → played **raise pot**; new set: check/call 0.87, raise ½ 0.10, raise pot 0.02, raise 2× 0.01
  - turn    board 6h Qh 8d Jc    key `31/31/` to call 0 → played **check/call**; new set: check/call 0.77, raise ½ 0.11, raise pot 0.05, raise 2× 0.07
  - turn    board 6h Qh 8d Jc    key `31/31/12` to call 1,149 → played **raise 2×**; new set: fold 0.91, raise ½ 0.08, raise pot 0.01

**-9,144 vs r0ckGarden**, hand 9 (e4e642d7), we held Jc Jd, they showed Qs Js.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.12, raise ½ 0.51, raise pot 0.21, raise 2× 0.16
  - flop    board Kc Qd 9s       key `21/2` to call 312 → played **check/call**; new set: check/call 0.69, raise ½ 0.29, raise pot 0.02
  - turn    board Kc Qd 9s 2c    key `21/31/2` to call 798 → played **raise ½**; new set: check/call 0.90, raise ½ 0.09
  - turn    board Kc Qd 9s 2c    key `21/31/225` to call 2,765 → played **check/call**; new set: no entry
  - river   board Kc Qd 9s 2c 5c key `21/31/3251/5` to call 5,471 → played **check/call**; new set: no entry

**-8,835 vs r0ckGarden**, hand 14 (27743fc0), we held 7c 9d, they showed Qh 7h.
  - preflop board -              key `1` to call 0 → played **check/call**; new set: check/call 0.94, raise pot 0.06
  - flop    board Kd 7s 9h       key `11/` to call 0 → played **raise 2×**; new set: check/call 0.79, raise ½ 0.12, raise pot 0.07, raise 2× 0.03
  - turn    board Kd 7s 9h Qc    key `11/41/` to call 0 → played **check/call**; new set: check/call 0.36, raise ½ 0.19, raise pot 0.35, raise 2× 0.10
  - turn    board Kd 7s 9h Qc    key `11/41/13` to call 780 → played **raise ½**; new set: check/call 0.34, raise ½ 0.24, raise pot 0.13, raise 2× 0.27, all-in 0.02
  - turn    board Kd 7s 9h Qc    key `11/41/1225` to call 2,701 → played **raise pot**; new set: no entry

**-8,594 vs r0ckGarden**, hand 27 (27743fc0), we held 7c Qh, they showed 4c 6h.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.72, raise ½ 0.27, raise pot 0.01
  - flop    board 7s Ad 4s       key `11/1` to call 0 → played **check/call**; new set: check/call 0.40, raise ½ 0.49, raise pot 0.11
  - turn    board 7s Ad 4s 9h    key `11/11/1` to call 0 → played **raise ½**; new set: check/call 0.22, raise ½ 0.32, raise pot 0.38, raise 2× 0.08
  - river   board 7s Ad 4s 9h 4d key `11/11/121/2` to call 468 → played **raise 2×**; new set: check/call 1.00
  - river   board 7s Ad 4s 9h 4d key `11/11/121/345` to call 4,754 → played **check/call**; new set: no entry

**-8,346 vs r0ckGarden**, hand 55 (524b6f3a), we held Qc 3c, they showed 8d 8s.
  - preflop board -              key `` to call 100 → played **raise 2×**; new set: raise ½ 0.13, raise pot 0.11, raise 2× 0.76
  - preflop board -              key `45` to call 1,500 → played **check/call**; new set: no entry
  - flop    board Jd Ts 3h       key `451/2` to call 3,250 → played **check/call**; new set: no entry
  - turn    board Jd Ts 3h Th    key `451/21/5` to call 5,904 → played **check/call**; new set: no entry

**-7,500 vs mr_hide**, hand 5 (1e672f47), we held 7s 8d, they showed Tc 9d.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: check/call 0.11, raise ½ 0.89
  - flop    board 6c 7d 3c       key `21/1` to call 0 → played **check/call**; new set: check/call 0.54, raise ½ 0.43, raise pot 0.03
  - turn    board 6c 7d 3c Jd    key `21/11/1` to call 0 → played **raise ½**; new set: check/call 0.19, raise ½ 0.61, raise pot 0.18, raise 2× 0.02
  - river   board 6c 7d 3c Jd 8c key `21/11/121/3` to call 528 → played **raise ½**; new set: raise ½ 0.21, raise pot 0.02, raise 2× 0.06, all-in 0.71
  - river   board 6c 7d 3c Jd 8c key `21/11/121/225` to call 3,926 → played **raise pot**; new set: no entry

