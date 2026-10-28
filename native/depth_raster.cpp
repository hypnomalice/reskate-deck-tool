#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

// Exact counterpart of depth_views._reference_view, for the tool only.
// No game/runtime integration or global state. Row buffers are owned per call.
static int round_even(double value) noexcept {
    const double base = std::floor(value);
    const double frac = value - base;
    const int lower = static_cast<int>(base);
    return lower + (frac > .5 || (frac == .5 && lower % 2 != 0) ? 1 : 0);
}
extern "C" __declspec(dllexport) int depth_raster_version() noexcept { return 1; }
extern "C" __declspec(dllexport) int depth_raster(
    const std::uint8_t* rgb, const std::uint8_t* depth, std::uint8_t* output,
    int width, int height, double angle, double strength, double convergence) noexcept {
    if (!rgb || !depth || !output || width < 1 || height < 1 || width > 32768 || height > 32768 ||
        !std::isfinite(angle) || !std::isfinite(strength) || !std::isfinite(convergence) ||
        angle < -1 || angle > 1 || strength < 0 || strength > 1 || convergence < 0 || convergence > 1) return 0;
    try {
        const std::size_t count = static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
        if (strength == 0 || angle == 0) { std::memcpy(output, rgb, count * 3); return 1; }
        std::memset(output, 0, count * 3);
        double shifts[256];
        for (int d = 0; d < 256; ++d) shifts[d] = angle * strength * width * (d / 255.0 - convergence);
        std::vector<double> zbuf(width);
        std::vector<int> indices(width);
        std::vector<std::uint8_t> colours(static_cast<std::size_t>(width) * 3), has_colour(width);
        std::vector<int> valid; valid.reserve(width);
        for (int y = 0; y < height; ++y) {
            const auto row = static_cast<std::size_t>(y) * static_cast<std::size_t>(width);
            std::fill(zbuf.begin(), zbuf.end(), -1);
            std::fill(indices.begin(), indices.end(), -1);
            std::fill(has_colour.begin(), has_colour.end(), std::uint8_t{0});
            for (int x = 0; x < width; ++x) {
                const int d = depth[row + x];
                if (x > 0 && x < width - 1 && std::abs(d - depth[row + x - 1]) <= 8 && std::abs(d - depth[row + x + 1]) <= 8) continue;
                const int target = round_even(x + shifts[d]);
                if (target >= 0 && target < width && d >= zbuf[target]) { zbuf[target] = d; indices[target] = x; }
            }
            for (int x = 0; x < width - 1; ++x) {
                const int da = depth[row + x], db = depth[row + x + 1];
                if (std::abs(da - db) > 8) continue;
                const double left = x + shifts[da], right = x + 1 + shifts[db];
                if (right <= left) continue;
                const int first = std::max(0, static_cast<int>(std::ceil(left)));
                const int last = std::min(width - 1, static_cast<int>(std::floor(right)));
                for (int target = first; target <= last; ++target) {
                    const double t = (target - left) / (right - left), z = da + (db - da) * t;
                    if (z + .001 < zbuf[target]) continue;
                    zbuf[target] = z; indices[target] = x; has_colour[target] = 1;
                    for (int c = 0; c < 3; ++c) {
                        const auto a = (row + x) * 3 + c;
                        const double colour = rgb[a] * (1 - t) + rgb[a + 3] * t;
                        colours[static_cast<std::size_t>(target) * 3 + c] = static_cast<std::uint8_t>(round_even(colour));
                    }
                }
            }
            valid.clear();
            for (int x = 0; x < width; ++x) if (indices[x] >= 0) valid.push_back(x);
            if (valid.empty()) continue;
            int previous = valid.front();
            for (int x = 0; x < previous; ++x) indices[x] = indices[previous];
            for (std::size_t i = 1; i < valid.size(); ++i) {
                const int next = valid[i];
                const int source = zbuf[previous] <= zbuf[next] ? indices[previous] : indices[next];
                for (int x = previous + 1; x < next; ++x) indices[x] = source;
                previous = next;
            }
            for (int x = previous + 1; x < width; ++x) indices[x] = indices[previous];
            for (int x = 0; x < width; ++x) {
                const auto destination = (row + x) * 3;
                const auto source = has_colour[x] ? static_cast<std::size_t>(x) * 3 : (row + indices[x]) * 3;
                const auto* bytes = has_colour[x] ? colours.data() : rgb;
                for (int c = 0; c < 3; ++c) output[destination + c] = bytes[source + c];
            }
        }
        return 1;
    } catch (...) { return 0; }
}

