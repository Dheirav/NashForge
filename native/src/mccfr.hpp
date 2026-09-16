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
#include <cstdint>
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

template <typename Game>
class MCCFR {
public:
    MCCFR(Game game, UpdateRule rule, uint64_t seed)
        : game_(std::move(game)), rule_(rule), rng_(seed) {
    }

    void train(int64_t iterations) {
        for (int64_t i = 0; i < iterations; ++i) {
            for (int player = 0; player < Game::num_players; ++player)
                walk(game_.initial_state(), player);
            ++iterations_;
        }
    }

    const std::unordered_map<std::string, InfoSetNode>& nodes() const { return nodes_; }
    int64_t iterations() const { return iterations_; }

private:
    double walk(const typename Game::State& state, int traverser) {
        if (game_.is_terminal(state)) return game_.utility(state, traverser);

        if (game_.is_chance(state))
            return walk(game_.sample_chance(state, rng_), traverser);

        const int player = game_.current_player(state);
        const std::vector<int8_t> actions = game_.legal_actions(state);
        const std::string key = game_.information_set(state, player);

        auto it = nodes_.find(key);
        if (it == nodes_.end())
            it = nodes_.emplace(key, InfoSetNode{static_cast<int>(actions.size()), {}, {}, 0}).first;
        InfoSetNode& node = it->second;

        double strategy[MAX_ACTIONS];
        node.strategy(strategy);

        if (player != traverser) {
            // Opponent: sample one action and accumulate their average strategy
            // here, where the reach weighting is correct.
            discount_once(node, iterations_ + 1);
            const double weight = rule_.strategy_weight(iterations_ + 1);
            for (size_t i = 0; i < actions.size(); ++i)
                node.strategy_sum[i] += weight * strategy[i];
            return walk(game_.next_state(state, actions[sample(strategy, actions.size())]),
                        traverser);
        }

        double values[MAX_ACTIONS];
        double value = 0.0;
        for (size_t i = 0; i < actions.size(); ++i) {
            values[i] = walk(game_.next_state(state, actions[i]), traverser);
            value += strategy[i] * values[i];
        }

        // No refetch: a rehash of `unordered_map` invalidates iterators, not
        // references to elements, so `node` is still the node. The refetch
        // hashed every key a second time per traverser visit.
        InfoSetNode& current = node;
        discount_once(current, iterations_ + 1);
        double regret[MAX_ACTIONS];
        for (size_t i = 0; i < actions.size(); ++i) regret[i] = values[i] - value;
        rule_.add_regret(current, regret);
        return value;
    }

    void discount_once(InfoSetNode& node, int64_t iteration) {
        // At most once per node per iteration. A sampler reaches the same
        // information set repeatedly within one iteration, and decaying on every
        // visit compounds the schedule an unpredictable number of times.
        if (node.last_discounted != iteration) {
            rule_.discount(node, iteration);
            node.last_discounted = iteration;
        }
    }

    size_t sample(const double* probabilities, size_t n) {
        const double draw = static_cast<double>(rng_.next() >> 11) * 0x1.0p-53;
        double cumulative = 0.0;
        for (size_t i = 0; i < n; ++i) {
            cumulative += probabilities[i];
            if (draw < cumulative) return i;
        }
        return n - 1;
    }

    Game game_;
    UpdateRule rule_;
    Rng rng_;
    std::unordered_map<std::string, InfoSetNode> nodes_;
    int64_t iterations_ = 0;
};

}  // namespace pokerbot
