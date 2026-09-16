# Replay: results/cfr/ladder169 on the logged hands

1367 decisions from 1283 hands (matches labelled v3*); baseline results/cfr/ladder200t.

## Coverage

logged misses 62, baseline lookup misses 62 (these should match), new-set misses 95; 1272 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 786 | 0.56 | 0.33 | 509 (65%) |
| flop | 262 | 0.53 | 0.43 | 117 (45%) |
| turn | 137 | 0.64 | 0.50 | 58 (42%) |
| river | 87 | 0.65 | 0.53 | 26 (30%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 165
- check/call → raise pot: 75
- raise pot → raise ½: 63
- raise ½ → raise pot: 52
- raise ½ → check/call: 50
- check/call → fold: 43
- check/call → raise 2×: 42
- raise ½ → raise 2×: 37

## Calls of a bet of the pot or more

24 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 33 | preflop | Qs Kh | - | 9,775 | 10,075 | 0.81 | 0.64 |
| 11 | preflop | Kh Kc | - | 9,500 | 10,500 | 1.00 | 1.00 |
| 21 | river | 7c 9c | 4h Qs 9s Th 9d | 7,800 | 12,000 | 1.00 | 0.99 |
| 103 | preflop | 5s 5c | - | 5,550 | 6,750 | 0.99 | 0.99 |
| 9 | turn | 6d 9c | 6c 7d 7s Ad | 1,600 | 2,700 | 1.00 | 1.00 |
| 29 | turn | 6c 6d | Jd Js Th 2c | 1,000 | 1,900 | 0.91 | 0.75 |
| 30 | preflop | As 8d | - | 450 | 750 | 0.47 | 1.00 |
| 38 | preflop | 6d Qd | - | 450 | 750 | 0.16 | 0.99 |
| 60 | preflop | 3h 4d | - | 450 | 850 | 0.77 | 0.03 |
| 59 | preflop | 8d Qh | - | 450 | 850 | 0.41 | 0.97 |
| 20 | preflop | Ac Jd | - | 450 | 650 | 0.27 | 0.00 |
| 21 | preflop | 7c 9c | - | 450 | 750 | 0.27 | 0.92 |
| 11 | preflop | 7d 7h | - | 450 | 650 | 0.27 | 0.11 |
| 21 | preflop | 7d 8h | - | 450 | 750 | 0.16 | 0.47 |
| 33 | preflop | 8s Ts | - | 450 | 750 | 1.00 | 1.00 |
| 3 | preflop | 6h 8h | - | 450 | 650 | 0.18 | 0.01 |
| 49 | preflop | Jc Ah | - | 450 | 850 | 0.99 | 1.00 |
| 10 | preflop | 7d Td | - | 450 | 650 | 0.93 | 0.07 |
| 5 | preflop | Ad 7h | - | 450 | 650 | 0.18 | 0.24 |
| 41 | preflop | 7c Qd | - | 450 | 850 | 0.69 | 0.93 |

Mean call probability over all 24: baseline 0.65, new 0.66.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs Blueprint**, hand 11 (daa4c270), we held Kh Kc, they showed 8c 8s.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: check/call 0.05, raise ½ 0.15, raise pot 0.03, raise 2× 0.76, all-in 0.02
  - preflop board -              key `45` to call 9,500 → played **check/call**; new set: check/call 1.00

**-9,925 vs Blueprint**, hand 33 (507aa7aa), we held Qs Kh, they showed Js Jd.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.10, raise ½ 0.34, raise pot 0.21, raise 2× 0.25, all-in 0.09
  - preflop board -              key `15` to call 9,775 → played **check/call**; new set: fold 0.36, check/call 0.64

**-9,850 vs Blueprint**, hand 3 (aae9fbf2), we held 6h 8h, they showed 7c 7s.
  - preflop board -              key `4` to call 450 → played **check/call**; new set: fold 0.89, check/call 0.01, raise ½ 0.08, raise pot 0.01, all-in 0.01
  - flop    board Jc 8s Qs       key `41/` to call 0 → played **check/call**; new set: check/call 0.70, raise ½ 0.23, raise pot 0.06, raise 2× 0.01
  - turn    board Jc 8s Qs Js    key `41/11/` to call 0 → played **check/call**; new set: check/call 0.60, raise ½ 0.30, raise pot 0.07, raise 2× 0.03
  - river   board Jc 8s Qs Js 4s key `41/11/11/` to call 0 → played **check/call**; new set: check/call 0.73, raise ½ 0.24, raise 2× 0.01, all-in 0.01
  - river   board Jc 8s Qs Js 4s key `41/11/11/14` to call 1,350 → played **all-in**; new set: fold 0.80, check/call 0.09, raise ½ 0.09, raise pot 0.02

**-9,725 vs Blueprint**, hand 22 (2fdf8130), we held Qd Ks, they showed As Js.
  - preflop board -              key `` to call 75 → played **raise pot**; new set: check/call 0.10, raise ½ 0.34, raise pot 0.21, raise 2× 0.25, all-in 0.09
  - preflop board -              key `35` to call 9,275 → played **check/call**; new set: no entry

**-9,650 vs Blueprint**, hand 5 (ed471b67), we held 5d Th, they showed Qc 5c.
  - preflop board -              key `` to call 50 → played **check/call**; new set: fold 0.27, check/call 0.72
  - flop    board 6s 5h Js       key `11/1` to call 0 → played **raise ½**; new set: check/call 0.51, raise ½ 0.42, raise pot 0.05, raise 2× 0.02
  - turn    board 6s 5h Js 5s    key `11/121/2` to call 100 → played **raise ½**; new set: check/call 0.06, raise ½ 0.51, raise pot 0.29, raise 2× 0.09, all-in 0.05
  - turn    board 6s 5h Js 5s    key `11/121/235` to call 9,050 → played **check/call**; new set: no entry

**-9,150 vs Blueprint**, hand 44 (8d645886), we held 3h Ac, they showed 3s 6c.
  - preflop board -              key `` to call 100 → played **check/call**; new set: check/call 0.02, raise ½ 0.16, raise pot 0.36, raise 2× 0.44, all-in 0.01
  - flop    board Ts 4c Js       key `11/1` to call 0 → played **check/call**; new set: check/call 0.21, raise ½ 0.69, raise pot 0.07, raise 2× 0.02
  - turn    board Ts 4c Js 2h    key `11/11/1` to call 0 → played **raise 2×**; new set: check/call 0.42, raise ½ 0.07, raise pot 0.36, raise 2× 0.15
  - river   board Ts 4c Js 2h 5c key `11/11/141/2` to call 200 → played **raise 2×**; new set: fold 0.02, check/call 0.98
  - river   board Ts 4c Js 2h 5c key `11/11/141/245` to call 4,850 → played **check/call**; new set: no entry

**-8,950 vs Blueprint**, hand 88 (e29644c9), we held 3d Tc, they showed Kh 9h.
  - preflop board -              key `2` to call 400 → played **check/call**; new set: fold 0.30, check/call 0.70
  - flop    board Jc Js 6s       key `21/` to call 0 → played **check/call**; new set: check/call 0.51, raise ½ 0.28, raise pot 0.13, raise 2× 0.08
  - turn    board Jc Js 6s Kd    key `21/11/` to call 0 → played **check/call**; new set: check/call 0.12, raise ½ 0.16, raise pot 0.40, raise 2× 0.32
  - river   board Jc Js 6s Kd 4c key `21/11/11/` to call 0 → played **all-in**; new set: check/call 0.75, raise ½ 0.11, raise 2× 0.06, all-in 0.08

**-8,850 vs Blueprint**, hand 30 (fd2e159f), we held Js Ks, they showed Ah Qd.
  - preflop board -              key `` to call 75 → played **raise ½**; new set: check/call 0.03, raise ½ 0.12, raise pot 0.19, raise 2× 0.49, all-in 0.17
  - preflop board -              key `25` to call 8,550 → played **check/call**; new set: no entry

