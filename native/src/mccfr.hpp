// External-sampling MCCFR, ported from cfr/mccfr.py.
//
// Templated on the game rather than virtual-dispatched: the traversal floor was
// 40.5% of a Python iteration and the whole point of the port is to remove it,
// so a virtual call per node would give back much of what we came for.
//
// Validated against Kuhn poker's analytically known value of -1/18. That is a
// stronger test than comparing against our own Python, because it checks the
// algorithm rather than the translation.
#pragma once
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>
#include <functional>
#include <array>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <cmath>
#include "equity.hpp"   // Rng

namespace pokerbot {

constexpr int MAX_ACTIONS = 6;

struct InfoSetNode {
    int num_actions = 0;
    std::array<double, MAX_ACTIONS> regret_sum{};
    std::array<double, MAX_ACTIONS> strategy_sum{};
    int64_t last_discounted = 0;
    // One byte of spinlock, taken only when the solver runs threads: a node's
    // update is a read-modify-write of a dozen doubles, and two traversers
    // meeting at the same node would otherwise lose each other's regret.
    // The atomic makes the struct non-copyable, hence the constructors.
    std::atomic<uint8_t> busy{0};

    InfoSetNode() = default;
    explicit InfoSetNode(int actions) : num_actions(actions) {}
    InfoSetNode(const InfoSetNode& o)
        : num_actions(o.num_actions), regret_sum(o.regret_sum),
          strategy_sum(o.strategy_sum), last_discounted(o.last_discounted) {}

    void lock() { while (busy.exchange(1, std::memory_order_acquire)) { /* spin: held for nanoseconds */ } }
    void unlock() { busy.store(0, std::memory_order_release); }

    /// Regret matching: play in proportion to positive cumulative regret,
    /// uniformly when none is positive.
    void strategy(double* out) const {
        double total = 0.0;
        for (int i = 0; i < num_actions; ++i) {
            out[i] = regret_sum[static_cast<size_t>(i)] > 0.0
                   ? regret_sum[static_cast<size_t>(i)] : 0.0;
            total += out[i];
        }
        if (total > 0.0) {
            for (int i = 0; i < num_actions; ++i) out[i] /= total;
        } else {
            const double uniform = 1.0 / num_actions;
            for (int i = 0; i < num_actions; ++i) out[i] = uniform;
        }
    }

    /// The strategy that converges: the reach-weighted average, not the latest.
    std::vector<double> average_strategy() const {
        std::vector<double> out(static_cast<size_t>(num_actions));
        double total = 0.0;
        for (int i = 0; i < num_actions; ++i) total += strategy_sum[static_cast<size_t>(i)];
        if (total > 0.0)
            for (int i = 0; i < num_actions; ++i)
                out[static_cast<size_t>(i)] = strategy_sum[static_cast<size_t>(i)] / total;
        else
            for (int i = 0; i < num_actions; ++i)
                out[static_cast<size_t>(i)] = 1.0 / num_actions;
        return out;
    }
};

/// A regret and strategy accumulation schedule; see cfr/updates.py.
struct UpdateRule {
    bool floor_regret = false;
    double alpha = NAN, beta = NAN, gamma = NAN;
    bool linear_strategy = false;

    static UpdateRule vanilla() { return {}; }
    static UpdateRule linear()  { UpdateRule r; r.alpha = 1; r.beta = 1; r.gamma = 1; return r; }
    // The other two schedules `cfr/updates.py` defines, with its parameters, so
    // a rule chosen on the Python path means the same thing on this one.
    static UpdateRule cfr_plus() { UpdateRule r; r.floor_regret = true; r.linear_strategy = true; return r; }
    static UpdateRule dcfr()     { UpdateRule r; r.alpha = 1.5; r.beta = 0.0; r.gamma = 2.0; return r; }

    /// By the names `cfr/updates.py` uses. Exposed because the vanilla average
    /// strategy is unweighted: at a node its owner rarely reaches, the early
    /// near-uniform visits weigh as much as the converged ones, and a fine
    /// preflop abstraction stayed at 50/50 facing a shove after 3M iterations.
    static UpdateRule from_name(const std::string& name) {
        if (name == "vanilla") return vanilla();
        if (name == "linear")  return linear();
        if (name == "cfr+")    return cfr_plus();
        if (name == "dcfr")    return dcfr();
        throw std::invalid_argument("unknown update rule: " + name + " (vanilla, linear, cfr+, dcfr)");
    }

