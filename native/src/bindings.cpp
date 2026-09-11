#include <nanobind/nanobind.h>
#include <nanobind/stl/vector.h>
#include <vector>
#include "hand_eval.hpp"
#include "equity.hpp"

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
}
