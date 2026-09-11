#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/tuple.h>
#include <vector>
#include "hand_eval.hpp"
#include "equity.hpp"
#include "nolimit.hpp"
#include <nanobind/stl/string.h>
#include <nanobind/stl/pair.h>

namespace nb = nanobind;
using namespace pokerbot;

NB_MODULE(pokerbot_native, m) {
    m.doc() = "NashForge solver core in C++. See native/README.md.";

    m.def("score_hand_7", [](const std::vector<int>& ranks,
                             const std::vector<int>& suits) {
        int8_t r[7], s[7];
        for (size_t i = 0; i < ranks.size() && i < 7; ++i) {
            r[i] = static_cast<int8_t>(ranks[i]);
            s[i] = static_cast<int8_t>(suits[i]);
        }
        return score_hand_7(r, s, static_cast<int>(ranks.size()));
    }, nb::arg("ranks"), nb::arg("suits"),
       "Packed comparable score. Must equal the Python score_hand_7 exactly.");

    m.def("equity_vs_random", [](const std::vector<int>& hole,
                                 const std::vector<int>& board,
                                 int samples, uint64_t seed) {
        return equity_vs_random(hole.data(), static_cast<int>(hole.size()),
                                board.data(), static_cast<int>(board.size()),
                                samples, seed);
    }, nb::arg("hole"), nb::arg("board"), nb::arg("samples"), nb::arg("seed"),
       "Equity by Monte Carlo. Same distribution as the Python, not the same stream.");

    // --- the betting game, exposed for equivalence testing ------------------
    //
    // Deliberately a replay function rather than a bound State class: the test
    // that matters drives both implementations through identical action
    // sequences and compares chips, so that is the surface it needs.
    m.def("replay", [](const std::vector<int>& actions, int starting_stack,
                       int small_blind, int big_blind,
                       const std::vector<int>& schedule) {
        RaiseSchedule sched;
        for (int n : schedule) sched.sizes.push_back(n);
        NoLimitHoldem game(starting_stack, small_blind, big_blind, sched);

        State s = game.initial_state();
        s.dealt = true;                     // cards are irrelevant to betting

        std::vector<std::vector<int8_t>> legal_at_each;
        for (int action : actions) {
            if (game.is_terminal(s)) return std::make_tuple(-1, std::vector<int>{},
                                                            std::string{}, legal_at_each);
            if (game.current_player(s) < 0) return std::make_tuple(-2, std::vector<int>{},
                                                                   std::string{}, legal_at_each);
            auto legal = game.legal_actions(s);
            legal_at_each.push_back(legal);
            bool ok = false;
            for (int8_t a : legal) if (a == action) ok = true;
            if (!ok) return std::make_tuple(-3, std::vector<int>{},
                                            std::string{}, legal_at_each);
            s = game.apply(s, action);
        }
        const int pot = s.contributions[0] + s.contributions[1];
        std::vector<int> stacks = {s.stacks[0], s.stacks[1]};
        return std::make_tuple(pot, stacks, s.history, legal_at_each);
    }, nb::arg("actions"), nb::arg("starting_stack"), nb::arg("small_blind"),
       nb::arg("big_blind"), nb::arg("schedule"),
       "Drive the betting game through a sequence. Returns (pot, stacks, history, "
       "legal-at-each-step); pot is -1 if the sequence ran past a terminal node, "
       "-2 at a chance node, -3 if an action was not legal.");
}