    /// The product of the per-iteration factor u^e / (u^e + 1) over the
    /// iterations this node was NOT visited, (last, now]. The schedules are
    /// defined per iteration of the algorithm, but a sampled node is only
    /// touched when the sampler reaches it; applying one iteration's factor
    /// per visit left a node visited at 1 and at 1,000,000 with a factor of
    /// 0.999999 instead of 0.000002, so at rarely reached nodes every rule
    /// collapsed to vanilla. Exact for e = 1 (the product telescopes to
    /// (last + 1) / (now + 1)); for other exponents the log of the product is
    /// approximated by the integral of -u^-e, which is within 1e-3 for e >= 1.
    static double cumulative(double exponent, int64_t last, int64_t now) {
        if (now <= last) return 1.0;
        if (exponent == 1.0)
            return static_cast<double>(last + 1) / static_cast<double>(now + 1);
        if (exponent == 0.0) return std::pow(0.5, static_cast<double>(now - last));
        // Exact over the first 64 iterations of the gap, which is the whole gap
        // for every node a dense traversal touches; the tail, where only the
        // sampled rare nodes go, uses the integral of log(u^e / (u^e + 1)) to
        // second order, within 1e-3 of the product for e >= 1.
        double product = 1.0;
        const int64_t head = std::min(now, last + 64);
        for (int64_t u = last + 1; u <= head; ++u) {
            const double p = std::pow(static_cast<double>(u), exponent);
            product *= p / (p + 1.0);
        }
        if (head < now) {
            const double a = static_cast<double>(head) + 0.5, b = static_cast<double>(now) + 0.5;
            const double first = (std::pow(a, 1.0 - exponent) - std::pow(b, 1.0 - exponent)) / (exponent - 1.0);
            const double second = (std::pow(a, 1.0 - 2.0 * exponent) - std::pow(b, 1.0 - 2.0 * exponent)) / (2.0 * exponent - 1.0);
            product *= std::exp(-first + second / 2.0);
        }
        return product;
    }

    void discount(InfoSetNode& node, int64_t iteration) const {
        const int64_t last = node.last_discounted;
        if (!std::isnan(alpha) || !std::isnan(beta)) {
            const double up = std::isnan(alpha) ? 1.0 : cumulative(alpha, last, iteration);
            const double down = std::isnan(beta) ? 1.0 : cumulative(beta, last, iteration);
            for (int i = 0; i < node.num_actions; ++i) {
                double& r = node.regret_sum[static_cast<size_t>(i)];
                if (r > 0.0) r *= up;
                else if (r < 0.0) r *= down;
            }
        }
        if (!std::isnan(gamma)) {
            const double factor = std::pow(cumulative(1.0, last, iteration), gamma);
            for (int i = 0; i < node.num_actions; ++i)
                node.strategy_sum[static_cast<size_t>(i)] *= factor;
        }
    }

    double strategy_weight(int64_t iteration) const {
        return linear_strategy ? static_cast<double>(iteration) : 1.0;
    }

    void add_regret(InfoSetNode& node, const double* regret) const {
        for (int i = 0; i < node.num_actions; ++i) {
            double& r = node.regret_sum[static_cast<size_t>(i)];
            r += regret[i];
            if (floor_regret && r < 0.0) r = 0.0;
        }
    }
};

/// Hash for the packed keys: a 64-bit mix, since consecutive keys differ in
/// their low bits and the standard identity hash would cluster them.
template <typename K>
struct KeyHash {
    size_t operator()(const K& k) const { return std::hash<K>{}(k); }
};
template <>
struct KeyHash<uint64_t> {
    size_t operator()(uint64_t x) const {
        x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ULL;
        x ^= x >> 27; x *= 0x94d049bb133111ebULL;
        x ^= x >> 31;
        return static_cast<size_t>(x);
    }
};

template <typename Game>
class MCCFR {
public:
    using Key = typename Game::Key;
    MCCFR(Game game, UpdateRule rule, uint64_t seed)
        : game_(std::move(game)), rule_(rule), rng_(seed), seed_(seed) {
        shards_.reserve(SHARDS);
        for (int i = 0; i < SHARDS; ++i) shards_.push_back(std::make_unique<Shard>());
    }
    // Shards own mutexes, so the solver moves but does not copy; nanobind
    // consults the trait, and vector<unique_ptr> claims to be copyable.
    MCCFR(const MCCFR&) = delete;
    MCCFR& operator=(const MCCFR&) = delete;
    MCCFR(MCCFR&&) = default;

