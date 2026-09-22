#include <string>
#include <cstring>
#include <algorithm>
#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <nanobind/stl/tuple.h>
#include <vector>
#include "hand_eval.hpp"
#include "equity.hpp"
#include "bucket_table.hpp"
#include "river.hpp"
#include "nolimit.hpp"
#include "mccfr.hpp"
#include "kuhn.hpp"
#include "nolimit_game.hpp"
#include <nanobind/ndarray.h>
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
    m.def("solve_kuhn", [](int64_t iterations, uint64_t seed, int64_t average_from, int threads,
                           const std::vector<std::pair<std::string, std::vector<double>>>& warm,
                           int64_t warm_weight, double warm_scale, const std::string& rule,
                           const std::string& warm_mode, int64_t prune_after, double prune_threshold) {
        MCCFR<KuhnPoker> solver(KuhnPoker{}, UpdateRule::from_name(rule), seed);
        solver.set_average_from(average_from);
        if (!warm.empty()) solver.warm_start(warm, warm_weight, warm_scale, warm_mode);
        if (prune_after >= 0) solver.set_pruning(prune_after, prune_threshold, 0.95);
        solver.train(iterations, threads);
        std::map<std::string, std::vector<double>> out;
        solver.for_each_node([&](const std::string& key, const InfoSetNode& node) {
            out[solver.key_string(key)] = node.average_strategy();
        });
        return out;
    }, nb::arg("iterations"), nb::arg("seed"), nb::arg("average_from") = 0, nb::arg("threads") = 1,
       nb::arg("warm") = std::vector<std::pair<std::string, std::vector<double>>>{},
       nb::arg("warm_weight") = 0, nb::arg("warm_scale") = 1.0, nb::arg("rule") = "vanilla",
       nb::arg("warm_mode") = "proportional", nb::arg("prune_after") = -1, nb::arg("prune_threshold") = 0.0,
       "Solve Kuhn poker. The game value to player 0 is -1/18 at equilibrium. `warm` seeds "
       "the named information sets before training, see MCCFR::warm_start.");

    // --- the no-limit solver -----------------------------------------------
    //
    // The fitted abstraction is handed over rather than refitted here. k-means
    // over sampled equities is cheap and happens once, and refitting in C++
    // would be a second clustering that could silently disagree with the one
    // every existing strategy was built against.
    m.def("allin_edge", [](const std::vector<int>& mine, const std::vector<int>& theirs,
                           const std::vector<int>& board, bool exact, int samples, uint64_t seed) {
        // For tests: P(win) - P(lose) of `mine` against `theirs` over the
        // runouts of `board`, exactly or by sampling.
        NoLimitGame game(Abstraction{}, 200, 1, 2, RaiseSchedule{});
        game.set_exact_terminals(exact);
        NoLimitGame::State s = game.initial_state();
        s.hole[0] = {static_cast<int8_t>(mine[0]), static_cast<int8_t>(mine[1])};
        s.hole[1] = {static_cast<int8_t>(theirs[0]), static_cast<int8_t>(theirs[1])};
        s.bet.dealt = true;
        for (size_t i = 0; i < board.size(); ++i) s.bet.board[i] = static_cast<int8_t>(board[i]);
        s.bet.board_n = static_cast<int8_t>(board.size());
        s.bet.street = static_cast<int8_t>(board.size() == 3 ? 1 : (board.size() == 4 ? 2 : 3));
        s.bet.contributions = {100, 100};
        s.bet.committed = {0, 0};
        s.bet.stacks = {0, 0};
        if (exact) return game.allin_edge(s, 0);
        Rng rng(seed);
        double total = 0.0;
        for (int i = 0; i < samples; ++i) {
            NoLimitGame::State r = s;
            while (r.bet.board_n < 5) r = game.sample_chance(r, rng);
            total += game.utility(r, 0) / 100.0;
        }
        return total / samples;
    }, nb::arg("mine"), nb::arg("theirs"), nb::arg("board"), nb::arg("exact"), nb::arg("samples") = 0, nb::arg("seed") = 0);

    m.def("strength_histogram", [](const std::vector<int>& hole, const std::vector<int>& board,
                                   int bins, int runouts, int opponents, uint64_t seed) {
        if (bins < 1 || bins > 64 || runouts < 1 || opponents < 1 || hole.size() != 2 || board.size() > 5)
            throw std::invalid_argument("strength_histogram: bins 1 to 64, runouts and opponents at least 1, two hole cards, at most five board cards");
        std::vector<double> out(static_cast<size_t>(bins));
        strength_histogram(hole.data(), board.data(), static_cast<int>(board.size()), bins, runouts, opponents, seed, out.data());
        return out;
    }, nb::arg("hole"), nb::arg("board"), nb::arg("bins"), nb::arg("runouts"), nb::arg("opponents"), nb::arg("seed"),
       "River-equity histogram over sampled runouts, as abstraction/histogram.py computes it; same distribution, not the same stream.");
    m.def("nearest_emd", [](const std::vector<std::vector<double>>& centroids, const std::vector<double>& hist) {
        for (const auto& row : centroids)
            if (row.size() != hist.size()) throw std::invalid_argument("nearest_emd: centroid width differs from the histogram");
        return nearest_emd(centroids, hist.data(), static_cast<int>(hist.size()));
    }, nb::arg("centroids"), nb::arg("hist"), "Nearest centroid under 1-D earth mover's distance.");

    m.def("board_texture", [](const std::vector<int>& board) {
        return Abstraction::board_texture(board.data(), static_cast<int>(board.size()));
    }, nb::arg("board"), "Board texture class, mirroring abstraction.buckets.board_texture.");

    nb::class_<BucketTable>(m, "BucketTable",
        "Precomputed postflop buckets keyed by suit-isomorphic canonical form (bucket_table.hpp).")
        .def("__init__", [](BucketTable* self, nb::ndarray<nb::numpy, const uint64_t, nb::ndim<1>> keys,
                            nb::ndarray<nb::numpy, const uint8_t, nb::ndim<1>> buckets) {
            if (keys.shape(0) != buckets.shape(0)) throw std::invalid_argument("BucketTable: keys and buckets differ in length");
            new (self) BucketTable();
            self->keys.assign(keys.data(), keys.data() + keys.shape(0));
            self->buckets.assign(buckets.data(), buckets.data() + buckets.shape(0));
            if (!std::is_sorted(self->keys.begin(), self->keys.end())) throw std::invalid_argument("BucketTable: keys must be sorted");
        }, nb::arg("keys"), nb::arg("buckets"))
        .def("__len__", [](const BucketTable& t) { return t.keys.size(); })
        .def("lookup", [](const BucketTable& t, const std::vector<int>& hole, const std::vector<int>& board) {
            if (hole.size() != 2 || board.size() < 3 || board.size() > 4)
                throw std::invalid_argument("BucketTable.lookup: two hole cards and a flop or turn board");
            return t.lookup(hole.data(), board.data(), static_cast<int>(board.size()));
        }, nb::arg("hole"), nb::arg("board"), "The bucket without texture, or -1 when the situation is not in the table.")
        .def("keys", [](const BucketTable& t) {
            uint64_t* out = new uint64_t[t.keys.size()];
            std::copy(t.keys.begin(), t.keys.end(), out);
            nb::capsule own(out, [](void* p) noexcept { delete[] static_cast<uint64_t*>(p); });
            return nb::ndarray<nb::numpy, uint64_t, nb::ndim<1>>(out, {t.keys.size()}, own);
        })
        .def("buckets", [](const BucketTable& t) {
            uint8_t* out = new uint8_t[t.buckets.size()];
            std::copy(t.buckets.begin(), t.buckets.end(), out);
            nb::capsule own(out, [](void* p) noexcept { delete[] static_cast<uint8_t*>(p); });
            return nb::ndarray<nb::numpy, uint8_t, nb::ndim<1>>(out, {t.buckets.size()}, own);
        });

    m.def("canonical_key", [](const std::vector<int>& hole, const std::vector<int>& board) {
        if (hole.size() != 2 || board.size() > 5) throw std::invalid_argument("canonical_key: two hole cards, at most five board cards");
        return canonical_key(hole.data(), board.data(), static_cast<int>(board.size()));
    }, nb::arg("hole"), nb::arg("board"), "The smallest packing of the cards over all suit permutations.");

    m.def("build_bucket_table", [](int board_n, const std::vector<std::vector<double>>& centroids,
                                   int bins, int runouts, int opponents, int threads) {
        if (board_n < 3 || board_n > 4) throw std::invalid_argument("build_bucket_table: board_n is 3 (flop) or 4 (turn)");
        if (bins < 1 || bins > 64 || runouts < 1 || opponents < 1) throw std::invalid_argument("build_bucket_table: bins 1 to 64, runouts and opponents at least 1");
        if (centroids.empty() || centroids.size() > 255) throw std::invalid_argument("build_bucket_table: 1 to 255 centroids");
        for (const auto& row : centroids)
            if (static_cast<int>(row.size()) != bins) throw std::invalid_argument("build_bucket_table: a centroid row is not bins wide");
        BucketTable table;
        {
            nb::gil_scoped_release release;
            table = build_bucket_table(board_n, centroids, bins, runouts, opponents, std::max(threads, 1));
        }
        return table;
    }, nb::arg("board_n"), nb::arg("centroids"), nb::arg("bins"), nb::arg("runouts"), nb::arg("opponents"), nb::arg("threads") = 1,
       "Every canonical situation's bucket for one street; minutes for the flop, tens of minutes for the turn.");

    nb::class_<RiverSolver>(m, "RiverSolver",
        "The river re-solver's CFR+ core (river.hpp); the tree and ranges come from cfr/river.py.")
        .def("__init__", [](RiverSolver* self, const std::vector<int>& pairs_a, const std::vector<int>& pairs_b,
                            const std::vector<int64_t>& ranks, const std::vector<int>& kind,
                            const std::vector<int>& player, const std::vector<int>& contrib0,
                            const std::vector<int>& contrib1, const std::vector<int>& folder,
                            const std::vector<std::vector<int>>& children,
                            const std::vector<std::vector<int>>& actions,
                            const std::vector<double>& range0, const std::vector<double>& range1) {
            const size_t H = ranks.size(), N = kind.size();
            if (pairs_a.size() != H || pairs_b.size() != H || range0.size() != H || range1.size() != H)
                throw std::invalid_argument("RiverSolver: pairs, ranks and ranges must all have one entry per hand");
            if (player.size() != N || contrib0.size() != N || contrib1.size() != N || folder.size() != N ||
                children.size() != N || actions.size() != N)
                throw std::invalid_argument("RiverSolver: every node array must have one entry per node");
            if (N == 0 || kind[0] != 0) throw std::invalid_argument("RiverSolver: node 0 must be the root decision");
            for (size_t n = 0; n < N; ++n) {
                if (kind[n] == 0 && (children[n].empty() || children[n].size() != actions[n].size()))
                    throw std::invalid_argument("RiverSolver: a decision node needs one action per child");
                for (int c : children[n])
                    if (c <= static_cast<int>(n) || c >= static_cast<int>(N))
                        throw std::invalid_argument("RiverSolver: children must come after their parent");
            }
            RiverTree tree{kind, player, contrib0, contrib1, folder, children, actions};
            new (self) RiverSolver(pairs_a, pairs_b, ranks, std::move(tree), range0, range1);
        }, nb::arg("pairs_a"), nb::arg("pairs_b"), nb::arg("ranks"), nb::arg("kind"), nb::arg("player"),
           nb::arg("contrib0"), nb::arg("contrib1"), nb::arg("folder"), nb::arg("children"), nb::arg("actions"),
           nb::arg("range0"), nb::arg("range1"))
        .def("solve", [](RiverSolver& s, int iterations, double budget_s) {
            nb::gil_scoped_release release;
            return s.solve(iterations, budget_s);
        }, nb::arg("iterations"), nb::arg("budget_s"))
        .def("iterations", &RiverSolver::iterations)
        .def("root_strategy", &RiverSolver::root_strategy, nb::arg("hand"));

    nb::class_<MCCFR<NoLimitGame>>(m, "NoLimitSolver")
        .def("__init__", [](MCCFR<NoLimitGame>* self,
                            const std::vector<int>& preflop,
                            const std::vector<double>& flop,
                            const std::vector<double>& turn,
                            const std::vector<double>& river,
                            int equity_samples, int starting_stack,
                            int small_blind, int big_blind,
                            const std::vector<int>& schedule, uint64_t seed,
                            bool texture, const std::string& rule,
                            const std::vector<std::vector<std::vector<double>>>& hist_centroids,
                            int hist_bins, int hist_runouts, int hist_opponents,
                            const BucketTable* flop_table, const BucketTable* turn_table) {
            Abstraction abstraction;
            if (flop_table) abstraction.hist_tables[0] = *flop_table;
            if (turn_table) abstraction.hist_tables[1] = *turn_table;
            abstraction.preflop.assign(preflop.begin(), preflop.end());
            abstraction.centroids = {flop, turn, river};
            abstraction.equity_samples = equity_samples;
            abstraction.texture = texture;
            if (!hist_centroids.empty()) {
                if (hist_centroids.size() != 3) throw std::invalid_argument("hist_centroids: one list per postflop street");
                if (hist_bins < 1 || hist_bins > 64) throw std::invalid_argument("hist_bins must be 1 to 64");
                if (hist_runouts < 1 || hist_opponents < 1) throw std::invalid_argument("hist_runouts and hist_opponents must be at least 1");
                for (size_t i = 0; i < 3; ++i) {
                    if (hist_centroids[i].empty()) throw std::invalid_argument("hist_centroids: a street has no centroids");
                    for (const auto& row : hist_centroids[i])
                        if (static_cast<int>(row.size()) != hist_bins)
                            throw std::invalid_argument("hist_centroids: a centroid row is not hist_bins wide");
                }
                for (size_t i = 0; i < 3; ++i) abstraction.hist_centroids[i] = hist_centroids[i];
                abstraction.hist_bins = hist_bins;
                abstraction.hist_runouts = hist_runouts;
                abstraction.hist_opponents = hist_opponents;
            }
            RaiseSchedule sched;
            for (int n : schedule) sched.sizes.push_back(n);
            new (self) MCCFR<NoLimitGame>(
                NoLimitGame(std::move(abstraction), starting_stack, small_blind,
                            big_blind, std::move(sched)),
                UpdateRule::from_name(rule), seed);
        }, nb::arg("preflop"), nb::arg("flop"), nb::arg("turn"), nb::arg("river"),
           nb::arg("equity_samples"), nb::arg("starting_stack"),
           nb::arg("small_blind"), nb::arg("big_blind"), nb::arg("schedule"),
           nb::arg("seed"), nb::arg("texture") = false, nb::arg("rule") = "vanilla",
           nb::arg("hist_centroids") = std::vector<std::vector<std::vector<double>>>{},
           nb::arg("hist_bins") = 20, nb::arg("hist_runouts") = 100, nb::arg("hist_opponents") = 50,
           nb::arg("flop_table").none() = nullptr, nb::arg("turn_table").none() = nullptr)
        .def("set_common_random_numbers", [](MCCFR<NoLimitGame>& s, bool on) { s.game().set_common_random_numbers(on); },
             nb::arg("on"), "One deal per iteration shared across every branch (variance reduction); off by default.")
        .def("set_exact_terminals", [](MCCFR<NoLimitGame>& s, bool on) { s.game().set_exact_terminals(on); },
             nb::arg("on"), "Score flop and turn all-ins over every runout instead of one sample; off by default.")
        .def("set_current_when_empty", &MCCFR<NoLimitGame>::set_current_when_empty, nb::arg("on"),
             "Export the current strategy where the average is empty, instead of a uniform; off by default.")
        .def("set_average_from", &MCCFR<NoLimitGame>::set_average_from, nb::arg("iteration"),
             "Accumulate the average strategy only from this iteration on (0: from the start).")
        .def("warm_start", &MCCFR<NoLimitGame>::warm_start, nb::arg("entries"), nb::arg("weight"), nb::arg("scale"),
             nb::arg("mode") = "proportional",
             "Seed nodes from a coarser game's strategy, [(key, probabilities)]: `proportional` sets regrets "
             "to the prior at `weight` iterations of `scale` chips; `frozen` plays the prior for `weight` "
             "iterations while regrets accumulate (sampled substitute regrets); see MCCFR::warm_start.")
        .def("set_pruning", &MCCFR<NoLimitGame>::set_pruning, nb::arg("after"), nb::arg("threshold"), nb::arg("fraction") = 0.95,
             "Regret-based pruning from iteration `after`: on `fraction` of iterations skip actions with "
             "regret below `threshold` chips (never on the river, never an action that ends the hand).")
        .def("pruned", &MCCFR<NoLimitGame>::pruned, "Action visits skipped so far.")
        .def("warm_entries", &MCCFR<NoLimitGame>::warm_entries)
        .def("warm_hits", &MCCFR<NoLimitGame>::warm_hits, "Nodes created so far that took a warm entry.")
        .def("train", &MCCFR<NoLimitGame>::train, nb::arg("iterations"), nb::arg("threads") = 1,
             nb::call_guard<nb::gil_scoped_release>(),
             "Run `iterations` passes, each traversing once per player, over `threads` workers "
             "sharing the table (1: the exact single-threaded path).")
        .def("iterations", &MCCFR<NoLimitGame>::iterations)
        .def("information_sets", [](const MCCFR<NoLimitGame>& s) { return s.size(); })
        .def("average_strategy", [](const MCCFR<NoLimitGame>& solver) {
            std::map<std::string, std::vector<double>> out;
            solver.for_each_node([&](uint64_t key, const InfoSetNode& node) {
                out[solver.key_string(key)] = solver.strategy_for_export(node);
            });
            return out;
        }, "Information-set key -> action probabilities, as the Python returns.")
        .def("average_strategy_flat", [](const MCCFR<NoLimitGame>& solver, int key_width) {
            // The same strategy as three arrays: keys zero-padded to
            // `key_width` bytes and sorted, row offsets, and one values array.
            // The map export built a red-black tree of strings and vectors,
            // then a dict, then millions of numpy arrays: about a gigabyte of
            // transient memory per write on a big rung, which twice put this
            // machine into the state where the harness kills jobs.
            std::vector<std::pair<std::string, const InfoSetNode*>> keys;
            keys.reserve(solver.size());
            solver.for_each_node([&](uint64_t key, const InfoSetNode& node) {
                keys.emplace_back(solver.key_string(key), &node);
            });
            std::sort(keys.begin(), keys.end(),
                      [](const auto& a, const auto& b) { return a.first < b.first; });
            const size_t n = keys.size();
            size_t total = 0;
            for (const auto& k : keys) {
                if (static_cast<int>(k.first.size()) > key_width)
                    throw std::invalid_argument("information-set key longer than key_width: " + k.first);
                total += static_cast<size_t>(k.second->num_actions);
            }
            uint8_t* key_bytes = new uint8_t[n * static_cast<size_t>(key_width)]();
            int64_t* offsets = new int64_t[n + 1];
            double* values = new double[total];
            size_t at = 0;
            offsets[0] = 0;
            for (size_t i = 0; i < n; ++i) {
                const std::string& k = keys[i].first;
                std::memcpy(key_bytes + i * static_cast<size_t>(key_width), k.data(), k.size());
                const std::vector<double> row = solver.strategy_for_export(*keys[i].second);
                for (double v : row) values[at++] = v;
                offsets[i + 1] = static_cast<int64_t>(at);
            }
            nb::capsule own_keys(key_bytes, [](void* p) noexcept { delete[] static_cast<uint8_t*>(p); });
            nb::capsule own_offsets(offsets, [](void* p) noexcept { delete[] static_cast<int64_t*>(p); });
            nb::capsule own_values(values, [](void* p) noexcept { delete[] static_cast<double*>(p); });
            return nb::make_tuple(
                nb::ndarray<nb::numpy, uint8_t, nb::ndim<2>>(key_bytes, {n, static_cast<size_t>(key_width)}, own_keys),
                nb::ndarray<nb::numpy, int64_t, nb::ndim<1>>(offsets, {n + 1}, own_offsets),
                nb::ndarray<nb::numpy, double, nb::ndim<1>>(values, {total}, own_values));
        }, nb::arg("key_width") = 32,
           "The average strategy as (keys as an (n, key_width) uint8 array, sorted; int64 offsets; float64 values).");
}
