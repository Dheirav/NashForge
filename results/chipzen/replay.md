# Replay: results/cfr/ladder169 on the logged hands

9798 decisions from 5234 hands; baseline results/cfr/ladder200t.

## Coverage

logged misses 557, baseline lookup misses 371 (these should match), new-set misses 485; 9299 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 4057 | 0.44 | 0.36 | 2398 (59%) |
| flop | 2427 | 0.54 | 0.52 | 708 (29%) |
| turn | 1628 | 0.52 | 0.51 | 560 (34%) |
| river | 1187 | 0.54 | 0.55 | 384 (32%) |

Most common changes of most-likely action (baseline → new):

- check/call → raise ½: 1056
- check/call → raise pot: 429
- raise ½ → check/call: 347
- check/call → fold: 310
- raise ½ → raise pot: 292
- raise pot → raise ½: 264
- check/call → raise 2×: 233
- fold → check/call: 228

## Calls of a bet of the pot or more

86 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 38 | preflop | 3h Th | - | 19,116 | 19,416 | 0.94 | 0.81 |
| 18 | preflop | Jc 8s | - | 18,988 | 19,188 | 1.00 | 0.44 |
| 48 | preflop | 9d Jh | - | 18,664 | 19,064 | 1.00 | 0.98 |
| 21 | river | Qd Jh | Jd 5d 8s 2d 6c | 18,018 | 19,218 | 1.00 | 1.00 |
| 30 | turn | 7c 7h | 2h 4h 5c 8h | 16,414 | 17,974 | 1.00 | 0.19 |
| 27 | river | Ah As | Ts 8h 3d Tc 4d | 12,363 | 16,127 | 1.00 | 1.00 |
| 39 | river | Qs 6c | 8s Jc Qh 6h 2s | 11,607 | 15,297 | 1.00 | 1.00 |
| 23 | river | Jh 2h | 6h 4h Jc 4c 5h | 10,314 | 14,568 | 1.00 | 1.00 |
| 33 | preflop | Qs Kh | - | 9,775 | 10,075 | 0.81 | 0.64 |
| 11 | preflop | Kh Kc | - | 9,500 | 10,500 | 1.00 | 1.00 |
| 29 | river | Ad 5s | 7h Ah 9d 6s 6c | 9,006 | 13,708 | 0.20 | 0.92 |
| 18 | river | 8c Jc | Jd Qc 9c Ts Jh | 8,051 | 13,295 | 0.65 | 0.99 |
| 21 | river | 7c 9c | 4h Qs 9s Th 9d | 7,800 | 12,000 | 1.00 | 0.99 |
| 2 | river | 5d Ac | 2c 4s 2h 3d 6s | 6,962 | 13,638 | 1.00 | 0.50 |
| 16 | turn | 4d 5s | 5h Kc 4c Ah | 6,712 | 10,816 | 1.00 | 1.00 |
| 103 | preflop | 5s 5c | - | 5,550 | 6,750 | 0.99 | 0.99 |
| 3 | turn | 2c 2h | 8s 6c 2d 4s | 3,600 | 6,000 | 1.00 | 1.00 |
| 2 | flop | 3h 3s | 6c 4c 7s | 3,600 | 6,000 | 0.00 | 0.07 |
| 3 | turn | 2c 2h | 8s 6c 2d 4s | 3,600 | 6,000 | 1.00 | 1.00 |
| 2 | flop | 3h 3s | 6c 4c 7s | 3,600 | 6,000 | 0.00 | 0.07 |

Mean call probability over all 86: baseline 0.67, new 0.68.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-10,000 vs hoops**, hand 1 (0b7e2f73), we held 9h Qs, they showed Kd Ks.
  - preflop board -              key `` to call 50 → played **raise ½**; new set: raise ½ 0.99, raise pot 0.01
  - preflop board -              key `25` to call 340 → played **check/call**; new set: fold 1.00
  - flop    board As 7s 2h       key `251/3` to call 610 → played **check/call**; new set: no entry
  - turn    board As 7s 2h 6d    key `251/21/1` to call 0 → played **raise ½**; new set: no entry
  - river   board As 7s 2h 6d 4c key `251/21/121/1` to call 0 → played **all-in**; new set: no entry

