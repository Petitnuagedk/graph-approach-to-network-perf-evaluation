#include <algorithm>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 5) return 2;
    const uint32_t n = static_cast<uint32_t>(std::stoul(argv[1]));
    const uint32_t probe_s = static_cast<uint32_t>(std::stoul(argv[2]));
    const uint32_t probe_d = static_cast<uint32_t>(std::stoul(argv[3]));
    const uint64_t seed = std::stoull(argv[4]);
    const double fraction = 0.05;
    std::vector<std::pair<uint32_t, uint32_t>> pairs{{probe_s, probe_d}};
    const uint64_t all_pairs = static_cast<uint64_t>(n) * (n - 1) / 2;
    const uint64_t requested = static_cast<uint64_t>(std::llround(fraction * all_pairs));
    std::vector<std::pair<uint32_t, uint32_t>> candidates;
    for (uint32_t s = 0; s < n; ++s) for (uint32_t d = s + 1; d < n; ++d) {
        if (s == std::min(probe_s, probe_d) && d == std::max(probe_s, probe_d)) continue;
        candidates.emplace_back(s, d);
    }
    std::mt19937_64 rng(seed);
    std::shuffle(candidates.begin(), candidates.end(), rng);
    for (uint64_t i = 0; i < requested; ++i) {
        auto [s, d] = candidates[i];
        if (rng() & 1ULL) std::swap(s, d);
        pairs.emplace_back(s, d);
    }
    for (size_t i = 0; i < pairs.size(); ++i)
        std::cout << i << "," << pairs[i].first << "," << pairs[i].second << "," << (i == 0 ? 1 : 0) << "\n";
}
