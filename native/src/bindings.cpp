#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/tuple.h>
#include <vector>
#include "hand_eval.hpp"
#include "equity.hpp"
#include "nolimit.hpp"
#include "mccfr.hpp"
#include "kuhn.hpp"
#include "nolimit_game.hpp"
#include <nanobind/stl/map.h>
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

    // --- MCCFR, validated on Kuhn -------------------------------------------
    m.def("solve_kuhn", [](int64_t iterations, uint64_t seed) {
        MCCFR<KuhnPoker> solver(KuhnPoker{}, UpdateRule::vanilla(), seed);
        solver.train(iterations);
        std::map<std::string, std::vector<double>> out;
        for (const auto& [key, node] : solver.nodes())
            out[key] = node.average_strategy();
        return out;
    }, nb::arg("iterations"), nb::arg("seed"),
       "Solve Kuhn poker. The game value to player 0 is -1/18 at equilibrium.");

    // --- the no-limit solver -----------------------------------------------
    //
    // The fitted abstraction is handed over rather than refitted here. k-means
    // over sampled equities is cheap and happens once, and refitting in C++
    // would be a second clustering that could silently disagree with the one
    // every existing strategy was built against.
    m.def("board_texture", [](const std::vector<int>& board) {
        return Abstraction::board_texture(board.data(), static_cast<int>(board.size()));
    }, nb::arg("board"), "Board texture class, mirroring abstraction.buckets.board_texture.");

    nb::class_<MCCFR<NoLimitGame>>(m, "NoLimitSolver")
        .def("__init__", [](MCCFR<NoLimitGame>* self,
                            const std::vector<int>& preflop,
                            const std::vector<double>& flop,
                            const std::vector<double>& turn,
                            const std::vector<double>& river,
                            int equity_samples, int starting_stack,
                            int small_blind, int big_blind,
                            const std::vector<int>& schedule, uint64_t seed,
                            bool texture) {
            Abstraction abstraction;
            abstraction.preflop.assign(preflop.begin(), preflop.end());
            abstraction.centroids = {flop, turn, river};
            abstraction.equity_samples = equity_samples;
            abstraction.texture = texture;
            RaiseSchedule sched;
            for (int n : schedule) sched.sizes.push_back(n);
            new (self) MCCFR<NoLimitGame>(
                NoLimitGame(std::move(abstraction), starting_stack, small_blind,
                            big_blind, std::move(sched)),
                UpdateRule::vanilla(), seed);
        }, nb::arg("preflop"), nb::arg("flop"), nb::arg("turn"), nb::arg("river"),
           nb::arg("equity_samples"), nb::arg("starting_stack"),
           nb::arg("small_blind"), nb::arg("big_blind"), nb::arg("schedule"),
           nb::arg("seed"), nb::arg("texture") = false)
        .def("train", &MCCFR<NoLimitGame>::train, nb::arg("iterations"),
             nb::call_guard<nb::gil_scoped_release>(),
             "Run `iterations` passes, each traversing once per player.")
        .def("iterations", &MCCFR<NoLimitGame>::iterations)
        .def("information_sets", [](const MCCFR<NoLimitGame>& s) { return s.nodes().size(); })
        .def("average_strategy", [](const MCCFR<NoLimitGame>& solver) {
            std::map<std::string, std::vector<double>> out;
            for (const auto& [key, node] : solver.nodes())
                out[key] = node.average_strategy();
            return out;
        }, "Information-set key -> action probabilities, as the Python returns.");
}