**-10,000 vs Blueprint**, hand 11 (daa4c270), we held Kh Kc, they showed 8c 8s.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: check/call 0.05, raise ½ 0.15, raise pot 0.03, raise 2× 0.76, all-in 0.02
  - preflop board -              key `45` to call 9,500 → played **check/call**; new set: check/call 1.00

**-9,933 vs hoops**, hand 17 (13fbf84a), we held Th Kh, they showed Qh Qc.
  - preflop board -              key `` to call 50 → played **raise pot**; new set: check/call 0.29, raise ½ 0.50, raise pot 0.18, raise 2× 0.02
  - preflop board -              key `35` to call 580 → played **check/call**; new set: fold 0.68, check/call 0.32
  - flop    board Tc 6d Ts       key `351/2` to call 1,046 → played **all-in**; new set: no entry

**-9,925 vs Blueprint**, hand 33 (507aa7aa), we held Qs Kh, they showed Js Jd.
  - preflop board -              key `` to call 75 → played **check/call**; new set: check/call 0.10, raise ½ 0.34, raise pot 0.21, raise 2× 0.25, all-in 0.09
  - preflop board -              key `15` to call 9,775 → played **check/call**; new set: fold 0.36, check/call 0.64

**-9,850 vs Blueprint**, hand 3 (aae9fbf2), we held 6h 8h, they showed 7c 7s.
  - preflop board -              key `4` to call 450 → played **check/call**; new set: fold 0.89, check/call 0.01, raise ½ 0.08, raise pot 0.01, all-in 0.01
  - flop    board Jc 8s Qs       key `41/` to call 0 → played **check/call**; new set: check/call 0.70, raise ½ 0.23, raise pot 0.06, raise 2× 0.01
  - turn    board Jc 8s Qs Js    key `41/11/` to call 0 → played **check/call**; new set: check/call 0.60, raise ½ 0.30, raise pot 0.07, raise 2× 0.03
  - river   board Jc 8s Qs Js 4s key `41/11/11/` to call 0 → played **check/call**; new set: check/call 0.73, raise ½ 0.24, raise 2× 0.01, all-in 0.01
  - river   board Jc 8s Qs Js 4s key `41/11/11/14` to call 1,350 → played **all-in**; new set: fold 0.80, check/call 0.09, raise ½ 0.09, raise pot 0.02

**-9,842 vs mr_hide**, hand 65 (fad37378), we held Th Ah, they showed As Ks.
  - preflop board -              key `` to call 150 → played **raise pot**; new set: fold 0.01, check/call 0.13, raise pot 0.18, raise 2× 0.27, all-in 0.40
  - preflop board -              key `35` to call 1,725 → played **check/call**; new set: no entry
  - flop    board Jh 4s 7h       key `351/1` to call 0 → played **check/call**; new set: no entry
  - turn    board Jh 4s 7h 3s    key `351/11/1` to call 0 → played **check/call**; new set: no entry
  - river   board Jh 4s 7h 3s Ac key `351/11/11/3` to call 2,887 → played **raise pot**; new set: no entry

**-9,725 vs Blueprint**, hand 22 (2fdf8130), we held Qd Ks, they showed As Js.
  - preflop board -              key `` to call 75 → played **raise pot**; new set: check/call 0.10, raise ½ 0.34, raise pot 0.21, raise 2× 0.25, all-in 0.09
  - preflop board -              key `35` to call 9,275 → played **check/call**; new set: no entry

**-9,671 vs mr_hide**, hand 45 (17c03884), we held 7d 7s, they showed 9s 9c.
  - preflop board -              key `` to call 100 → played **raise 2×**; new set: check/call 0.03, raise ½ 0.18, raise pot 0.09, raise 2× 0.19, all-in 0.51
  - flop    board 6h Kh 3c       key `41/1` to call 0 → played **raise ½**; new set: check/call 0.59, raise ½ 0.32, raise pot 0.08, raise 2× 0.01
  - turn    board 6h Kh 3c 2c    key `41/121/1` to call 0 → played **check/call**; new set: check/call 0.65, raise ½ 0.34, raise 2× 0.01
  - river   board 6h Kh 3c 2c 4s key `41/131/11/1` to call 0 → played **raise 2×**; new set: check/call 0.38, raise ½ 0.16, raise pot 0.06, raise 2× 0.20, all-in 0.20

