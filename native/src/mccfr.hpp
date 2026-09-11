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
#include <cstdint>
#include <array>
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

    void discount(InfoSetNode& node, int64_t iteration) const {
        const double t = static_cast<double>(iteration);
        if (!std::isnan(alpha) || !std::isnan(beta)) {
            for (int i = 0; i < node.num_actions; ++i) {
                double& r = node.regret_sum[static_cast<size_t>(i)];
                if (r > 0.0 && !std::isnan(alpha))
                    r *= std::pow(t, alpha) / (std::pow(t, alpha) + 1.0);
                else if (r < 0.0 && !std::isnan(beta))
                    r *= std::pow(t, beta) / (std::pow(t, beta) + 1.0);
            }
        }
        if (!std::isnan(gamma)) {
            const double factor = std::pow(t / (t + 1.0), gamma);
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
        : game_(std::move(game)), rule_(rule), rng_(seed) {}

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

        // Refetch: `nodes_` may have rehashed during the recursion above, which
        // would leave the reference dangling. This is the kind of thing Python's
        // dict hid for free and C++ does not.
        InfoSetNode& current = nodes_.find(key)->second;
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
