// The no-limit game as MCCFR sees it: betting, dealing, bucketing, payoffs.
//
// `nolimit.hpp` holds the betting, which is pinned against the Python exactly.
// This adds the parts that involve cards, where the port deliberately does NOT
// match bit-for-bit: bucketing runs a Monte Carlo equity estimate seeded from
// the cards, and reproducing numba's generator would buy nothing. What is
// preserved is the structure -- the same abstraction, the same centroids, the
// same tie-breaking -- so the two produce the same distribution of buckets.
#pragma once
#include <cstdint>
#include <array>
#include <string>
#include <unordered_map>
#include <vector>
#include "nolimit.hpp"
#include "equity.hpp"

namespace pokerbot {

/// The fitted card abstraction, handed over from Python.
///
/// Passed as tables rather than refitted here: k-means over sampled equities is
/// cheap and happens once, and refitting in C++ would be a second clustering
/// that could silently disagree with the one every existing strategy was built
/// against.
struct Abstraction {
    /// bucket for each unordered hole pair, indexed [card][card].
    std::vector<int8_t> preflop;            // 52 * 52
    /// Sorted centroids for flop, turn, river.
    std::array<std::vector<double>, 3> centroids;
    int equity_samples = 40;

    /// Mirrors `_nearest_centroid`: bisect_left, ties to the lower index.
    static int nearest(const std::vector<double>& sorted, double value) {
        size_t position = 0;
        while (position < sorted.size() && sorted[position] < value) ++position;
        if (position == 0) return 0;
        if (position == sorted.size()) return static_cast<int>(sorted.size()) - 1;
        const double below = sorted[position - 1], above = sorted[position];
        return (above - value) < (value - below)
             ? static_cast<int>(position) : static_cast<int>(position) - 1;
    }
};

class NoLimitGame {
public:
    static constexpr int num_players = 2;

    struct State {
        pokerbot::State bet;                        // betting, from nolimit.hpp
        std::array<std::array<int8_t, 2>, 2> hole{};
    };

    NoLimitGame(Abstraction abstraction, int starting_stack, int small_blind,
                int big_blind, RaiseSchedule schedule)
        : abstraction_(std::move(abstraction)),
          betting_(starting_stack, small_blind, big_blind, std::move(schedule)) {}

    State initial_state() const {
        State s;
        s.bet = betting_.initial_state();
        return s;
    }

    bool is_chance(const State& s) const {
        if (!s.bet.dealt) return true;
        return betting_.current_player(s.bet) == CHANCE && !is_terminal(s);
    }

    bool is_terminal(const State& s) const { return betting_.is_terminal(s.bet); }
    int current_player(const State& s) const { return betting_.current_player(s.bet); }
    std::vector<int8_t> legal_actions(const State& s) const {
        return betting_.legal_actions(s.bet);
    }

    State next_state(const State& s, int8_t action) const {
        State next = s;
        next.bet = betting_.apply(s.bet, action);
        return next;
    }

    State sample_chance(const State& s, Rng& rng) const {
        State next = s;
        if (!s.bet.dealt) {
            int8_t deck[52];
            for (int i = 0; i < 52; ++i) deck[i] = static_cast<int8_t>(i);
            for (int i = 0; i < 4; ++i) {
                const int j = i + static_cast<int>(rng.below(static_cast<uint32_t>(52 - i)));
                const int8_t t = deck[i]; deck[i] = deck[j]; deck[j] = t;
            }
            next.hole[0] = {deck[0], deck[1]};
            next.hole[1] = {deck[2], deck[3]};
            next.bet.dealt = true;
            return next;
        }

        // Reveal the next street.
        const int street = s.bet.street + 1;
        const int needed = STREET_BOARD_SIZE[static_cast<size_t>(street)] - s.bet.board_n;
        int8_t board[5];
        for (int i = 0; i < s.bet.board_n; ++i) board[i] = s.bet.board[static_cast<size_t>(i)];

        bool used[52] = {false};
        for (int p = 0; p < 2; ++p)
            for (int i = 0; i < 2; ++i) used[s.hole[static_cast<size_t>(p)][static_cast<size_t>(i)]] = true;
        for (int i = 0; i < s.bet.board_n; ++i) used[s.bet.board[static_cast<size_t>(i)]] = true;

        int8_t pool[52];
        int pool_n = 0;
        for (int c = 0; c < 52; ++c) if (!used[c]) pool[pool_n++] = static_cast<int8_t>(c);
        for (int i = 0; i < needed; ++i) {
            const int j = i + static_cast<int>(rng.below(static_cast<uint32_t>(pool_n - i)));
            const int8_t t = pool[i]; pool[i] = pool[j]; pool[j] = t;
            board[s.bet.board_n + i] = pool[i];
        }
        next.bet = betting_.advance_street(s.bet, board, s.bet.board_n + needed);
        return next;
    }