    /// Accumulate the average strategy only from this iteration on. Pluribus
    /// stored no average for the first part of its run and Modicum ignores the
    /// first half of a subgame's iterations: the early visits are the uniform
    /// ones, and at a rarely reached node they are most of what the average
    /// ever sees. Zero, the default, is the classical average.
    void set_average_from(int64_t iteration) { average_from_ = iteration; }

    /// Warm start from a strategy of a coarser game on the same histories
    /// (Brown and Sandholm 2016, in the plain form): when a node whose key is
    /// in `entries` is first created, its regrets are set proportional to the
    /// given probabilities, so regret matching reproduces that strategy, at a
    /// magnitude of `weight` iterations times `scale` chips, and its discount
    /// stamp and the iteration counter start at `weight`, so the schedules
    /// treat the prior as `weight` iterations already played. Actions the
    /// coarser game lacked (the re-raises) start at zero regret and are
    /// learnt from there; the coarser game's action list must be a prefix
    /// of this game's at the shared node, which holds for a one-raise tree
    /// inside a cap-2 tree because both list fold, call, then the sizes.
    /// Why: at 50M iterations a cap-2 rung was still 12.7 BB/100 behind the
    /// one-raise rung at the same depth, most of that budget spent learning
    /// the ordinary game on a tree five times bigger; the one-raise pickle
    /// already holds that part. Nothing changes when no entries are given.
    ///
    /// Two modes. "proportional": regrets are set to the prior's probabilities
    /// times `weight * scale` when the node is created, and the counter starts
    /// at `weight`; measured worth about 1.6x on a cap-2 rung, because the new
    /// actions start at zero and the prior says nothing about them. "frozen":
    /// Brown and Sandholm's substitute regrets, sampled. For the first `weight`
    /// iterations every node plays the prior (uniform where the prior has no
    /// entry) instead of regret matching, and regrets accumulate as usual, so
    /// at the end each node holds `weight` iterations of measured regret
    /// against the prior, including for the actions the prior never took;
    /// then regret matching takes over. `scale` is unused in that mode. The
    /// average is not accumulated during the frozen phase; the trainer sets
    /// `average_from` past it.
    void warm_start(const std::vector<std::pair<std::string, std::vector<double>>>& entries,
                    int64_t weight, double scale, const std::string& mode = "proportional") {
        warm_.clear();
        for (const auto& e : entries) {
            if (e.second.size() > static_cast<size_t>(MAX_ACTIONS))
                throw std::invalid_argument("warm start entry wider than MAX_ACTIONS: " + e.first);
            warm_.emplace(Game::key_from_string(e.first), e.second);
        }
        warm_weight_ = weight;
        warm_scale_ = scale;
        if (mode == "proportional") {
            frozen_until_ = 0;
            if (weight > iterations_) iterations_ = weight;
        } else if (mode == "frozen") {
            frozen_until_ = iterations_ + weight;
        } else {
            throw std::invalid_argument("warm start mode: proportional or frozen, not " + mode);
        }
    }
    /// Regret-based pruning (Brown and Sandholm 2015, 2017; Pluribus's form).
    /// From iteration `after`, on a `fraction` of iterations the traverser
    /// skips any action whose cumulative regret is below `threshold` chips,
    /// unless it ends the hand or the node is on the final street; skipped
    /// actions get no value and no regret update that iteration. The other
    /// iterations traverse everything, so a pruned action that has become
    /// good is found again. Off until called: the golden path draws no extra
    /// random number.
    void set_pruning(int64_t after, double threshold, double fraction) {
        prune_after_ = after;
        prune_threshold_ = threshold;
        prune_fraction_ = fraction;
    }
    size_t pruned() const { return pruned_.load(); }
    size_t warm_entries() const { return warm_.size(); }
    size_t warm_hits() const { return warm_hits_.load(); }

