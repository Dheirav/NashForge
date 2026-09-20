# Replay: results/cfr/ladder169l_v5f on the logged hands

1668 decisions from 1294 hands (matches labelled v5d*); baseline results/cfr/ladder169l_v5c.

## Coverage

logged misses 45, baseline lookup misses 44 (these should match), new-set misses 103; 1560 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 973 | 0.65 | 0.57 | 215 (22%) |
| flop | 350 | 0.70 | 0.66 | 33 (9%) |
| turn | 147 | 0.65 | 0.61 | 25 (17%) |
| river | 90 | 0.69 | 0.64 | 12 (13%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 80
- raise ½ → check/call: 54
- check/call → raise pot: 33
- raise ½ → raise pot: 29
- raise pot → raise ½: 16
- raise pot → check/call: 15
- check/call → fold: 12
- fold → check/call: 11

## Calls of a bet of the pot or more

22 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 16 | preflop | Qs 6c | - | 19,700 | 19,900 | 1.00 | 1.00 |
| 6 | preflop | Ad 7s | - | 19,500 | 19,700 | 1.00 | 1.00 |
| 8 | preflop | 5c Tc | - | 19,000 | 19,200 | 0.72 | 0.72 |
| 112 | preflop | Ts 7c | - | 18,550 | 19,750 | 1.00 | 1.00 |
| 32 | preflop | Ac Ah | - | 18,250 | 18,550 | 1.00 | 1.00 |
| 68 | preflop | 6s Ah | - | 18,250 | 18,850 | 1.00 | 1.00 |
| 30 | preflop | 6c 6s | - | 17,725 | 18,025 | 1.00 | 1.00 |
| 122 | preflop | As 4d | - | 17,400 | 19,000 | 1.00 | 1.00 |
| 70 | preflop | 8h As | - | 17,400 | 18,000 | 1.00 | 1.00 |
| 39 | preflop | Qd Jd | - | 17,025 | 17,325 | 0.94 | 0.94 |
| 51 | preflop | Qc 8c | - | 16,950 | 17,350 | 0.37 | 0.37 |
| 77 | preflop | Kh 9h | - | 14,800 | 15,400 | 1.00 | 1.00 |
| 72 | preflop | As 6c | - | 14,100 | 17,100 | 1.00 | 1.00 |
| 88 | preflop | 2c 3s | - | 12,050 | 13,650 | 0.50 | 0.50 |
| 111 | preflop | 2s 6h | - | 8,375 | 10,775 | 0.50 | 0.50 |
| 117 | preflop | Th 9h | - | 8,100 | 10,500 | 1.00 | 1.00 |
| 95 | preflop | 9c Kc | - | 7,050 | 7,850 | 0.99 | 0.99 |
| 95 | preflop | 3s 3c | - | 6,650 | 7,450 | 1.00 | 1.00 |
| 39 | preflop | Kc Kh | - | 5,425 | 5,725 | 1.00 | 1.00 |
| 66 | preflop | 7c 7s | - | 4,475 | 5,075 | 1.00 | 1.00 |

Mean call probability over all 22: baseline 0.87, new 0.87.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-9,900 vs Blueprint**, hand 4 (4e1b0b4e), we held Jd Ts, they showed Kd Qh.
  - preflop board -              key `3` to call 200 → played **raise ½**; new set: check/call 1.00
  - preflop board -              key `325` to call 650 → played **check/call**; new set: no entry
  - flop    board Tc 7d Qs       key `3251/` to call 0 → played **raise pot**; new set: no entry
  - flop    board Tc 7d Qs       key `3251/35` to call 6,150 → played **check/call**; new set: no entry

**-9,800 vs Blueprint**, hand 14 (4ecd82cb), we held As Qs, they showed Ah Ac.
  - preflop board -              key `3` to call 300 → played **raise pot**; new set: raise 2× 0.89, all-in 0.11
  - preflop board -              key `335` to call 950 → played **raise pot**; new set: no entry
  - preflop board -              key `33555` to call 3,350 → played **check/call**; new set: no entry

**-9,575 vs Blueprint**, hand 111 (389c8bf0), we held 2s 6h, they showed Qs Kd.
  - preflop board -              key `` to call 300 → played **raise ½**; new set: fold 1.00
  - preflop board -              key `25` to call 8,375 → played **check/call**; new set: fold 0.50, check/call 0.50

**-9,350 vs Blueprint**, hand 57 (8c43cb83), we held Ks 2d, they showed 7h Qh.
  - preflop board -              key `2` to call 300 → played **check/call**; new set: check/call 0.33, raise 2× 0.67
  - flop    board Jh 3c Kh       key `21/` to call 0 → played **check/call**; new set: check/call 0.83, raise ½ 0.15, raise pot 0.01
  - turn    board Jh 3c Kh 3h    key `21/11/` to call 0 → played **raise ½**; new set: check/call 0.36, raise ½ 0.36, raise pot 0.29
  - turn    board Jh 3c Kh 3h    key `21/11/22` to call 500 → played **check/call**; new set: no entry
  - river   board Jh 3c Kh 3h 2c key `31/11/221/` to call 0 → played **raise ½**; new set: no entry
  - river   board Jh 3c Kh 3h 2c key `21/11/221/25` to call 7,650 → played **check/call**; new set: no entry

**-9,300 vs Blueprint**, hand 117 (5b41b64c), we held Th 9h, they showed Kh Ad.
  - preflop board -              key `` to call 300 → played **raise ½**; new set: check/call 0.42, raise ½ 0.58
  - preflop board -              key `25` to call 8,100 → played **check/call**; new set: check/call 1.00

**-9,200 vs Blueprint**, hand 31 (08a32bb7), we held Tc Th, they showed Ah Jh.
  - preflop board -              key `2` to call 200 → played **raise 2×**; new set: raise 2× 1.00
  - preflop board -              key `245` to call 7,450 → played **check/call**; new set: check/call 1.00

**-9,000 vs Blueprint**, hand 14 (8e95e484), we held 8h Jh, they showed Ac Tc.
  - preflop board -              key `4` to call 450 → played **raise pot**; new set: fold 0.01, check/call 0.99
  - flop    board Ah Qd 9s       key `431/` to call 0 → played **raise ½**; new set: no entry
  - turn    board Ah Qd 9s Jd    key `431/21/` to call 0 → played **check/call**; new set: no entry
  - turn    board Ah Qd 9s Jd    key `431/21/12` to call 2,550 → played **raise ½**; new set: no entry

**-8,650 vs Blueprint**, hand 43 (649fddd0), we held 6d Ah, they showed 9d Ad.
  - preflop board -              key `2` to call 300 → played **raise pot**; new set: check/call 0.83, raise 2× 0.11, all-in 0.06
  - flop    board 9c 9s 6s       key `331/` to call 0 → played **raise ½**; new set: no entry
  - flop    board 9c 9s 6s       key `331/25` to call 5,650 → played **check/call**; new set: no entry

