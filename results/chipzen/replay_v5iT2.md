# Replay: ../PokerBot/results/cfr/ladder169l_v5iT2full on the logged hands

1867 decisions from 1282 hands (matches labelled v5i*); baseline ../PokerBot/results/cfr/ladder169l_v5i.

History keys rebuilt from each logged hand on each set's own schedule. The check: the baseline's rebuilt keys against the logged ones, {'rebuilt': 1867, 'same as logged': 1781, 'no draw: same': 1707, 'differs from logged': 86, 'no draw: DIFFERS': 11}; the new set's, {'rebuilt': 1867, 'same as logged': 1747, 'no draw: same': 1671, 'differs from logged': 120, 'no draw: DIFFERS': 35} (these differ by design where its tree differs).

## Coverage

logged misses 18, baseline lookup misses 18 (these should match), new-set misses 18; 1849 decisions compared.

## Agreement with what was played

Mean probability the set gives the action actually taken. The baseline played these, so its column is the check on the lookup; the new set's column is how differently it would play.

| street | compared | P(baseline) | P(new) | most likely action differs |
|---|---|---|---|---|
| preflop | 1029 | 0.63 | 0.56 | 230 (22%) |
| flop | 425 | 0.76 | 0.67 | 61 (14%) |
| turn | 243 | 0.71 | 0.65 | 29 (12%) |
| river | 152 | 0.68 | 0.64 | 20 (13%) |

Most common changes of most-likely action (baseline → new):

- raise ½ → check/call: 67
- raise ½ → raise pot: 49
- raise pot → raise ½: 46
- raise pot → check/call: 31
- check/call → raise ½: 30
- check/call → raise pot: 27
- raise ½ → raise 2×: 15
- check/call → fold: 15

## Calls of a bet of the pot or more

16 such calls were made. Call probability under each set:

| hand | street | ours | board | to call | pot | baseline call | new call |
|---|---|---|---|---|---|---|---|
| 87 | preflop | Qd 9s | - | 18,250 | 19,050 | 1.00 | 1.00 |
| 7 | preflop | Qh Qs | - | 9,950 | 10,150 | 1.00 | 1.00 |
| 61 | preflop | Tc Ts | - | 8,150 | 8,750 | 1.00 | 1.00 |
| 127 | preflop | 8s Ah | - | 6,600 | 11,400 | 1.00 | 1.00 |
| 84 | preflop | 7d Kd | - | 6,400 | 7,200 | 0.34 | 0.34 |
| 91 | preflop | Qs Qd | - | 5,775 | 6,575 | 1.00 | 1.00 |
| 76 | preflop | Ts Tc | - | 5,725 | 6,325 | 1.00 | 1.00 |
| 61 | preflop | Qd Jd | - | 5,000 | 5,600 | 0.94 | 0.94 |
| 74 | preflop | 7c 2h | - | 4,575 | 5,775 | 0.50 | 0.50 |
| 115 | preflop | Tc Ah | - | 4,500 | 8,100 | 1.00 | 1.00 |
| 48 | river | Jd Kd | Tc 8d Jh Qd 9s | 4,500 | 6,500 | 1.00 | 1.00 |
| 110 | preflop | Ts 7s | - | 4,450 | 8,050 | 0.86 | 0.86 |
| 38 | preflop | 9h 9d | - | 4,401 | 8,301 | 1.00 | 1.00 |
| 10 | river | 3s 4s | 3h Qs 7s 8d 2h | 1,307 | 2,565 | 0.05 | 0.40 |
| 26 | preflop | Qd Qc | - | 550 | 850 | 1.00 | 1.00 |
| 35 | preflop | 9d 2d | - | 357 | 657 | 0.52 | 0.52 |

Mean call probability over all 16: baseline 0.83, new 0.85.

## The 8 most expensive hands, re-asked

Only the first decision that differs is a real divergence; after it the opponent's replies are unknown.

**-9,950 vs Blueprint**, hand 7 (cebbe08d), we held Qh Qs, they showed Kh As.
  - preflop board -              key `5` to call 9,950 → played **check/call**; new set: check/call 1.00

**-9,715 vs wsp**, hand 67 (916a19a4), we held Ah 9s, they showed 9d Qd.
  - preflop board -              key `` to call 150 → played **raise ½**; new set: check/call 0.31, raise ½ 0.48, raise pot 0.21, all-in 0.01
  - flop    board 5s 7d 9h       key `21/2` to call 720 → played **raise ½**; new set: check/call 0.67, raise ½ 0.29, raise pot 0.03
  - turn    board 5s 7d 9h Qh    key `21/221/2` to call 3,168 → played **check/call**; new set: check/call 0.93, raise ½ 0.06
  - river   board 5s 7d 9h Qh Jh key `21/321/21/5` to call 4,477 → played **check/call**; new set: fold 0.31, check/call 0.69

**-9,492 vs r0ckGarden**, hand 17 (01a9fdae), we held Ad Tc, they showed Ac As.
  - preflop board -              key `` to call 50 → played **raise 2×**; new set: check/call 0.01, raise ½ 0.09, raise pot 0.77, raise 2× 0.13
  - preflop board -              key `44` to call 750 → played **check/call**; new set: check/call 0.99, all-in 0.01
  - flop    board Th Ks 2c       key `441/2` to call 1,950 → played **raise 2×**; new set: check/call 1.00

**-9,025 vs Blueprint**, hand 83 (ba45b472), we held 6d Kd, they showed 5c 4c.
  - preflop board -              key `2` to call 400 → played **raise 2×**; new set: check/call 0.27, raise ½ 0.27, raise pot 0.15, raise 2× 0.30
  - preflop board -              key `245` to call 5,025 → played **check/call**; new set: no entry

**-8,550 vs r0ckGarden**, hand 9 (7cb48600), we held Td 9h, they showed Ac 2c.
  - preflop board -              key `` to call 50 → played **check/call**; new set: check/call 0.30, raise pot 0.70
  - flop    board 8d Qs Jc       key `11/1` to call 0 → played **raise ½**; new set: raise ½ 0.46, raise pot 0.30, raise 2× 0.24
  - flop    board 8d Qs Jc       key `11/124` to call 248 → played **check/call**; new set: check/call 1.00
  - turn    board 8d Qs Jc 3c    key `11/1241/1` to call 0 → played **raise ½**; new set: raise ½ 0.39, raise pot 0.38, raise 2× 0.22
  - river   board 8d Qs Jc 3c 5c key `11/1241/121/2` to call 1,397 → played **all-in**; new set: check/call 0.04, raise 2× 0.60, all-in 0.37

**-7,935 vs wsp**, hand 29 (916a19a4), we held Ac Ks, they showed Kd Kh.
  - preflop board -              key `` to call 75 → played **raise pot**; new set: check/call 0.02, raise ½ 0.51, raise pot 0.47
  - preflop board -              key `34` to call 510 → played **all-in**; new set: check/call 0.02, all-in 0.98

**-6,575 vs Blueprint**, hand 95 (0bbff31f), we held 6h Ac, they showed Ts 9s.
  - preflop board -              key `` to call 200 → played **all-in**; new set: check/call 0.30, raise ½ 0.06, raise 2× 0.15, all-in 0.48

**-6,300 vs Blueprint**, hand 115 (3e6754f8), we held Tc Ah, they showed Qh Ac.
  - preflop board -              key `` to call 300 → played **raise pot**; new set: check/call 0.27, raise ½ 0.22, raise pot 0.17, raise 2× 0.32, all-in 0.03
  - preflop board -              key `35` to call 4,500 → played **check/call**; new set: check/call 1.00