    /// `threads` workers share the node table and split the iterations. One
    /// thread is the original path, bit for bit (the golden test pins it).
    /// More than one is Pluribus's arrangement: every worker traverses with
    /// its own deal and random stream, and the table is the only shared
    /// state, guarded by a lock per node for the update and a lock per shard
    /// for insertion. Which worker gets which iteration is not deterministic,
    /// so a threaded run is reproducible only in distribution.
    void train(int64_t iterations, int threads = 1) {
        if (threads <= 1) {
            Context main{&game_, &rng_};
            for (int64_t i = 0; i < iterations; ++i) {
                run_iteration(main, iterations_ + 1);
                ++iterations_;
            }
            return;
        }
        // Worker games are copies of the main one, taken now so they carry
        // the flags set since the last call; only the random streams persist.
        while (worker_rngs_.size() < static_cast<size_t>(threads - 1)) {
            const uint64_t k = static_cast<uint64_t>(worker_rngs_.size()) + 1;
            worker_rngs_.emplace_back(seed_ ^ (KeyHash<uint64_t>{}(k) | 1));
        }
        std::vector<Game> games(static_cast<size_t>(threads - 1), game_);
        std::atomic<int64_t> next{iterations_};
        const int64_t end = iterations_ + iterations;
        parallel_ = true;
        auto work = [&](Context ctx) {
            for (;;) {
                const int64_t i = next.fetch_add(1);
                if (i >= end) return;
                run_iteration(ctx, i + 1);
            }
        };
        std::vector<std::thread> pool;
        for (int t = 1; t < threads; ++t)
            pool.emplace_back(work, Context{&games[static_cast<size_t>(t - 1)], &worker_rngs_[static_cast<size_t>(t - 1)]});
        work(Context{&game_, &rng_});
        for (auto& th : pool) th.join();
        parallel_ = false;
        iterations_ = end;
    }

    Game& game() { return game_; }

    /// Export regret matching's current strategy at a node whose strategy sum
    /// is zero, instead of a uniform. Such nodes exist: created while their
    /// owner was the traverser and never entered as the opponent, so they
    /// have regrets but no average. The uniform is what put every 169-class
    /// preflop solver at exactly 50/50 facing a shove. Pluribus plays the
    /// final iteration in search for the same reason. Off by default.
    void set_current_when_empty(bool on) { current_when_empty_ = on; }

    /// A fixed policy for the opponent's nodes (archetype.hpp): given the
    /// state, the player to act and the legal actions, the action it takes.
    /// With one installed the traversal learns a best response to it rather
    /// than an equilibrium, and the opponent's nodes are neither updated nor
    /// created. Both seats learn, since each iteration traverses each seat
    /// as "us" against the policy in the other.
    using OpponentPolicy = std::function<int8_t(const typename Game::State&, int, const std::vector<int8_t>&, Rng&)>;
    void set_opponent_policy(OpponentPolicy policy) { opponent_policy_ = std::move(policy); }
    bool has_opponent_policy() const { return static_cast<bool>(opponent_policy_); }

    std::vector<double> strategy_for_export(const InfoSetNode& node) const {
        if (current_when_empty_) {
            double total = 0.0;
            for (int i = 0; i < node.num_actions; ++i) total += node.strategy_sum[static_cast<size_t>(i)];
            if (total <= 0.0) {
                double current[MAX_ACTIONS];
                node.strategy(current);
                return std::vector<double>(current, current + node.num_actions);
            }
        }
        return node.average_strategy();
    }

    /// Visit every node; the order is the shards' and means nothing.
    template <typename F>
    void for_each_node(F&& f) const {
        for (const auto& shard : shards_)
            for (const auto& kv : shard->map) f(kv.first, kv.second);
    }
    size_t size() const {
        size_t n = 0;
        for (const auto& shard : shards_) n += shard->map.size();
        return n;
    }
    std::string key_string(const Key& key) const { return Game::key_to_string(key); }
    int64_t iterations() const { return iterations_; }

private:
    struct Context { Game* game; Rng* rng; bool pruning = false; };

