# The misread-price guard

Written 5 October 2026 on branch `price-guard`. Behind `--price-misread`, off by default. Tested on
`tests/test_price_guard.py`, `tests/test_chipzen_player.py` and `tests/test_chipzen_bridge.py` only;
no duel, burst or full suite was run.

## 1. The leak

Match f1a0b755 against mr_hide, hand 20, 98bb deep. We held J♦T♦ and flopped a jack-high flush on
9♦4♦8♦. On the 5♦ turn they bet 800, we raised to 2,100 and they re-raised to 7,540. That is the third
raise of the street, and at that depth the cap-2 rung's schedule offers only all-in, so the bridge read
7,540 as all-in. We called 5,440. They were not all in: 2,174 was left behind.

The river J♣ checked to them and they bet the 2,174. **That river bet was a real all-in**: they started
the hand with 10,214 and had put in 500 preflop and 7,540 on the turn. So at the river decision
`opponent_stacks` was 0 and the true history `1321/11/13251/15` is terminal in every tree (an all-in
called, then more betting). The primary missed, and the bridge's last resort answered on the collapsed
re-read `1321/11/1221/15`, where the turn's pseudo all-in and our call collapse into a single call. On
that history the tree's pot is a small fraction of the arena's 16,080, so a shove reads as a shove of a
whole stack into a small pot, and the strategy folded. The real price was 1,746 (our whole stack) into
17,826, about 9 percent. They had 2♦3♥, a nine-high flush. Folding instead of calling cost 17,826
chips against the outcome of calling.

The existing "called for pot odds" rule did not catch it because it needs 10 to 1
(`to_call * 10 <= pot - to_call`), and this was 9 to 1 or so: 21,740 against 16,080 with the arena's
`to_call`, 17,460 against 16,080 with our capped call.

## 2. What the guard does, and one deviation from the brief

`ArenaPlayer.price_misread` (CLI `--price-misread` in `scripts/chipzen_run.py` and in
`scripts/chipzen_duel.py`'s flag string, and recorded in the match's `version` row). It runs after every
existing read and after the pot-odds rule, and turns a fold into a call when all of these hold:

- the choice is a fold, there is a bet to call and the arena offers a call;
- no read changed the choice (a read that folds on purpose, such as "river bet believed", priced the real
  bet and is left alone); the rule fallback is excluded too, because it prices the arena's own pot;
- the answer came from a misread history (`ArenaPlayer._misread`): either a `collapsed:` re-read, or the
  history the answering strategy was asked about ends in all-in while the bettor still has chips;
- the real price `call / (pot + call)` is at most `MISREAD_PRICE = 0.25`, where the arena's `pot`
  already holds their bet (the same definition the re-raise rule uses) and the call is capped at our stack,
  with their uncalled excess taken back out of the pot;
- the hand beats a random hand at least `MISREAD_EQUITY = 0.5` of the time, by the same
  `native.equity_vs_random(..., 200, 17)` call the river bluff-catch uses.

It records `adjusted = "priced a misread all-in"` and counts `Stats.misread_prices_called`.

**The deviation.** The brief said the guard fires only while the opponent still has chips and leaves real
all-ins to the pot-odds rule. Applied literally that would not have fired on hand 20, because the river
bet there was a real all-in; what was misread was the turn under it. So a collapsed re-read counts as a
misread whether or not the current bet is all-in, and the "chips behind" condition applies only to the
second case, a history whose last action is a pseudo all-in. A real all-in on a true history is still left
to the pot-odds rule, which is what the brief wanted to protect.

To know which history answered, `decide()` now tracks `answered_history`: the primary's, the
companion's own translation when a companion answered (a taper that reads a min-raise as a sized re-raise
was not misread), the alt history on a collapsed answer, and none when the rule or the short-stack table
answered.

## 3. Tests

`tests/test_price_guard.py`, 8 tests. The shipped solvers never fold a strong hand on these histories by
themselves, so the tests wrap each solver's lookup: the real lookup still runs (misses, the companion, the
collapsed re-read all happen as in a match) and only the action that comes back is forced to a fold.
That isolates the guard's own conditions:

| Test | State | Expected |
|---|---|---|
| fires | collapsed flop (preflop third raise called), T9 on A-T-4, 500 into 3,500 (price 0.125) | call, `priced a misread all-in`, counter +1 |
| flag off | the same with the flag off | fold |
| high price | the same facing 3,000 into 6,000 (price 0.33) | fold |
| weak hand | 7♣6♣ on A-T-4 (28 percent against random) | fold |
| real all-in | river shove for their whole stack on a true history, price 0.12 | fold, left to the pot-odds rule |
| true history | plain flop bet after a called open | fold |
| all-in read, chips behind | a min-raise read as all-in with 9,200 behind, primary holding the node | call; and when the taper answers on its own sized translation, fold |
| `_misread` | the hand 20 tuple and four negatives | as labelled |

