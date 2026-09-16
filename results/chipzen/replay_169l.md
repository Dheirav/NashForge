# Replay: results/cfr/ladder169l on the logged hands

3608 decisions from 2976 hands (matches labelled v*); baseline results/cfr/ladder200t.

## Coverage

logged misses 202, baseline lookup misses 202 (these should match), new-set misses 202; 3406 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 2019 | 0.57 | 0.45 | 952 (47%) |
| flop | 754 | 0.54 | 0.50 | 168 (22%) |
| turn | 388 | 0.60 | 0.57 | 92 (24%) |
| river | 245 | 0.62 | 0.57 | 57 (23%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 255
- raise pot → raise ½: 152
- raise ½ → check/call: 146
- raise ½ → raise pot: 146
- check/call → fold: 114
- check/call → raise pot: 103
- raise ½ → raise 2×: 58
- raise ½ → fold: 41

## Calls of a bet of the pot or more

40 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 38 | flop | 6d Qd | 6s 3c Qs | 11,275 | 13,675 | 1.00 | 1.00 |
| 33 | preflop | Qs Kh | - | 9,775 | 10,075 | 0.81 | 0.01 |
| 11 | preflop | Kh Kc | - | 9,500 | 10,500 | 1.00 | 1.00 |
| 22 | preflop | Qd Ks | - | 9,275 | 10,175 | 0.40 | 0.00 |
| 33 | preflop | Qc Ac | - | 8,875 | 9,775 | 1.00 | 1.00 |
| 30 | preflop | Js Ks | - | 8,550 | 9,150 | 0.45 | 0.02 |
| 74 | preflop | Tc Td | - | 8,000 | 8,600 | 1.00 | 1.00 |
| 18 | preflop | Ad Kc | - | 7,950 | 8,350 | 1.00 | 1.00 |
| 21 | river | 7c 9c | 4h Qs 9s Th 9d | 7,800 | 12,000 | 1.00 | 1.00 |
| 62 | preflop | Kc Ad | - | 6,800 | 7,400 | 1.00 | 1.00 |
| 22 | preflop | Kc Ks | - | 6,400 | 7,300 | 1.00 | 1.00 |
| 103 | preflop | 5s 5c | - | 5,550 | 6,750 | 0.99 | 1.00 |
| 84 | preflop | Jc Qc | - | 5,300 | 6,100 | 1.00 | 0.03 |
| 83 | preflop | Jc Jd | - | 3,850 | 4,650 | 1.00 | 1.00 |
| 70 | preflop | Qd Ad | - | 2,850 | 3,450 | 1.00 | 1.00 |
| 28 | flop | Td Ad | 8s 9d As | 2,500 | 4,500 | 0.58 | 0.78 |
| 9 | turn | 6d 9c | 6c 7d 7s Ad | 1,600 | 2,700 | 1.00 | 1.00 |
| 29 | turn | 6c 6d | Jd Js Th 2c | 1,000 | 1,900 | 0.91 | 0.84 |
| 15 | flop | 6s 9c | 9h Ks 6d | 880 | 1,680 | 1.00 | 1.00 |
| 21 | preflop | Kc 9c | - | 700 | 1,300 | 0.98 | 1.00 |

Mean call probability over all 40: baseline 0.75, new 0.66.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs Blueprint**, hand 11 (daa4c270), we held Kh Kc, they showed 8c 8s.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: check/call 0.10, raise ½ 0.13, raise pot 0.67, raise 2× 0.10
  - preflop board -              key `45` to call 9,500 → played **check/call**; new set: check/call 1.00

**-9,925 vs Blueprint**, hand 33 (507aa7aa), we held Qs Kh, they showed Js Jd.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.07, raise ½ 0.43, raise pot 0.47, raise 2× 0.03
  - preflop board -              key `15` to call 9,775 → played **check/call**; new set: fold 0.99, check/call 0.01

**-9,850 vs Blueprint**, hand 3 (aae9fbf2), we held 6h 8h, they showed 7c 7s.
  - preflop board -              key `4` to call 450 → played **check/call**; new set: fold 0.82, check/call 0.09, raise ½ 0.06, raise 2× 0.02
  - flop    board Jc 8s Qs       key `41/` to call 0 → played **check/call**; new set: check/call 0.90, raise ½ 0.09, raise pot 0.01
  - turn    board Jc 8s Qs Js    key `41/11/` to call 0 → played **check/call**; new set: check/call 0.51, raise ½ 0.30, raise pot 0.17, raise 2× 0.02
  - river   board Jc 8s Qs Js 4s key `41/11/11/` to call 0 → played **check/call**; new set: check/call 0.76, raise ½ 0.21, raise pot 0.02
  - river   board Jc 8s Qs Js 4s key `41/11/11/14` to call 1,350 → played **all-in**; new set: fold 0.75, check/call 0.24

**-9,725 vs Blueprint**, hand 22 (2fdf8130), we held Qd Ks, they showed As Js.
  - preflop board -              key `` to call 75 → played **raise pot**; new set: check/call 0.07, raise ½ 0.43, raise pot 0.47, raise 2× 0.03
  - preflop board -              key `35` to call 9,275 → played **check/call**; new set: fold 1.00

**-9,650 vs Blueprint**, hand 5 (ed471b67), we held 5d Th, they showed Qc 5c.
  - preflop board -              key `` to call 50 → played **check/call**; new set: fold 0.07, check/call 0.93
  - flop    board 6s 5h Js       key `11/1` to call 0 → played **raise ½**; new set: check/call 0.51, raise ½ 0.25, raise pot 0.24
  - turn    board 6s 5h Js 5s    key `11/121/2` to call 100 → played **raise ½**; new set: check/call 0.09, raise ½ 0.19, raise pot 0.52, raise 2× 0.20
  - turn    board 6s 5h Js 5s    key `11/121/235` to call 9,050 → played **check/call**; new set: no entry

**-9,225 vs Blueprint**, hand 69 (66dc2ed8), we held 8h Jd, they showed Ac As.
  - preflop board -              key `2` to call 300 → played **check/call**; new set: check/call 1.00
  - flop    board 6c 6h Js       key `21/` to call 0 → played **check/call**; new set: check/call 0.62, raise ½ 0.38
  - flop    board 6c 6h Js       key `21/12` to call 500 → played **check/call**; new set: check/call 1.00
  - turn    board 6c 6h Js Ks    key `21/121/` to call 0 → played **raise ½**; new set: check/call 0.29, raise ½ 0.71
  - turn    board 6c 6h Js Ks    key `21/121/25` to call 1,150 → played **check/call**; new set: no entry
  - river   board 6c 6h Js Ks Th key `21/121/251/` to call 0 → played **check/call**; new set: no entry
  - river   board 6c 6h Js Ks Th key `21/121/251/15` to call 5,875 → played **check/call**; new set: no entry

**-9,150 vs Blueprint**, hand 44 (8d645886), we held 3h Ac, they showed 3s 6c.
  - preflop board -              key `` to call 100 → played **check/call**; new set: check/call 0.40, raise ½ 0.06, raise pot 0.48, raise 2× 0.05
  - flop    board Ts 4c Js       key `11/1` to call 0 → played **check/call**; new set: check/call 0.75, raise ½ 0.22, raise pot 0.02, raise 2× 0.01
  - turn    board Ts 4c Js 2h    key `11/11/1` to call 0 → played **raise 2×**; new set: check/call 1.00
  - river   board Ts 4c Js 2h 5c key `11/11/141/2` to call 200 → played **raise 2×**; new set: raise ½ 0.73, raise pot 0.18, raise 2× 0.02, all-in 0.07
  - river   board Ts 4c Js 2h 5c key `11/11/141/245` to call 4,850 → played **check/call**; new set: no entry

**-9,150 vs r0ckGarden**, hand 13 (edfb18dc), we held 8s 3h, they showed Qh Jd.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: fold 1.00
  - flop    board 2d 8c Th       key `41/1` to call 0 → played **check/call**; new set: check/call 0.68, raise ½ 0.30, raise pot 0.02
  - turn    board 2d 8c Th 9h    key `41/11/3` to call 780 → played **raise pot**; new set: fold 0.13, check/call 0.76, raise ½ 0.09, raise pot 0.01, raise 2× 0.01
  - turn    board 2d 8c Th 9h    key `41/11/335` to call 4,442 → played **check/call**; new set: no entry
  - river   board 2d 8c Th 9h Qd key `41/11/3351/5` to call 868 → played **check/call**; new set: no entry

