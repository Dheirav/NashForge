# Replay: results/cfr/ladder169l_v5c on the logged hands

1771 decisions from 1299 hands (matches labelled v7*); baseline results/cfr/ladder169l_v7.

## Coverage

logged misses 167, baseline lookup misses 167 (these should match), new-set misses 82 after its cap-2 companions answered 85 of the primary's 167; 1604 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 949 | 0.59 | 0.59 | 0 (0%) |
| flop | 315 | 0.67 | 0.67 | 0 (0%) |
| turn | 199 | 0.64 | 0.64 | 0 (0%) |
| river | 141 | 0.68 | 0.68 | 0 (0%) |

Most common changes of most-likely action (baseline → new):


## Calls of a bet of the pot or more

20 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 56 | preflop | 8d 8c | - | 18,394 | 18,794 | 1.00 | 1.00 |
| 78 | preflop | 8c Th | - | 17,464 | 18,064 | 0.76 | 0.76 |
| 83 | preflop | Ks 7h | - | 15,900 | 16,700 | 1.00 | 1.00 |
| 104 | preflop | Kc Tc | - | 8,850 | 10,050 | 0.60 | 0.60 |
| 1 | river | 7h Js | Tc 8h 2h 9h As | 7,750 | 12,250 | 1.00 | 1.00 |
| 98 | preflop | 5d 3d | - | 6,300 | 7,100 | 0.10 | 0.10 |
| 42 | river | 9d 8s | 9c 4d 3s Qs Qd | 6,300 | 7,900 | 1.00 | 1.00 |
| 72 | preflop | Jh Ac | - | 5,225 | 5,825 | 1.00 | 1.00 |
| 93 | preflop | 7c Qc | - | 5,200 | 6,000 | 0.98 | 0.98 |
| 58 | preflop | Ks Kh | - | 4,775 | 5,175 | 1.00 | 1.00 |
| 46 | preflop | As Ts | - | 2,950 | 3,350 | 0.97 | 0.97 |
| 56 | river | As 5h | Ad 4c Kd Ah Qh | 2,600 | 4,900 | 1.00 | 1.00 |
| 78 | preflop | 6s Ac | - | 1,574 | 2,174 | 1.00 | 1.00 |
| 74 | preflop | 4h As | - | 1,012 | 1,612 | 1.00 | 1.00 |
| 11 | turn | Kd Qd | 6d Qh Kh 3h | 750 | 1,150 | 1.00 | 1.00 |
| 71 | preflop | Ah 9h | - | 630 | 1,230 | 1.00 | 1.00 |
| 55 | preflop | Js 3s | - | 502 | 902 | 1.00 | 1.00 |
| 28 | preflop | Jd Qd | - | 300 | 600 | 1.00 | 1.00 |
| 1 | preflop | Ks As | - | 300 | 500 | 1.00 | 1.00 |
| 19 | preflop | 5s 9d | - | 224 | 424 | 0.98 | 0.98 |

Mean call probability over all 20: baseline 0.92, new 0.92.

## The primary's misses, answered by the cap-2 companion