The "chips behind" test cannot be built from the shipped trees, which have no all-in-only level (the
v5 ladder's cap-2 rungs have one at every third raise, and their pickles are not in this worktree), so
that one test also skips the lookup and lets the primary "hold" the node.

Run on 5 October: `venv/bin/python -m pytest tests/test_chipzen_player.py tests/test_chipzen_bridge.py
tests/test_price_guard.py -q` printed `69 passed in 1.63s`.

## 4. Audit over the logs

`scripts/audit_price_guard.py` walks every decision in `results/chipzen/matches/*.jsonl` (556 files,
50,544 decisions) and applies the guard's conditions as far as the record allows. The opponent's
remaining stack is rebuilt from the hand's starting stacks (`round_start.stacks`) and the action history
up to our action. The arena shows their cards on hands we folded as well, so every firing below has them.

Value of calling is our exact equity against their hand over the cards still to come
(`native.allin_edge(..., exact=True)`), times the pot after the call, less the call. **This scores the
call as the last chip in.** In seven of the eight firings the bettor kept chips, so the call would meet
more betting on later streets, played on a collapsed history, and that is ignored in both directions.
For the preflop ones in particular the number is the equity of a hand shown down, not the value of a
hand played out of tree.

Of 6,525 strategy folds facing a bet, 34 were on a misread history, 26 of them outside the thresholds,
and 453 more were answered by a companion whose own history the record does not keep, so they could
not be judged.

At price 0.25 and equity 0.5: **8 firings, all 8 with cards shown, estimated +23,404 chips** (+2,926 a
firing). Hand 20 alone is +17,826; the other seven are +5,578, every one positive.

| Match | Hand | Opponent | Street | Ours | Board | Theirs | Pot | Call | Price | Eq. random | Eq. vs theirs | Value | Kind |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b5b90d8e | 22 | mr_hide | preflop | 8♦A♠ | | 3♦3♣ | 1,875 | 375 | 0.17 | 0.58 | 0.47 | +680 | all-in read, chips behind |
| ba45b472 | 37 | Blueprint | preflop | A♥T♦ | | 5♣5♥ | 6,300 | 1,800 | 0.22 | 0.64 | 0.47 | +1,969 | all-in read, chips behind |
| cefb7663 | 57 | Blueprint | preflop | A♣3♥ | | J♣J♥ | 9,100 | 2,600 | 0.22 | 0.50 | 0.29 | +776 | all-in read, chips behind |
| f1a0b755 | 2 | mr_hide | preflop | K♣T♣ | | 5♥5♠ | 1,437 | 437 | 0.23 | 0.61 | 0.50 | +507 | all-in read, chips behind |
| f1a0b755 | 20 | mr_hide | river | J♦T♦ | 9♦4♦8♦5♦J♣ | 2♦3♥ | 17,826 | 1,746 | 0.09 | 0.89 | 1.00 | +17,826 | collapsed |
| f1dd11ec | 6 | mr_hide | preflop | Q♣K♦ | | T♥T♣ | 1,437 | 437 | 0.23 | 0.63 | 0.44 | +378 | all-in read, chips behind |
| f1dd11ec | 20 | mr_hide | preflop | K♣7♦ | | 6♠A♣ | 3,500 | 1,000 | 0.22 | 0.56 | 0.39 | +777 | all-in read, chips behind |
| fe2158ec | 34 | mr_hide | preflop | Q♠K♥ | | J♠A♠ | 1,875 | 375 | 0.17 | 0.61 | 0.38 | +491 | all-in read, chips behind |

Pot is the arena's pot before our call, with any uncalled excess removed. The seven preflop firings are
all the same shape: a small preflop four-bet (histories `325` and `345`), read as all-in because the
cap-2 schedule has only all-in at the third raise, folded at 17 to 23 percent.

Other thresholds, same equity floor, for the threshold choice:

| Price cap | Firings | Estimated chips | Note |
|---|---|---|---|
| 0.25 | 8 | +23,404 | all positive |
| 0.35 | 20 | +36,115 | adds 12, four of them negative (worst −1,492); +8,648 of the gain is one river straight |
| 0.50 | 22 | +31,387 | adds a collapsed turn at 0.37 worth −3,995 |

Dropping the equity floor to 0.4 at price 0.25 adds two preflop firings (+1,075). These samples are a
few dozen hands across many versions, so the table says which way the thresholds lean, not where they
should sit.

## 5. Recommendation

Merge behind the flag, off by default, at 0.25 and 0.5. At 0.25 every firing in the logs gained, and the
expected value of a call at that price with a hand that beats random is hard to make negative even
against a value-heavy range: the break-even equity is 25 percent and the shown hands averaged 0.42
excluding hand 20. Going to 0.35 roughly doubles the firings but brings in the first losses, and the
one large gain there is a river straight that a sliding rule (equity well above price) would catch more
safely than a higher flat cap; that is worth measuring, not adopting from this table.

The guard fires rarely, eight times in 50,544 logged decisions, so a burst cannot measure it directly. The
order should be the usual one: the cross-tree gate with the flag on and off, a replay on hand 20 to see
the call, then a burst labelled for this one change and read decomposed. The audit's number is the
better guide to its size than any burst will be, with the caveat above that it scores each call as the
last chip in.

Two related findings, not fixed here. The small preflop four-bet is read as all-in at every cap-2 rung,
and folding it at 17 to 23 percent is a leak of its own, larger in count than the collapsed case; the guard
covers it at the price, but the cleaner fix is a sized third raise on the preflop schedule. And 453
companion folds facing a bet could not be audited because the record does not keep the companion's
history; logging it would close that gap.