    // The table is sharded so that insertion, the one operation that changes
    // the map's structure, locks a 1/256th of it rather than all of it. A
    // node's address is stable across rehashes (the standard promises that
    // for unordered_map elements), so a reference taken under the shard lock
    // stays good after it.
    static constexpr int SHARDS = 256;
    struct Shard {
        std::mutex mutex;
        std::unordered_map<Key, InfoSetNode, KeyHash<Key>> map;
    };

    void run_iteration(Context& ctx, int64_t iteration) {
        ctx.game->begin_iteration(*ctx.rng);          // one deal, shared by both traversers
        ctx.pruning = prune_after_ >= 0 && iteration > prune_after_
                   && static_cast<double>(ctx.rng->next() >> 11) * 0x1.0p-53 < prune_fraction_;
        for (int player = 0; player < Game::num_players; ++player)
            walk(ctx, ctx.game->initial_state(), player, iteration);
    }

    InfoSetNode& node_for(const Key& key, int num_actions) {
        // The top bits pick the shard and the map hashes the whole key again;
        // using the same bits for both would put every node of a shard into a
        // few of its buckets.
        const size_t h = KeyHash<Key>{}(key);
        Shard& shard = *shards_[(h >> 24) % SHARDS];
        if (!parallel_) {
            auto made = shard.map.try_emplace(key, num_actions);
            if (made.second && !warm_.empty()) seed_node(key, made.first->second);
            return made.first->second;
        }
        std::lock_guard<std::mutex> guard(shard.mutex);
        auto made = shard.map.try_emplace(key, num_actions);
        if (made.second && !warm_.empty()) seed_node(key, made.first->second);
        return made.first->second;
    }

    /// The strategy to play at a node on this iteration: the prior while the
    /// frozen phase lasts, regret matching otherwise.
    void strategy_at(const Key& key, const InfoSetNode& node, int64_t iteration, double* out) {
        if (iteration <= frozen_until_) {
            auto it = warm_.find(key);
            const size_t n = static_cast<size_t>(node.num_actions);
            if (it == warm_.end()) {
                for (size_t i = 0; i < n; ++i) out[i] = 1.0 / static_cast<double>(n);
            } else {
                const std::vector<double>& p = it->second;
                double total = 0.0;
                for (size_t i = 0; i < n; ++i) { out[i] = i < p.size() ? p[i] : 0.0; total += out[i]; }
                if (total > 0.0) for (size_t i = 0; i < n; ++i) out[i] /= total;
                else for (size_t i = 0; i < n; ++i) out[i] = 1.0 / static_cast<double>(n);
            }
            return;
        }
        node.strategy(out);
    }

    /// The warm start, applied to a node the moment it exists. Done here and
    /// not up front because a node's action count is only known when the
    /// game reaches it, and creating every key in the table blind would put
    /// nodes in with the wrong width.
    void seed_node(const Key& key, InfoSetNode& node) {
        auto it = warm_.find(key);
        if (it == warm_.end()) return;
        warm_hits_.fetch_add(1, std::memory_order_relaxed);   // counted in both modes
        if (frozen_until_ > 0) return;                        // frozen: the prior is played, not seeded
        const std::vector<double>& p = it->second;
        const size_t n = std::min(p.size(), static_cast<size_t>(node.num_actions));
        const double magnitude = static_cast<double>(warm_weight_) * warm_scale_;
        // Regrets only. The average is left to accumulate from real play:
        // seeding it with the prior put a wrong prior into the exported
        // strategy for good under the vanilla rule (Kuhn stayed 0.007 off
        // after four times the prior's weight), while regrets alone let the
        // run overrule it and the average then reflects what was learnt.
        for (size_t i = 0; i < n; ++i) node.regret_sum[i] = p[i] * magnitude;
        node.last_discounted = warm_weight_;
    }