Every line the one-raise primary has no node for (an opponent's re-raise, mostly) and what the companion says there. Baseline is what the set that played gave at the same point (its own primary, or nothing if it fell to the rule).

| hand | street | ours | board | to call | pot | played | companion | baseline |
|---|---|---|---|---|---|---|---|---|
| 56 | preflop | 4h Jh | - | 13,450 | 14,250 | fold | 50bb: fold 1.00 | no entry |
| 44 | preflop | 3s 9h | - | 13,150 | 13,950 | fold | 50bb: fold 1.00 | no entry |
| 59 | preflop | 8h 2d | - | 12,900 | 13,700 | fold | 50bb: fold 0.97 | no entry |
| 52 | preflop | 8c Jd | - | 12,150 | 12,950 | fold | 50bb: fold 1.00 | no entry |
| 15 | preflop | 4h Jh | - | 11,750 | 12,350 | fold | 70bb: fold 1.00 | no entry |
| 60 | river | Qh 7h | 7c 3h 2d 5s Ts | 11,450 | 13,850 | fold | 50bb: fold 0.99 | no entry |
| 69 | preflop | 5d 6c | - | 11,100 | 12,300 | fold | 50bb: fold 1.00 | no entry |
| 43 | preflop | 6c 8d | - | 10,700 | 11,900 | fold | 50bb: fold 1.00 | no entry |
| 77 | preflop | 9h 8c | - | 10,700 | 12,500 | fold | 50bb: fold 1.00 | no entry |
| 13 | preflop | 7d Qh | - | 9,850 | 10,450 | fold | 100bb: fold 1.00 | no entry |
| 64 | flop | 9c 4c | Td 7s 8s | 9,750 | 12,150 | fold | 50bb: fold 1.00 | no entry |
| 1 | preflop | Jh 9s | - | 9,700 | 10,300 | fold | 100bb: fold 1.00 | no entry |
| 9 | preflop | 3h 4h | - | 9,700 | 10,700 | fold | 100bb: fold 1.00 | no entry |
| 31 | river | Th Td | 7h 4h 3s Kc 2s | 9,700 | 10,900 | fold | 70bb: fold 1.00 | no entry |
| 3 | preflop | 9s 7d | - | 9,550 | 9,950 | fold | 100bb: fold 1.00 | no entry |
| 59 | preflop | 3c Ac | - | 9,475 | 10,275 | fold | 50bb: fold 1.00 | no entry |
| 17 | preflop | Kd 4s | - | 9,350 | 10,350 | fold | 100bb: fold 1.00 | no entry |
| 25 | river | 9c 5d | Kh 2s 2c Ac Qc | 8,875 | 10,075 | fold | 70bb: fold 1.00 | no entry |
| 42 | preflop | 6s 8h | - | 8,875 | 9,675 | fold | 50bb: fold 1.00 | no entry |
| 40 | preflop | Jc As | - | 8,775 | 9,375 | fold | 70bb: fold 0.66, check/call 0.34 | no entry |
| 15 | preflop | Qh 3c | - | 8,600 | 9,600 | fold | 100bb: fold 1.00 | no entry |
| 78 | river | 7d Kd | Jh Jd Kh 3c 9d | 8,250 | 11,850 | fold | 50bb: fold 0.88, check/call 0.12 | no entry |
| 78 | preflop | 6c 8c | - | 8,225 | 10,025 | fold | 50bb: fold 1.00 | no entry |
| 54 | preflop | 5h 3c | - | 7,875 | 9,075 | fold | 50bb: fold 1.00 | no entry |
| 24 | preflop | 2s Qc | - | 7,600 | 8,200 | fold | 50bb: fold 1.00 | no entry |

Facing a bet of the pot or more on those lines (57): the companion calls with mean probability 0.07 and folds with 0.93.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs Blueprint**, hand 1 (7ab8614e), we held 7h Js, they showed Qh 5h.
  - preflop board -              key `` to call 50 → played **raise pot**; new set: raise ½ 0.22, raise pot 0.64, raise 2× 0.14
  - flop    board Tc 8h 2h       key `31/1` to call 0 → played **raise pot**; new set: check/call 0.22, raise ½ 0.65, raise pot 0.13, raise 2× 0.01
  - turn    board Tc 8h 2h 9h    key `31/131/2` to call 1,350 → played **check/call**; new set: check/call 1.00
  - river   board Tc 8h 2h 9h As key `31/131/31/5` to call 7,750 → played **check/call**; new set: check/call 1.00

**-8,946 vs hoops**, hand 71 (94fea99e), we held Ah 9h, they showed 6d Ks.
  - preflop board -              key `` to call 150 → played **check/call**; new set: check/call 0.10, raise ½ 0.05, raise pot 0.54, raise 2× 0.23, all-in 0.08
  - preflop board -              key `13` to call 630 → played **check/call**; new set: check/call 1.00
  - flop    board 8c Ac Kd       key `131/2` to call 937 → played **check/call**; new set: check/call 1.00
  - turn    board 8c Ac Kd 6h    key `131/21/3` to call 2,596 → played **check/call**; new set: check/call 1.00
  - river   board 8c Ac Kd 6h Qd key `131/21/31/5` to call 4,483 → played **check/call**; new set: check/call 1.00

**-7,100 vs Blueprint**, hand 42 (b0968a01), we held 9d 8s, they showed Kc 9s.
  - preflop board -              key `2` to call 200 → played **check/call**; new set: check/call 1.00
  - flop    board 9c 4d 3s       key `21/` to call 0 → played **check/call**; new set: check/call 0.63, raise ½ 0.21, raise pot 0.13, raise 2× 0.04
  - turn    board 9c 4d 3s Qs    key `21/11/` to call 0 → played **raise ½**; new set: check/call 0.13, raise ½ 0.87
  - river   board 9c 4d 3s Qs Qd key `21/11/21/` to call 0 → played **check/call**; new set: check/call 0.71, raise pot 0.13, raise 2× 0.16
  - river   board 9c 4d 3s Qs Qd key `21/11/21/15` to call 6,300 → played **check/call**; new set: check/call 1.00

**-6,725 vs Blueprint**, hand 40 (bb5594e5), we held Qd Kc, they showed Ad As.
  - preflop board -              key `` to call 75 → played **raise pot**; new set: raise ½ 0.27, raise pot 0.34, raise 2× 0.39
  - preflop board -              key `35` to call 750 → played **check/call**; new set: fold 0.98, check/call 0.02
  - flop    board 4c 3s Kd       key `351/2` to call 1,500 → played **raise 2×**; new set: no entry

**-6,500 vs Blueprint**, hand 42 (cfd7fb0e), we held Ah Qh, they showed As Ts.
  - preflop board -              key `` to call 100 → played **raise 2×**; new set: check/call 0.12, raise ½ 0.01, raise pot 0.47, raise 2× 0.40
  - preflop board -              key `45` to call 1,150 → played **check/call**; new set: fold 0.14, check/call 0.86
  - flop    board Td 7s 4s       key `451/1` to call 0 → played **raise pot**; new set: no entry
  - flop    board Td 7s 4s       key `451/135` to call 50 → played **check/call**; new set: no entry

**-6,000 vs Blueprint**, hand 89 (d5f9d67c), we held Ks 3h, they showed As 6c.
  - preflop board -              key `2` to call 400 → played **check/call**; new set: check/call 1.00
  - flop    board 9c Ts 4c       key `21/` to call 0 → played **check/call**; new set: check/call 0.65, raise ½ 0.20, raise pot 0.15, raise 2× 0.01
  - flop    board 9c Ts 4c       key `21/12` to call 400 → played **check/call**; new set: fold 0.07, check/call 0.93
  - turn    board 9c Ts 4c 7d    key `21/121/` to call 0 → played **check/call**; new set: check/call 0.99, raise ½ 0.01
  - river   board 9c Ts 4c 7d 5h key `21/121/11/` to call 0 → played **raise 2×**; new set: raise ½ 0.35, raise pot 0.01, raise 2× 0.18, all-in 0.45
  - river   board 9c Ts 4c 7d 5h key `21/121/11/45` to call 3,075 → played **fold**; new set: no entry

**-5,525 vs Blueprint**, hand 98 (d5f9d67c), we held 8d Kh, they showed Qc Kd.
  - preflop board -              key `` to call 200 → played **raise ½**; new set: raise ½ 0.59, raise pot 0.41
  - preflop board -              key `25` to call 13,675 → played **check/call**; new set: no entry

**-5,000 vs Blueprint**, hand 72 (bb5594e5), we held Ah 8s, they showed 9s Ac.
  - preflop board -              key `` to call 150 → played **raise ½**; new set: raise ½ 0.26, raise pot 0.72, raise 2× 0.02
  - preflop board -              key `25` to call 1,050 → played **check/call**; new set: no entry
  - flop    board Jd 2h 5h       key `251/5` to call 13,350 → played **check/call**; new set: no entry