    double utility(const State& s, int player) const {
        const int opponent = 1 - player;
        const size_t fold_at = s.bet.history.find(char('0' + FOLD));
        if (fold_at != std::string::npos) {
            const int folded = who_folded(s.bet, fold_at);
            return folded == player
                 ? -static_cast<double>(s.bet.contributions[static_cast<size_t>(player)])
                 :  static_cast<double>(s.bet.contributions[static_cast<size_t>(opponent)]);
        }

        int8_t mine_r[7], mine_s[7], theirs_r[7], theirs_s[7];
        fill_cards(s, player, mine_r, mine_s);
        fill_cards(s, opponent, theirs_r, theirs_s);
        const int n = 2 + s.bet.board_n;
        const int32_t mine = score_hand_7(mine_r, mine_s, n);
        const int32_t theirs = score_hand_7(theirs_r, theirs_s, n);

        // Only the matched portion is at risk; anything beyond what the
        // opponent could cover is returned, so it nets to nothing.
        const double at_risk = static_cast<double>(
            std::min(s.bet.contributions[0], s.bet.contributions[1]));
        if (mine > theirs) return at_risk;
        if (mine < theirs) return -at_risk;
        return 0.0;
    }

    std::string information_set(const State& s, int player) const {
        return std::to_string(bucket_for(s, player)) + "|" + s.bet.history;
    }

    size_t cache_size() const { return bucket_cache_.size(); }

private:
    static int who_folded(const pokerbot::State& s, size_t position) {
        const std::string prefix = s.history.substr(0, position);
        int street = 0;
        size_t last_slash = std::string::npos;
        for (size_t i = 0; i < prefix.size(); ++i)
            if (prefix[i] == '/') { ++street; last_slash = i; }
        const size_t before = last_slash == std::string::npos
                            ? prefix.size() : prefix.size() - last_slash - 1;
        const int first = street == 0 ? 0 : 1;
        return (first + static_cast<int>(before)) % 2;
    }

    static void fill_cards(const State& s, int player, int8_t* ranks, int8_t* suits) {
        for (int i = 0; i < 2; ++i) {
            const int card = s.hole[static_cast<size_t>(player)][static_cast<size_t>(i)];
            ranks[i] = static_cast<int8_t>(deck_rank(card));
            suits[i] = static_cast<int8_t>(deck_suit(card));
        }
        for (int i = 0; i < s.bet.board_n; ++i) {
            const int card = s.bet.board[static_cast<size_t>(i)];
            ranks[2 + i] = static_cast<int8_t>(deck_rank(card));
            suits[2 + i] = static_cast<int8_t>(deck_suit(card));
        }
    }

    int bucket_for(const State& s, int player) const {
        const auto& hole = s.hole[static_cast<size_t>(player)];
        if (s.bet.board_n == 0) {
            const int a = hole[0], b = hole[1];
            return abstraction_.preflop[static_cast<size_t>(a) * 52 + static_cast<size_t>(b)];
        }

        // Memoised on the cards, exactly as the Python game does: without it
        // every decision on a street would recompute the same rollout.
        uint64_t key = 0;
        const int lo = std::min(hole[0], hole[1]), hi = std::max(hole[0], hole[1]);
        key = (key << 6) | static_cast<uint64_t>(lo);
        key = (key << 6) | static_cast<uint64_t>(hi);
        for (int i = 0; i < s.bet.board_n; ++i)
            key = (key << 6) | static_cast<uint64_t>(s.bet.board[static_cast<size_t>(i)]);

        auto found = bucket_cache_.find(key);
        if (found != bucket_cache_.end()) return found->second;

        int cards[2] = {hole[0], hole[1]};
        int board[5];
        for (int i = 0; i < s.bet.board_n; ++i) board[i] = s.bet.board[static_cast<size_t>(i)];
        // Seeded from the cards so a situation always buckets the same way
        // within a run. Not the Python's seed: that comes from Python's own
        // tuple hash, which is not reproducible here and need not be.
        const double value = equity_vs_random(cards, 2, board, s.bet.board_n,
                                              abstraction_.equity_samples, key * 0x9E3779B97F4A7C15ULL);
        const int street_index = s.bet.board_n - 3;
        const int bucket = Abstraction::nearest(
            abstraction_.centroids[static_cast<size_t>(street_index)], value);
        bucket_cache_.emplace(key, bucket);
        return bucket;
    }

    Abstraction abstraction_;
    NoLimitHoldem betting_;
    mutable std::unordered_map<uint64_t, int> bucket_cache_;
};

}  // namespace pokerbot