    double walk(Context& ctx, const typename Game::State& state, int traverser, int64_t iteration) {
        const Game& game = *ctx.game;
        if (game.is_terminal(state)) return game.utility(state, traverser);

        if (game.is_chance(state))
            return walk(ctx, game.sample_chance(state, *ctx.rng), traverser, iteration);

        const int player = game.current_player(state);
        const std::vector<int8_t> actions = game.legal_actions(state);
        if (player != traverser && opponent_policy_) {
            // A scripted opponent: its move comes from the policy, and no node
            // is touched, so the table holds only what "we" learned.
            const int8_t chosen = opponent_policy_(state, player, actions, *ctx.rng);
            return walk(ctx, game.next_state(state, chosen), traverser, iteration);
        }
        const Key key = game.information_set(state, player);
        InfoSetNode& node = node_for(key, static_cast<int>(actions.size()));

        double strategy[MAX_ACTIONS];
        if (player != traverser) {
            // Opponent: sample one action and accumulate their average strategy
            // here, where the reach weighting is correct.
            if (parallel_) node.lock();
            strategy_at(key, node, iteration, strategy);
            discount_once(node, iteration);
            const double weight = rule_.strategy_weight(iteration);
            if (iteration - 1 >= average_from_)
                for (size_t i = 0; i < actions.size(); ++i)
                    node.strategy_sum[i] += weight * strategy[i];
            if (parallel_) node.unlock();
            return walk(ctx, game.next_state(state, actions[sample(*ctx.rng, strategy, actions.size())]),
                        traverser, iteration);
        }

        if (parallel_) node.lock();
        strategy_at(key, node, iteration, strategy);
        if (parallel_) node.unlock();

        double values[MAX_ACTIONS];
        bool explored[MAX_ACTIONS];
        double value = 0.0;
        const bool may_prune = ctx.pruning && !game.is_final_street(state);
        for (size_t i = 0; i < actions.size(); ++i) {
            explored[i] = true;
            if (may_prune && node.regret_sum[i] < prune_threshold_) {
                const typename Game::State next = game.next_state(state, actions[i]);
                if (!game.is_terminal(next)) {        // an action that ends the hand is always explored
                    explored[i] = false;
                    values[i] = 0.0;                  // its strategy weight is zero: regret is negative
                    pruned_.fetch_add(1, std::memory_order_relaxed);
                    continue;
                }
            }
            values[i] = walk(ctx, game.next_state(state, actions[i]), traverser, iteration);
            value += strategy[i] * values[i];
        }

        double regret[MAX_ACTIONS];
        for (size_t i = 0; i < actions.size(); ++i) regret[i] = explored[i] ? values[i] - value : 0.0;
        if (parallel_) node.lock();
        discount_once(node, iteration);
        rule_.add_regret(node, regret);
        if (parallel_) node.unlock();
        return value;
    }

    void discount_once(InfoSetNode& node, int64_t iteration) {
        // At most once per node per iteration. A sampler reaches the same
        // information set repeatedly within one iteration, and decaying on every
        // visit compounds the schedule an unpredictable number of times. Under
        // threads the iterations reach a node slightly out of order; an older
        // one arriving after a newer one has already discounted is skipped
        // rather than rewinding the stamp, which would discount twice.
        if (iteration > node.last_discounted) {
            rule_.discount(node, iteration);
            node.last_discounted = iteration;
        }
    }

    static size_t sample(Rng& rng, const double* probabilities, size_t n) {
        const double draw = static_cast<double>(rng.next() >> 11) * 0x1.0p-53;
        double cumulative = 0.0;
        for (size_t i = 0; i < n; ++i) {
            cumulative += probabilities[i];
            if (draw < cumulative) return i;
        }
        return n - 1;
    }

    Game game_;
    OpponentPolicy opponent_policy_;
    UpdateRule rule_;
    Rng rng_;
    uint64_t seed_;
    std::vector<Rng> worker_rngs_;
    std::vector<std::unique_ptr<Shard>> shards_;
    int64_t iterations_ = 0;
    int64_t average_from_ = 0;
    std::unordered_map<Key, std::vector<double>, KeyHash<Key>> warm_;
    int64_t warm_weight_ = 0;
    double warm_scale_ = 1.0;
    int64_t frozen_until_ = 0;
    int64_t prune_after_ = -1;
    double prune_threshold_ = 0.0;
    double prune_fraction_ = 0.95;
    std::atomic<size_t> pruned_{0};
    std::atomic<size_t> warm_hits_{0};
    bool current_when_empty_ = false;
    bool parallel_ = false;
};

}  // namespace pokerbot
