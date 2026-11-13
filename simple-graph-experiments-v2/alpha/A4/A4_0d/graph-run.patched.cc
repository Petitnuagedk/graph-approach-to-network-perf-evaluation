/*
    graph-run.cc

    Pure trace-matrix replay: loads a dense per-frame adjacency-matrix CSV
    (see LoadFramesCsv for the exact layout) from a given path and drives
    the network layer (routing + UDP traffic) with
    TraceMatrixPropagationLossModel fed from those frames. A 1 in the
    matrix becomes --linkUpLossDb, a 0 becomes --linkDownLossDb; frame i
    occurs at time i / --fps, since this format carries no timestamps.

    This is the "trace-only" half of L1-perf-compare.cc, pulled out into its
    own script: no mobility, no physical propagation model, no buildings, no
    frame capture. It only ever plays back a matrix you already have.

    Output: <outDir>/trace_replay_results.csv (one row per protocol run)
*/

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/ipv4-static-routing-helper.h"
#include "ns3/ipv4-static-routing.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/olsr-helper.h"
#include "ns3/applications-module.h"
#include "ns3/propagation-module.h"
#include "ns3/aodv-module.h"
#include "ns3/dsdv-module.h"
#include "ns3/olsr-header.h"
#include "ns3/aodv-packet.h"
#include "ns3/trace-matrix-propagation-model.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <random>
#include <queue>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("L1TraceReplay");

// ============================================================
//  Shared constant
// ============================================================
static const uint16_t APP_PORT = 9000;

// ============================================================
//  Performance / network metrics collected for one protocol run
// ============================================================
struct PerfMetrics {
    double   wall_time_s       = 0.0;
    double   cpu_time_s        = 0.0;
    uint64_t ip_tx_cb_calls    = 0;
    uint64_t ip_rx_cb_calls    = 0;
    uint64_t frame_apply_calls = 0;
    uint64_t routing_tx        = 0;
    uint64_t routing_rx        = 0;
    double   pdr               = 0.0;  // packet delivery ratio
    double   goodput_mbps      = 0.0;  // effective throughput (Mbps)
    double   eed_mean_s        = 0.0;  // mean end-to-end delay (s)
    uint64_t app_tx_pkts       = 0;
    uint64_t app_rx_pkts       = 0;
    uint64_t ip_drop_no_route  = 0;
    uint64_t ip_drop_route_err = 0;
    uint64_t phy_tx_drop       = 0;
    uint64_t phy_rx_drop       = 0;
    uint64_t control_packets  = 0;
    uint64_t control_bytes    = 0;
    double routing_efficiency = std::numeric_limits<double>::quiet_NaN();
    std::vector<double> reestablishment_times;
    std::vector<double> recovered_outage_durations;
    std::map<std::string, uint64_t> control_message_counts;
    std::map<std::string, uint64_t> control_message_bytes;
};

// ============================================================
//  Per-frame representation: a timestamp plus a list of (i, j, lossDb)
//  triplets for i < j only, derived from a dense 0/1 adjacency matrix
//  (see LoadFramesCsv). Every pair is always present -- a 1 becomes
//  g_linkUpLossDb, a 0 becomes g_linkDownLossDb -- there is no "absent
//  pair" case in this format.
// ============================================================
struct SparseFrame {
    double time = 0.0;
    std::vector<std::tuple<uint32_t, uint32_t, double>> entries; // (i, j, lossDb), i < j
};

static double g_lossThresholdDb  = 150.0; // dB; still passed to SetSparseThreshold
static bool   g_traceInterpolate = true;  // linear-in-dB interpolation between frames
static double g_linkUpLossDb     = 10.0;  // loss (dB) written for a 1 in the adjacency matrix
static double g_linkDownLossDb   = 125.0; // below sparse threshold, but above PHY path-loss cutoff
static double g_defaultLossDb    = 1e6;
static double g_txPowerDbm       = 20.0;
static double g_rxSensitivityDbm = -101.0;
static double g_framesPerSecond  = 1.0;   // frame i occurs at time i / g_framesPerSecond
static double g_warmupSec        = 0.0;   // requested warm-up (s); 0 = legacy behaviour
static double g_warmupEffective  = 0.0;   // warm-up actually inserted (whole frames)
static bool   g_dumpRoutes       = false; // write routing-table dumps and rx/tx times
static std::string g_warmupMode  = "first"; // union: all links ever up; first: topology of trace frame 0
static std::string g_staticOracleMode = "frame"; // legacy frame routes or interpolated usable routes
static uint32_t g_traceStartFrame = 0;
static uint32_t g_oracleSource = 0;
static uint32_t g_oracleDestination = 1;
static Ipv4Address g_oracleDestinationAddress;
static std::vector<Ptr<Ipv4StaticRouting>> g_staticRoutes;
static NodeContainer g_replayNodes;
static Ipv4InterfaceContainer g_replayInterfaces;
static std::map<std::string, uint64_t> g_controlPackets;
static std::map<std::string, uint64_t> g_controlBytes;
static std::string g_activeRouting;
static std::string g_outDir;

// ============================================================
//  Loaded-frame storage (read from CSV, consumed by the replay)
// ============================================================
static std::vector<SparseFrame>  g_frames;
static uint32_t                  g_frameDimension = 0;
static std::vector<std::string>  g_nodes;

// Fixed RNG stream bases (NOT ns-3's automatic per-object stream counter),
// so WifiMac / routing draw from the same absolute substreams on every
// protocol run in this process, independent of construction order.
static constexpr int64_t kWifiStreamBase    = 1000;
static constexpr int64_t kRoutingStreamBase = 5000;

// ============================================================
//  Replay globals
// ============================================================
static Ptr<TraceMatrixPropagationLossModel> g_traceLossModel;
static std::vector<Ptr<MobilityModel>>      g_traceMobModels;

static uint64_t g_traceTxCb      = 0;
static uint64_t g_traceRxCb      = 0;
static uint64_t g_traceApplyCb   = 0;
static uint64_t g_traceRoutingTx = 0;
static uint64_t g_traceRoutingRx = 0;

// ============================================================
//  Per-run flow tracker (reset at the start of each protocol run)
// ============================================================
struct RunTracker {
    uint64_t appTxPkts      = 0;
    uint64_t appRxPkts      = 0;
    uint64_t appRxBytes     = 0;
    double   firstTxTime    = -1.0;
    double   lastTxTime     = -1.0;
    double   firstRxTime    = -1.0;
    double   lastRxTime     = -1.0;
    double   sumDelay       = 0.0;
    uint64_t appTxBytes     = 0;
    std::vector<double> txTimes;
    std::vector<double> rxTimes;
    uint64_t ipDropNoRoute  = 0;
    uint64_t ipDropRouteErr = 0;
    uint64_t phyTxDrop      = 0;
    uint64_t phyRxDrop      = 0;
    uint64_t appIpDropNoRoute = 0;
    uint64_t appIpDropRouteErr = 0;
    uint64_t macTxDrop = 0;
    uint64_t macQueueDrop = 0;
    uint64_t duplicateRxPkts = 0;
    std::set<uint32_t> rxSequences;

    struct PacketEvent {
        std::string kind;
        int64_t sequence = -1;
        double appTxTime = std::numeric_limits<double>::quiet_NaN();
        double eventTime = 0.0;
        double delay = std::numeric_limits<double>::quiet_NaN();
        bool frameConnected = false;
        bool usableConnected = false;
    };
    std::vector<PacketEvent> packetEvents;

    void reset() { *this = RunTracker(); }
};

static RunTracker g_traceTracker;

static double
FrameLoss(const SparseFrame& frame, uint32_t a, uint32_t b)
{
    if (a > b) std::swap(a, b);
    for (const auto& [i, j, loss] : frame.entries)
        if (i == a && j == b) return loss;
    return g_defaultLossDb;
}

static bool
GraphConnectedAt(double time, bool useInterpolatedUsability)
{
    if (g_frames.empty() || g_oracleSource >= g_frameDimension ||
        g_oracleDestination >= g_frameDimension || time < g_frames.front().time)
        return false;

    auto after = std::upper_bound(g_frames.begin(), g_frames.end(), time,
        [](double t, const SparseFrame& frame) { return t < frame.time; });
    size_t current = after == g_frames.begin() ? 0
        : static_cast<size_t>(std::distance(g_frames.begin(), after) - 1);
    size_t next = current + 1;
    double alpha = 0.0;
    const bool interpolate = useInterpolatedUsability && g_traceInterpolate &&
        next < g_frames.size() && g_frames[next].time > g_frames[current].time;
    if (interpolate)
        alpha = std::clamp((time - g_frames[current].time) /
                           (g_frames[next].time - g_frames[current].time), 0.0, 1.0);

    std::vector<std::vector<uint32_t>> adjacency(g_frameDimension);
    for (const auto& [a, b, currentLoss] : g_frames[current].entries) {
        double loss = currentLoss < g_lossThresholdDb ? currentLoss : g_defaultLossDb;
        if (interpolate) {
            const double rawNextLoss = FrameLoss(g_frames[next], a, b);
            const double nextLoss = rawNextLoss < g_lossThresholdDb
                ? rawNextLoss : g_defaultLossDb;
            loss += alpha * (nextLoss - loss);
        }
        if (useInterpolatedUsability) {
            if (loss >= g_lossThresholdDb) loss = g_defaultLossDb;
            if (g_txPowerDbm - loss < g_rxSensitivityDbm) continue;
        } else if (currentLoss != g_linkUpLossDb) {
            continue;
        }
        adjacency[a].push_back(b);
        adjacency[b].push_back(a);
    }

    std::vector<bool> visited(g_frameDimension, false);
    std::queue<uint32_t> pending;
    visited[g_oracleSource] = true;
    pending.push(g_oracleSource);
    while (!pending.empty()) {
        const uint32_t node = pending.front();
        pending.pop();
        if (node == g_oracleDestination) return true;
        for (uint32_t neighbor : adjacency[node]) {
            if (!visited[neighbor]) {
                visited[neighbor] = true;
                pending.push(neighbor);
            }
        }
    }
    return false;
}

struct TrafficWindowOracleMetrics {
    double startTime = 0.0;
    double stopTime = 0.0;
    double frameUptime = std::numeric_limits<double>::quiet_NaN();
    double usableUptime = std::numeric_limits<double>::quiet_NaN();
};

static TrafficWindowOracleMetrics
ComputeTrafficWindowOracleMetrics()
{
    TrafficWindowOracleMetrics result;
    result.startTime = g_warmupEffective + 0.1;
    result.stopTime = g_frames.empty() ? result.startTime : g_frames.back().time;
    if (result.stopTime <= result.startTime) return result;

    std::set<double> breakpoints{result.startTime, result.stopTime};
    for (size_t i = 1; i + 1 < g_frames.size(); ++i) {
        if (g_frames[i].time > result.startTime && g_frames[i].time < result.stopTime)
            breakpoints.insert(g_frames[i].time);
    }

    const double usableLossLimitDb = g_txPowerDbm - g_rxSensitivityDbm;
    if (g_traceInterpolate) {
        for (size_t i = 0; i + 1 < g_frames.size(); ++i) {
            for (const auto& [a, b, rawCurrentLoss] : g_frames[i].entries) {
                const double rawNextLoss = FrameLoss(g_frames[i + 1], a, b);
                const double currentLoss = rawCurrentLoss < g_lossThresholdDb
                    ? rawCurrentLoss : g_defaultLossDb;
                const double nextLoss = rawNextLoss < g_lossThresholdDb
                    ? rawNextLoss : g_defaultLossDb;
                if (currentLoss == nextLoss) continue;
                const double alpha = (usableLossLimitDb - currentLoss) /
                                     (nextLoss - currentLoss);
                if (alpha <= 0.0 || alpha >= 1.0) continue;
                const double crossing = g_frames[i].time +
                    alpha * (g_frames[i + 1].time - g_frames[i].time);
                if (crossing > result.startTime && crossing < result.stopTime)
                    breakpoints.insert(crossing);
            }
        }
    }

    double frameConnectedSeconds = 0.0;
    double usableConnectedSeconds = 0.0;
    for (auto it = breakpoints.begin(); std::next(it) != breakpoints.end(); ++it) {
        const double start = *it;
        const double stop = *std::next(it);
        const double midpoint = (start + stop) / 2.0;
        const double duration = stop - start;
        if (GraphConnectedAt(midpoint, false)) frameConnectedSeconds += duration;
        if (GraphConnectedAt(midpoint, true)) usableConnectedSeconds += duration;
    }
    const double trafficDuration = result.stopTime - result.startTime;
    result.frameUptime = frameConnectedSeconds / trafficDuration;
    result.usableUptime = usableConnectedSeconds / trafficDuration;
    return result;
}

static void
RecordPacketEvent(const std::string& kind, int64_t sequence, double appTxTime)
{
    RunTracker::PacketEvent event;
    event.kind = kind;
    event.sequence = sequence;
    event.appTxTime = appTxTime;
    event.eventTime = Simulator::Now().GetSeconds();
    if (std::isfinite(appTxTime)) event.delay = event.eventTime - appTxTime;
    event.frameConnected = GraphConnectedAt(event.eventTime, false);
    event.usableConnected = GraphConnectedAt(event.eventTime, true);
    g_traceTracker.packetEvents.push_back(event);
}

struct OracleMetrics {
    double uptimeRatio = 0.0;
    double meanUpRunSeconds = std::numeric_limits<double>::quiet_NaN();
    double medianUpRunSeconds = std::numeric_limits<double>::quiet_NaN();
    double p90UpRunSeconds = std::numeric_limits<double>::quiet_NaN();
    uint32_t transitions = 0;
    double pathRetention = std::numeric_limits<double>::quiet_NaN();
    bool hasAlternativePaths = false;
    std::vector<double> upRuns;
    std::vector<double> outages;
    std::vector<bool> connected;
    std::vector<std::vector<uint32_t>> routes;
};

static OracleMetrics g_oracle;

// ============================================================
//  Traffic flow pairs (sender -> receiver), as positions in g_nodes.
//  Either given explicitly via --flows (labels resolved in main()), or
//  drawn deterministically from `seed` against the node count implied
//  by the loaded CSV when --flows is absent.
// ============================================================
struct FlowPair {
    uint32_t senderIdx;
    uint32_t receiverIdx;
    bool probe = false;
};

struct FlowStatistics {
    uint64_t offered = 0;
    uint64_t delivered = 0;
    double configuredStartTime = 0.0;
    std::set<uint32_t> receivedSequences;
    std::vector<double> txTimes;
    std::vector<double> rxTimes;
    std::vector<double> delays;
};

static bool g_a3Instrumentation = false;
static bool g_a3bForwardLogEnabled = false;
static bool g_emitControlUnparsedColumns = false;
static std::ofstream g_a3bForwardLog;
static std::ofstream g_a3bControlLog;
static double g_flowFraction = 0.0;
static uint64_t g_flowSeed = 9001;
static std::vector<FlowPair> g_activeFlows;
static std::vector<FlowStatistics> g_flowStatistics;
static std::map<std::pair<uint32_t, uint32_t>, uint32_t> g_flowIndexByAddress;
static std::vector<std::vector<int>> g_staticHopDistances;
static std::map<uint32_t, std::map<std::string, uint64_t>> g_nodeControlPackets;
static std::map<uint32_t, std::map<std::string, uint64_t>> g_nodeControlBytes;
static std::map<uint32_t, uint64_t> g_nodeForwardedData;
static std::map<uint32_t, uint64_t> g_nodeMacDataFailed;
static std::map<uint32_t, uint64_t> g_nodeMacFinalDataFailed;
static std::map<uint32_t, uint64_t> g_nodeMacTxDrop;
static std::map<uint32_t, uint64_t> g_nodeMacQueueDrop;
static std::map<uint32_t, std::map<std::string, uint64_t>> g_nodePhyRxReasons;
static std::map<uint32_t, std::map<std::string, uint64_t>> g_nodePhyRxClasses;
static std::map<Mac48Address, uint32_t> g_nodeByMacAddress;

static std::vector<FlowPair>
GenerateFractionFlowPairs(uint32_t numNodes,
                          double fraction,
                          FlowPair probe,
                          uint64_t seed,
                          std::string& error)
{
    if (numNodes < 2 || probe.senderIdx >= numNodes || probe.receiverIdx >= numNodes ||
        probe.senderIdx == probe.receiverIdx) {
        error = "invalid node count or probe endpoints";
        return {};
    }
    std::vector<FlowPair> pairs{probe};
    const uint64_t allPairs = static_cast<uint64_t>(numNodes) * (numNodes - 1) / 2;
    const uint64_t requested = static_cast<uint64_t>(std::llround(fraction * allPairs));
    std::vector<std::pair<uint32_t, uint32_t>> candidates;
    for (uint32_t source = 0; source < numNodes; ++source) {
        for (uint32_t destination = source + 1; destination < numNodes; ++destination) {
            if (source == std::min(probe.senderIdx, probe.receiverIdx) &&
                destination == std::max(probe.senderIdx, probe.receiverIdx))
                continue;
            candidates.emplace_back(source, destination);
        }
    }
    if (requested > candidates.size()) {
        error = "rounded flowFraction requests more background pairs than are available after excluding the probe";
        return {};
    }
    std::mt19937_64 rng(seed);
    std::shuffle(candidates.begin(), candidates.end(), rng);
    pairs.reserve(requested + 1);
    for (uint64_t i = 0; i < requested; ++i) {
        auto [source, destination] = candidates[i];
        if (rng() & 1ULL) std::swap(source, destination);
        pairs.push_back({source, destination, false});
    }
    return pairs;
}

static std::vector<FlowPair>
GenerateFlowPairs(uint32_t numNodes, uint32_t numFlows, uint32_t seed)
{
    std::vector<FlowPair> pairs;
    if (numNodes < 2 || numFlows == 0) return pairs;

    std::mt19937 rng(seed + 0x9E3779B9u);
    std::uniform_int_distribution<uint32_t> dist(0, numNodes - 1);

    const uint64_t maxOrderedPairs = (uint64_t)numNodes * (numNodes - 1);
    const uint32_t target = (uint32_t)std::min<uint64_t>(numFlows, maxOrderedPairs);

    std::set<std::pair<uint32_t, uint32_t>> seen;
    uint32_t attempts = 0;
    const uint32_t maxAttempts = target * 50 + 100;
    while (pairs.size() < target && attempts < maxAttempts) {
        ++attempts;
        uint32_t s = dist(rng);
        uint32_t r = dist(rng);
        if (s == r) continue;
        if (!seen.insert({s, r}).second) continue;
        pairs.push_back({s, r});
    }
    return pairs;
}

static bool
FileExists(const std::string& filename)
{
    std::ifstream f(filename);
    return f.good();
}

static std::vector<uint32_t>
ShortestPath(const SparseFrame& frame, uint32_t source, uint32_t destination,
             bool* hasAlternative = nullptr)
{
    std::vector<std::vector<uint32_t>> adjacency(g_frameDimension);
    for (const auto& [i, j, loss] : frame.entries) {
        if (loss == g_linkUpLossDb) {
            adjacency[i].push_back(j);
            adjacency[j].push_back(i);
        }
    }
    std::vector<int> distance(g_frameDimension, -1);
    std::vector<uint32_t> ways(g_frameDimension, 0);
    std::vector<int> parent(g_frameDimension, -1);
    std::queue<uint32_t> pending;
    distance[source] = 0;
    ways[source] = 1;
    pending.push(source);
    while (!pending.empty()) {
        const uint32_t here = pending.front();
        pending.pop();
        for (uint32_t next : adjacency[here]) {
            if (distance[next] < 0) {
                distance[next] = distance[here] + 1;
                parent[next] = static_cast<int>(here);
                ways[next] = ways[here];
                pending.push(next);
            } else if (distance[next] == distance[here] + 1) {
                ways[next] = std::min<uint32_t>(2, ways[next] + ways[here]);
            }
        }
    }
    if (distance[destination] < 0) return {};
    std::vector<uint32_t> path;
    for (int at = static_cast<int>(destination); at >= 0; at = parent[at]) {
        path.push_back(static_cast<uint32_t>(at));
        if (static_cast<uint32_t>(at) == source) break;
    }
    std::reverse(path.begin(), path.end());
    bool alternateExists = false;
    for (size_t edge = 1; edge < path.size() && !alternateExists; ++edge) {
        std::vector<bool> visited(g_frameDimension, false);
        std::queue<uint32_t> search;
        visited[source] = true;
        search.push(source);
        while (!search.empty() && !visited[destination]) {
            const uint32_t here = search.front();
            search.pop();
            for (uint32_t next : adjacency[here]) {
                const bool removedEdge =
                    (here == path[edge - 1] && next == path[edge]) ||
                    (here == path[edge] && next == path[edge - 1]);
                if (!removedEdge && !visited[next]) {
                    visited[next] = true;
                    search.push(next);
                }
            }
        }
        alternateExists = visited[destination];
    }
    if (hasAlternative) *hasAlternative = alternateExists;
    return path;
}

static double
Quantile(std::vector<double> values, double probability)
{
    if (values.empty()) return std::numeric_limits<double>::quiet_NaN();
    std::sort(values.begin(), values.end());
    const double position = probability * (values.size() - 1);
    const size_t lower = static_cast<size_t>(position);
    const size_t upper = std::min(lower + 1, values.size() - 1);
    const double fraction = position - lower;
    return values[lower] * (1.0 - fraction) + values[upper] * fraction;
}

static OracleMetrics
ComputeOracleMetrics()
{
    OracleMetrics result;
    const size_t n = g_frames.size() - g_traceStartFrame;
    if (!n) return result;
    const double frameDuration = 1.0 / g_framesPerSecond;
    uint32_t upFrames = 0;
    uint32_t upRun = 0;
    uint32_t downRun = 0;
    bool previous = false;
    bool havePrevious = false;
    uint32_t routeComparisons = 0;
    uint32_t routeRepeats = 0;
    for (size_t k = 0; k < n; ++k) {
        bool alternative = false;
        auto route = ShortestPath(g_frames[g_traceStartFrame + k], g_oracleSource,
                                 g_oracleDestination, &alternative);
        const bool up = !route.empty();
        result.connected.push_back(up);
        result.routes.push_back(route);
        result.hasAlternativePaths = result.hasAlternativePaths || alternative;
        if (up) {
            ++upFrames;
            ++upRun;
            if (downRun) {
                result.outages.push_back(downRun * frameDuration);
                downRun = 0;
            }
        } else {
            ++downRun;
            if (upRun) {
                result.upRuns.push_back(upRun * frameDuration);
                upRun = 0;
            }
        }
        if (havePrevious && up != previous) ++result.transitions;
        if (k > 0 && up && result.connected[k - 1]) {
            ++routeComparisons;
            if (route == result.routes[k - 1]) ++routeRepeats;
        }
        previous = up;
        havePrevious = true;
    }
    if (upRun) result.upRuns.push_back(upRun * frameDuration);
    if (downRun) result.outages.push_back(downRun * frameDuration);
    result.uptimeRatio = static_cast<double>(upFrames) / n;
    if (!result.upRuns.empty()) {
        double total = 0.0;
        for (double value : result.upRuns) total += value;
        result.meanUpRunSeconds = total / result.upRuns.size();
        result.medianUpRunSeconds = Quantile(result.upRuns, 0.5);
        result.p90UpRunSeconds = Quantile(result.upRuns, 0.9);
    }
    if (result.hasAlternativePaths && routeComparisons)
        result.pathRetention = static_cast<double>(routeRepeats) / routeComparisons;
    return result;
}

static std::string
FormatList(const std::vector<double>& values)
{
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) out << ';';
        out << values[i];
    }
    return out.str();
}

static std::string
JsonEscape(const std::string& value)
{
    std::ostringstream escaped;
    for (unsigned char ch : value) {
        if (ch == '"' || ch == '\\') escaped << '\\' << ch;
        else if (ch == '\n') escaped << "\\n";
        else if (ch == '\r') escaped << "\\r";
        else if (ch == '\t') escaped << "\\t";
        else escaped << ch;
    }
    return escaped.str();
}

// ============================================================
//  Helper: is this packet destined for / originating from APP_PORT?
//  Returns false for routing/control packets.
// ============================================================
static bool
IsAppPacket(Ptr<const Packet> packet)
{
    Ptr<Packet> pcopy = packet->Copy();
    Ipv4Header  ip4h;
    if (!pcopy->PeekHeader(ip4h)) return false;
    pcopy->RemoveHeader(ip4h);
    UdpHeader udph;
    if (pcopy->GetSize() < udph.GetSerializedSize()) return false;
    if (!pcopy->PeekHeader(udph))                    return false;
    return udph.GetDestinationPort() == APP_PORT ||
           udph.GetSourcePort()      == APP_PORT;
}

static void
TraceUdpClientTx(Ptr<const Packet> packet)
{
    ++g_traceTracker.appTxPkts;
    g_traceTracker.appTxBytes += packet->GetSize();
    const double now = Simulator::Now().GetSeconds();
    g_traceTracker.txTimes.push_back(now);
    if (g_traceTracker.firstTxTime < 0) g_traceTracker.firstTxTime = now;
    g_traceTracker.lastTxTime = now;
    if (g_dumpRoutes)
        RecordPacketEvent("tx", static_cast<int64_t>(g_traceTracker.appTxPkts - 1), now);
}

static void
TraceUdpClientTxForFlow(uint32_t flowIndex, Ptr<const Packet> packet)
{
    TraceUdpClientTx(packet);
    if (g_a3Instrumentation && flowIndex < g_flowStatistics.size()) {
        auto& stats = g_flowStatistics[flowIndex];
        ++stats.offered;
        stats.txTimes.push_back(Simulator::Now().GetSeconds());
    }
}

static std::string
ControlMessageKind(Ptr<const Packet> packet)
{
    Ptr<Packet> payload = packet->Copy();
    Ipv4Header ip;
    if (payload->GetSize() < ip.GetSerializedSize() || !payload->PeekHeader(ip))
        return g_activeRouting == "olsr" ? "olsr_unparsed" : g_activeRouting + "_other";
    payload->RemoveHeader(ip);
    if (ip.GetProtocol() != 17) return g_activeRouting + "_other";
    UdpHeader udp;
    if (payload->GetSize() < udp.GetSerializedSize() || !payload->PeekHeader(udp))
        return g_activeRouting == "olsr" ? "olsr_unparsed" : g_activeRouting + "_other";
    if (g_activeRouting == "olsr") {
        if (udp.GetSourcePort() != 698 || udp.GetDestinationPort() != 698) return "olsr_other";
        payload->RemoveHeader(udp);
        const uint32_t size = payload->GetSize();
        if (size < 16) return "olsr_unparsed";
        std::vector<uint8_t> bytes(size);
        if (payload->CopyData(bytes.data(), size) != size) return "olsr_unparsed";
        auto readU16 = [&bytes](uint32_t offset) -> uint16_t {
            return static_cast<uint16_t>((static_cast<uint16_t>(bytes[offset]) << 8) |
                                         static_cast<uint16_t>(bytes[offset + 1]));
        };
        const uint32_t packetLength = readU16(0);
        if (packetLength != size || packetLength < 16) return "olsr_unparsed";
        uint32_t offset = 4;
        uint8_t firstType = 0;
        while (offset < packetLength) {
            if (packetLength - offset < 12) return "olsr_unparsed";
            const uint8_t messageType = bytes[offset];
            const uint32_t messageLength = readU16(offset + 2);
            if (messageType < 1 || messageType > 4 || messageLength < 12 ||
                messageLength > packetLength - offset) return "olsr_unparsed";
            if (offset == 4) firstType = messageType;
            offset += messageLength;
        }
        if (offset != packetLength) return "olsr_unparsed";
        switch (firstType) {
        case olsr::MessageHeader::HELLO_MESSAGE: return "olsr_hello";
        case olsr::MessageHeader::TC_MESSAGE: return "olsr_tc";
        case olsr::MessageHeader::MID_MESSAGE: return "olsr_mid";
        case olsr::MessageHeader::HNA_MESSAGE: return "olsr_hna";
        }
        return "olsr_unparsed";
    } else if (g_activeRouting == "aodv") {
        payload->RemoveHeader(udp);
        aodv::TypeHeader type;
        if (payload->RemoveHeader(type)) {
            switch (type.Get()) {
            case aodv::AODVTYPE_RREQ: return "aodv_rreq";
            case aodv::AODVTYPE_RREP: {
                aodv::RrepHeader reply;
                if (payload->PeekHeader(reply) && reply.GetDst() == reply.GetOrigin())
                    return "aodv_hello";
                return "aodv_rrep";
            }
            case aodv::AODVTYPE_RERR: return "aodv_rerr";
            case aodv::AODVTYPE_RREP_ACK: return "aodv_rrep_ack";
            }
        }
    } else if (g_activeRouting == "dsdv") {
        return "dsdv_update";
    }
    payload->RemoveHeader(udp);
    return g_activeRouting + "_other";
}

static void
RecordControlTx(Ptr<const Packet> packet, uint32_t nodeId)
{
    const std::string kind = ControlMessageKind(packet);
    ++g_controlPackets[kind];
    g_controlBytes[kind] += packet->GetSize();
    if (g_a3Instrumentation) {
        ++g_nodeControlPackets[nodeId][kind];
        g_nodeControlBytes[nodeId][kind] += packet->GetSize();
    }
}

static void
RecordA3bControlEvent(const char* direction, Ptr<const Packet> packet, uint32_t nodeId)
{
    if (!g_a3bForwardLogEnabled || g_activeRouting != "aodv" || !g_a3bControlLog.is_open()) return;
    const std::string kind = ControlMessageKind(packet);
    if (kind != "aodv_rreq" && kind != "aodv_rrep" && kind != "aodv_rerr") return;
    g_a3bControlLog << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds()
                    << ',' << direction << ',' << nodeId << ',' << kind << ','
                    << packet->GetUid() << '\n';
}

static void
RecordAppRx(Ptr<const Packet> packet, Ptr<Ipv4> localIpv4, uint32_t iface, RunTracker& t)
{
    Ptr<Packet> p = packet->Copy();
    Ipv4Header ip4h;
    if (p->GetSize() < ip4h.GetSerializedSize()) return;
    p->RemoveHeader(ip4h);
    if (ip4h.GetProtocol() != 17) return;
    UdpHeader udph;
    if (p->GetSize() < udph.GetSerializedSize()) return;
    p->RemoveHeader(udph);
    if (udph.GetDestinationPort() != APP_PORT) return;
    // Only count at the final destination, not intermediate forwarders
    if (iface >= localIpv4->GetNInterfaces()) return;
    if (localIpv4->GetAddress(iface, 0).GetLocal() != ip4h.GetDestination()) return;

    ++t.appRxPkts;
    t.appRxBytes += p->GetSize();
    double now = Simulator::Now().GetSeconds();
    t.rxTimes.push_back(now);
    if (t.firstRxTime < 0) t.firstRxTime = now;
    t.lastRxTime = now;

    // Keep the legacy scalar EED calculation unchanged for CSV regression.
    // Packet diagnostics below decode the actual UdpClient SeqTsHeader.
    SeqTsSizeHeader legacyDelayHeader;
    if (p->GetSize() >= legacyDelayHeader.GetSerializedSize() &&
        p->PeekHeader(legacyDelayHeader)) {
        double delay = now - legacyDelayHeader.GetTs().GetSeconds();
        if (delay >= 0.0) t.sumDelay += delay;
    }
    if (g_dumpRoutes) {
        SeqTsHeader packetHeader;
        if (p->GetSize() >= packetHeader.GetSerializedSize() && p->PeekHeader(packetHeader)) {
            const uint32_t sequence = packetHeader.GetSeq();
            if (!t.rxSequences.insert(sequence).second) ++t.duplicateRxPkts;
            RecordPacketEvent("rx", sequence, packetHeader.GetTs().GetSeconds());
        } else {
            RecordPacketEvent("rx", -1, std::numeric_limits<double>::quiet_NaN());
        }
    }
    if (g_a3Instrumentation) {
        const auto key = std::make_pair(ip4h.GetSource().Get(), ip4h.GetDestination().Get());
        const auto flow = g_flowIndexByAddress.find(key);
        if (flow != g_flowIndexByAddress.end() && flow->second < g_flowStatistics.size()) {
            SeqTsHeader packetHeader;
            auto& stats = g_flowStatistics[flow->second];
            if (p->GetSize() >= packetHeader.GetSerializedSize() && p->PeekHeader(packetHeader) &&
                stats.receivedSequences.insert(packetHeader.GetSeq()).second) {
                ++stats.delivered;
                stats.rxTimes.push_back(now);
                const double delay = now - packetHeader.GetTs().GetSeconds();
                if (delay >= 0.0) stats.delays.push_back(delay);
            }
        }
    }
}

static void
FillAppMetrics(PerfMetrics& m, const RunTracker& t, double stopTime)
{
    m.app_tx_pkts       = t.appTxPkts;
    m.app_rx_pkts       = t.appRxPkts;
    m.ip_drop_no_route  = t.ipDropNoRoute;
    m.ip_drop_route_err = t.ipDropRouteErr;
    m.phy_tx_drop       = t.phyTxDrop;
    m.phy_rx_drop       = t.phyRxDrop;
    m.pdr = (t.appTxPkts > 0) ? (double)t.appRxPkts / (double)t.appTxPkts : 0.0;
    double dur = (t.firstRxTime >= 0 && t.lastRxTime > t.firstRxTime)
                 ? (t.lastRxTime - t.firstRxTime)
                 : stopTime;
    m.goodput_mbps = (dur > 0 && t.appRxBytes > 0)
                     ? (t.appRxBytes * 8.0) / (dur * 1e6)
                     : 0.0;
    m.eed_mean_s = (t.appRxPkts > 0) ? t.sumDelay / (double)t.appRxPkts : 0.0;
}

// ============================================================
//  Apply one loaded loss frame, and stage the next one keyed to its
//  own captured timestamp so interpolation (if enabled) works against
//  the real inter-frame spacing rather than an assumed uniform one.
// ============================================================
static std::vector<TraceMatrixPropagationLossModel::SparseLossEntry>
ToSparseEntries(const SparseFrame& f)
{
    std::vector<TraceMatrixPropagationLossModel::SparseLossEntry> out;
    out.reserve(f.entries.size());
    for (const auto& [i, j, loss] : f.entries) {
        out.push_back({i, j, loss});
    }
    return out;
}

static void
UpdateOracleStaticRoutes(uint32_t frameIdx)
{
    if (g_staticRoutes.empty() || frameIdx >= g_frames.size()) return;
    const auto path = ShortestPath(g_frames[frameIdx], g_oracleSource, g_oracleDestination);
    const Ipv4Mask hostMask("255.255.255.255");
    for (uint32_t node = 0; node < g_staticRoutes.size(); ++node) {
        Ptr<Ipv4StaticRouting> table = g_staticRoutes[node];
        for (int32_t route = static_cast<int32_t>(table->GetNRoutes()) - 1; route >= 0; --route) {
            const auto entry = table->GetRoute(static_cast<uint32_t>(route));
            if (entry.GetDest() == g_oracleDestinationAddress &&
                entry.GetDestNetworkMask() == hostMask) {
                table->RemoveRoute(static_cast<uint32_t>(route));
            }
        }
    }
    if (path.empty()) return;
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        const uint32_t node = path[i];
        const uint32_t next = path[i + 1];
        g_staticRoutes[node]->AddHostRouteTo(g_oracleDestinationAddress,
                                             g_replayInterfaces.GetAddress(next), 1);
    }
}

static std::vector<uint32_t>
ShortestPathAtUsableTime(double time)
{
    if (g_frames.empty()) return {};
    auto after = std::upper_bound(g_frames.begin(), g_frames.end(), time,
        [](double t, const SparseFrame& frame) { return t < frame.time; });
    const size_t current = after == g_frames.begin() ? 0
        : static_cast<size_t>(std::distance(g_frames.begin(), after) - 1);
    const size_t next = current + 1;
    double alpha = 0.0;
    const bool interpolate = g_traceInterpolate && next < g_frames.size() &&
        g_frames[next].time > g_frames[current].time;
    if (interpolate)
        alpha = std::clamp((time - g_frames[current].time) /
                           (g_frames[next].time - g_frames[current].time), 0.0, 1.0);

    SparseFrame usableFrame;
    usableFrame.time = time;
    for (const auto& [a, b, rawCurrentLoss] : g_frames[current].entries) {
        double loss = rawCurrentLoss < g_lossThresholdDb ? rawCurrentLoss : g_defaultLossDb;
        if (interpolate) {
            const double rawNextLoss = FrameLoss(g_frames[next], a, b);
            const double nextLoss = rawNextLoss < g_lossThresholdDb
                ? rawNextLoss : g_defaultLossDb;
            loss += alpha * (nextLoss - loss);
        }
        usableFrame.entries.emplace_back(a, b,
            g_txPowerDbm - loss >= g_rxSensitivityDbm ? g_linkUpLossDb : g_linkDownLossDb);
    }
    return ShortestPath(usableFrame, g_oracleSource, g_oracleDestination);
}

static void
UpdateOracleStaticRoutesAtUsableTime(double time)
{
    if (g_staticRoutes.empty()) return;
    const auto path = ShortestPathAtUsableTime(time);
    const Ipv4Mask hostMask("255.255.255.255");
    for (uint32_t node = 0; node < g_staticRoutes.size(); ++node) {
        Ptr<Ipv4StaticRouting> table = g_staticRoutes[node];
        for (int32_t route = static_cast<int32_t>(table->GetNRoutes()) - 1; route >= 0; --route) {
            const auto entry = table->GetRoute(static_cast<uint32_t>(route));
            if (entry.GetDest() == g_oracleDestinationAddress &&
                entry.GetDestNetworkMask() == hostMask) {
                table->RemoveRoute(static_cast<uint32_t>(route));
            }
        }
    }
    if (path.empty()) return;
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        const uint32_t node = path[i];
        const uint32_t next = path[i + 1];
        g_staticRoutes[node]->AddHostRouteTo(g_oracleDestinationAddress,
                                             g_replayInterfaces.GetAddress(next), 1);
    }
}

void
TraceApplyFrame(uint32_t frameIdx)
{
    ++g_traceApplyCb;
    if (frameIdx >= g_frames.size()) return;
    if (!g_traceLossModel) return;

    g_traceLossModel->SetCurrentFrameSparse(ToSparseEntries(g_frames[frameIdx]));

    if (frameIdx + 1 < g_frames.size()) {
        const SparseFrame& next = g_frames[frameIdx + 1];
        g_traceLossModel->SetNextFrameSparse(ToSparseEntries(next), Seconds(next.time));
    }
}

// ============================================================
//  Ipv4 Tx / Rx / Drop callbacks + PHY drop callbacks
// ============================================================
void
TraceIpTxCb(Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t iface)
{
    ++g_traceTxCb;
    if (!IsAppPacket(packet)) {
        ++g_traceRoutingTx;
        const Ptr<Node> node = ipv4 ? ipv4->GetObject<Node>() : nullptr;
        const uint32_t nodeId = node ? node->GetId() : std::numeric_limits<uint32_t>::max();
        RecordControlTx(packet, nodeId);
        RecordA3bControlEvent("tx", packet, nodeId);
    }
}

static bool
IsAppIpv4Payload(const Ipv4Header& ipHeader, Ptr<const Packet> packet)
{
    if (ipHeader.GetProtocol() != 17) return false;
    Ptr<Packet> copy = packet->Copy();
    Ipv4Header nestedIp;
    if (copy->PeekHeader(nestedIp) && nestedIp.GetProtocol() == 17) copy->RemoveHeader(nestedIp);
    UdpHeader udp;
    return copy->PeekHeader(udp) &&
           (udp.GetDestinationPort() == APP_PORT || udp.GetSourcePort() == APP_PORT);
}

static bool
IsIpv4AddressAssignedToNode(uint32_t nodeId, Ipv4Address address)
{
    if (nodeId >= g_replayNodes.GetN()) return false;
    Ptr<Ipv4> ipv4 = g_replayNodes.Get(nodeId)->GetObject<Ipv4>();
    if (!ipv4) return false;
    for (uint32_t interface = 0; interface < ipv4->GetNInterfaces(); ++interface) {
        for (uint32_t addressIndex = 0; addressIndex < ipv4->GetNAddresses(interface); ++addressIndex) {
            const Ipv4Address local = ipv4->GetAddress(interface, addressIndex).GetLocal();
            if (!local.IsAny() && local == address) return true;
        }
    }
    return false;
}

static void
TraceIpForward(uint32_t nodeId, const Ipv4Header& header, Ptr<const Packet> packet, uint32_t)
{
    if (!g_a3Instrumentation || !IsAppIpv4Payload(header, packet)) return;

    const bool sourceIsLocal = IsIpv4AddressAssignedToNode(nodeId, header.GetSource());
    const bool destinationIsLocal = IsIpv4AddressAssignedToNode(nodeId, header.GetDestination());
    const bool countsAsForward = !sourceIsLocal && !destinationIsLocal;
    Ptr<Packet> payload = packet->Copy();
    UdpHeader udp;
    uint16_t sourcePort = 0;
    uint16_t destinationPort = 0;
    bool hasUdpHeader = payload->PeekHeader(udp) != 0;
    bool hasSequence = false;
    uint32_t sequence = 0;
    double appTimestamp = std::numeric_limits<double>::quiet_NaN();
    if (hasUdpHeader) {
        sourcePort = udp.GetSourcePort();
        destinationPort = udp.GetDestinationPort();
        payload->RemoveHeader(udp);
        SeqTsHeader seqTs;
        if (payload->GetSize() >= seqTs.GetSerializedSize() && payload->PeekHeader(seqTs) != 0) {
            payload->RemoveHeader(seqTs);
            hasSequence = true;
            sequence = seqTs.GetSeq();
            appTimestamp = seqTs.GetTs().GetSeconds();
        }
    }

    if (g_a3bForwardLogEnabled && g_a3bForwardLog.is_open()) {
        g_a3bForwardLog << std::fixed << std::setprecision(9) << Simulator::Now().GetSeconds()
                        << ',' << nodeId << ',' << header.GetSource() << ',' << header.GetDestination()
                        << ',' << sourcePort << ',' << destinationPort << ','
                        << (hasSequence ? std::to_string(sequence) : "") << ',';
        if (hasSequence) g_a3bForwardLog << appTimestamp;
        g_a3bForwardLog << ',' << packet->GetUid() << ',' << (sourceIsLocal ? 1 : 0)
                        << ',' << (destinationIsLocal ? 1 : 0) << ','
                        << (countsAsForward ? 1 : 0) << '\n';
    }
    if (countsAsForward) ++g_nodeForwardedData[nodeId];
}

void
TraceIpRxCb(Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t iface)
{
    ++g_traceRxCb;
    if (!IsAppPacket(packet)) {
        ++g_traceRoutingRx;
        const Ptr<Node> node = ipv4 ? ipv4->GetObject<Node>() : nullptr;
        RecordA3bControlEvent("rx", packet,
                              node ? node->GetId() : std::numeric_limits<uint32_t>::max());
    }
    RecordAppRx(packet, ipv4, iface, g_traceTracker);
}

void
TraceIpDropCb(const Ipv4Header& ipHeader, Ptr<const Packet> packet,
              Ipv4L3Protocol::DropReason reason,
              Ptr<Ipv4>, uint32_t)
{
    bool appPacket = false;
    if (ipHeader.GetProtocol() == 17) {
        Ptr<Packet> copy = packet->Copy();
        Ipv4Header packetIp;
        if (copy->PeekHeader(packetIp) && packetIp.GetProtocol() == 17)
            copy->RemoveHeader(packetIp);
        UdpHeader udp;
        appPacket = copy->PeekHeader(udp) && udp.GetDestinationPort() == APP_PORT;
    }
    if (reason == Ipv4L3Protocol::DROP_NO_ROUTE) {
        ++g_traceTracker.ipDropNoRoute;
        if (appPacket) ++g_traceTracker.appIpDropNoRoute;
    } else if (reason == Ipv4L3Protocol::DROP_ROUTE_ERROR) {
        ++g_traceTracker.ipDropRouteErr;
        if (appPacket) ++g_traceTracker.appIpDropRouteErr;
    }
}

void TracePhyTxDrop(Ptr<const Packet>) { ++g_traceTracker.phyTxDrop; }

static bool
IsInterferenceFailure(WifiPhyRxfailureReason reason)
{
    switch (reason) {
    case RXING:
    case BUSY_DECODING_PREAMBLE:
    case PREAMBLE_DETECT_FAILURE:
    case L_SIG_FAILURE:
    case HT_SIG_FAILURE:
    case SIG_A_FAILURE:
    case SIG_B_FAILURE:
    case U_SIG_FAILURE:
    case EHT_SIG_FAILURE:
    case PREAMBLE_DETECTION_PACKET_SWITCH:
    case FRAME_CAPTURE_PACKET_SWITCH:
    case OBSS_PD_CCA_RESET:
    case DMG_HEADER_FAILURE:
        return true;
    default:
        return false;
    }
}

static std::string
PhyReasonName(WifiPhyRxfailureReason reason)
{
    std::ostringstream out;
    out << reason;
    return out.str();
}

static void
TracePhyRxDrop(uint32_t nodeId, Ptr<const Packet> packet, WifiPhyRxfailureReason reason)
{
    ++g_traceTracker.phyRxDrop;
    if (!g_a3Instrumentation) return;
    const std::string reasonName = PhyReasonName(reason);
    ++g_nodePhyRxReasons[nodeId][reasonName];
    std::string category = "other_unclassified";
    Ptr<Packet> copy = packet->Copy();
    WifiMacHeader mac;
    if (copy->PeekHeader(mac) && nodeId < g_traceMobModels.size() && g_traceLossModel) {
        const auto source = g_nodeByMacAddress.find(mac.GetAddr2());
        if (source != g_nodeByMacAddress.end() && source->second < g_traceMobModels.size()) {
            const double rxPowerDbm = g_traceLossModel->CalcRxPower(
                g_txPowerDbm, g_traceMobModels[source->second], g_traceMobModels[nodeId]);
            if (reason == PREAMBLE_DETECT_FAILURE && rxPowerDbm < g_rxSensitivityDbm) {
                category = "below_sensitivity";
            } else if (rxPowerDbm >= g_rxSensitivityDbm && IsInterferenceFailure(reason)) {
                category = "collision_interference";
            }
        }
    }
    ++g_nodePhyRxClasses[nodeId][category];
}

static void
TraceMacTxDropForNode(uint32_t nodeId, Ptr<const Packet>)
{
    ++g_traceTracker.macTxDrop;
    if (g_a3Instrumentation) ++g_nodeMacTxDrop[nodeId];
}

static void
TraceMacQueueDropForNode(uint32_t nodeId, Ptr<const WifiMpdu>)
{
    ++g_traceTracker.macQueueDrop;
    if (g_a3Instrumentation) ++g_nodeMacQueueDrop[nodeId];
}

static void
TraceMacDataFailed(uint32_t nodeId, Mac48Address)
{
    if (g_a3Instrumentation) ++g_nodeMacDataFailed[nodeId];
}

static void
TraceMacFinalDataFailed(uint32_t nodeId, Mac48Address)
{
    if (g_a3Instrumentation) ++g_nodeMacFinalDataFailed[nodeId];
}

// ============================================================
//  CSV loader
//
//  Dense adjacency-matrix CSV format (one file, N+1 lines per frame):
//
//    Node_0,Node_1,...,Node_N-1   <- header: node labels, in matrix order
//    a00,a01,...,a0,N-1           <- row 0 of frame 0's N x N 0/1 matrix
//    a10,a11,...,a1,N-1           <- row 1
//    ...                          <- N rows total
//                                    (blank line separates frames)
//    a00,a01,...                  <- row 0 of frame 1
//    ...
//
//  There is no per-frame timestamp in this format: frame i is assigned
//  time i / g_framesPerSecond (see --fps). A 1 in the matrix becomes
//  g_linkUpLossDb; a 0 becomes g_linkDownLossDb; both values are always
//  written for every i<j pair (this format has no "missing" entries).
//  Matrix asymmetry (A[i][j] != A[j][i]) is treated as an error, since
//  the network model here is undirected.
// ------------------------------------------------------------------
static bool
LoadFramesCsv(const std::string& filename)
{
    g_frames.clear();
    g_nodes.clear();
    g_frameDimension = 0;

    std::ifstream ifs(filename);
    if (!ifs.is_open()) { std::cerr << "Cannot open: " << filename << "\n"; return false; }

    auto trim = [](std::string s) {
        while (!s.empty() && isspace((unsigned char)s.front())) s.erase(s.begin());
        while (!s.empty() && isspace((unsigned char)s.back()))  s.pop_back();
        return s;
    };

    std::string line;
    while (std::getline(ifs, line))
        if (line.find_first_not_of(" \t\r\n") != std::string::npos) break;
    if (line.empty()) { std::cerr << "Empty frames file: " << filename << "\n"; return false; }

    {
        std::istringstream ss(line);
        std::string tok;
        while (std::getline(ss, tok, ',')) {
            tok = trim(tok);
            if (!tok.empty()) g_nodes.push_back(tok);
        }
    }
    g_frameDimension = (uint32_t)g_nodes.size();
    if (g_frameDimension == 0) {
        std::cerr << "No node labels found on header line of " << filename << "\n";
        return false;
    }

    auto parseRow = [&](const std::string& rowLine) {
        std::vector<int> row;
        row.reserve(g_frameDimension);
        std::istringstream rs(rowLine);
        std::string tok;
        while (std::getline(rs, tok, ',')) {
            tok = trim(tok);
            if (tok.empty()) continue;
            row.push_back(std::stoi(tok));
        }
        return row;
    };

    std::vector<std::vector<int>> rows;
    rows.reserve(g_frameDimension);

    auto flushFrame = [&]() {
        if (rows.empty()) return;
        const size_t frameIdx = g_frames.size();
        if (rows.size() != g_frameDimension) {
            std::cerr << "Warning: frame " << frameIdx << " has " << rows.size()
                      << " rows, expected " << g_frameDimension
                      << " (from header); skipping malformed frame\n";
            rows.clear();
            return;
        }
        for (uint32_t i = 0; i < g_frameDimension; ++i) {
            if (rows[i].size() != g_frameDimension) {
                std::cerr << "Warning: frame " << frameIdx << " row " << i << " has "
                          << rows[i].size() << " values, expected " << g_frameDimension
                          << "; skipping malformed frame\n";
                rows.clear();
                return;
            }
        }
        SparseFrame f;
        f.time = (double)frameIdx / g_framesPerSecond;
        for (uint32_t i = 0; i < g_frameDimension; ++i) {
            for (uint32_t j = i + 1; j < g_frameDimension; ++j) {
                if (rows[i][j] != rows[j][i]) {
                    std::cerr << "Warning: frame " << frameIdx << " is asymmetric at ("
                              << i << "," << j << "): " << rows[i][j] << " vs " << rows[j][i]
                              << "; using row-i value\n";
                }
                bool up = rows[i][j] != 0;
                f.entries.emplace_back(i, j, up ? g_linkUpLossDb : g_linkDownLossDb);
            }
        }
        g_frames.push_back(std::move(f));
        rows.clear();
    };

    while (std::getline(ifs, line)) {
        if (line.find_first_not_of(" \t\r\n") == std::string::npos) {
            flushFrame();
            continue;
        }
        rows.push_back(parseRow(line));
    }
    flushFrame(); // last frame has no trailing blank line

    if (g_frames.empty()) {
        std::cerr << "No complete " << g_frameDimension << "x" << g_frameDimension
                  << " frames parsed from " << filename << "\n";
        return false;
    }

    // Warm-up: prepend whole frames (spaced 1/fps) in which every link that is
    // up in ANY trace frame is up, and shift the trace by the warm-up length.
    g_warmupEffective = 0.0;
    g_traceStartFrame = 0;
    if (g_warmupSec > 0.0) {
        const uint32_t nWarm = (uint32_t)std::ceil(g_warmupSec * g_framesPerSecond);
        std::set<std::pair<uint32_t, uint32_t>> upAny;
        for (const auto& fr : g_frames) {
            for (const auto& [i, j, loss] : fr.entries)
                if (loss == g_linkUpLossDb) upAny.insert({i, j});
            if (g_warmupMode == "first") break;
        }
        SparseFrame warm;
        for (uint32_t i = 0; i < g_frameDimension; ++i)
            for (uint32_t j = i + 1; j < g_frameDimension; ++j)
                warm.entries.emplace_back(i, j, upAny.count({i, j}) ? g_linkUpLossDb
                                                                    : g_linkDownLossDb);
        g_warmupEffective = (double)nWarm / g_framesPerSecond;
        g_traceStartFrame = nWarm;
        for (auto& fr : g_frames) fr.time += g_warmupEffective;
        std::vector<SparseFrame> all;
        for (uint32_t k = 0; k < nWarm; ++k) {
            SparseFrame w = warm;
            w.time = (double)k / g_framesPerSecond;
            all.push_back(std::move(w));
        }
        for (auto& fr : g_frames) all.push_back(std::move(fr));
        g_frames = std::move(all);
    }
    return true;
}

// ============================================================
//  Replay runner: stationary nodes + TraceMatrixPropagationLossModel
//  fed entirely from the loaded CSV. No mobility model, no physical
//  propagation model, nothing captured — frames are scheduled at
//  i / fps (LoadFramesCsv already stamped each frame's .time this way,
//  since the adjacency-matrix format carries no timestamps of its own).
// ============================================================
static PerfMetrics
runTraceReplay(const std::string& routing,
               const std::vector<FlowPair>& flows,
               const std::string& dataRate,
               uint32_t           packetSize,
               double             defaultLossDb,
               double             txPowerDbm)
{
    g_activeFlows = flows;
    g_flowStatistics.assign(g_a3Instrumentation ? flows.size() : 0, FlowStatistics{});
    g_flowIndexByAddress.clear();
    g_nodeControlPackets.clear();
    g_nodeControlBytes.clear();
    g_nodeForwardedData.clear();
    g_nodeMacDataFailed.clear();
    g_nodeMacFinalDataFailed.clear();
    g_nodeMacTxDrop.clear();
    g_nodeMacQueueDrop.clear();
    g_nodePhyRxReasons.clear();
    g_nodePhyRxClasses.clear();
    g_nodeByMacAddress.clear();
    g_activeRouting = routing;
    if (g_a3bForwardLog.is_open()) g_a3bForwardLog.close();
    if (g_a3bControlLog.is_open()) g_a3bControlLog.close();
    if (g_a3bForwardLogEnabled) {
        g_a3bForwardLog.open(g_outDir + "/forward_events_" + routing + ".csv",
                             std::ios::out | std::ios::trunc);
        g_a3bControlLog.open(g_outDir + "/control_events_" + routing + ".csv",
                             std::ios::out | std::ios::trunc);
        NS_ABORT_MSG_UNLESS(g_a3bForwardLog.is_open() && g_a3bControlLog.is_open(),
                            "Could not open A3b diagnostic event logs");
        g_a3bForwardLog << "time_s,node_id,source,destination,source_port,destination_port,"
                           "sequence,app_timestamp_s,packet_uid,source_is_local,"
                           "destination_is_local,counts_as_forward\n";
        g_a3bControlLog << "time_s,direction,node_id,message_type,packet_uid\n";
    }
    g_controlPackets.clear();
    g_controlBytes.clear();
    g_staticRoutes.clear();
    g_traceMobModels.clear();
    g_traceTxCb = g_traceRxCb = g_traceApplyCb = 0;
    g_traceRoutingTx = g_traceRoutingRx = 0;

    // Each protocol run in this process constructs its own set of
    // automatic-stream objects (TraceMatrixPropagationLossModel included);
    // reset the counter so every protocol gets the same automatic-stream
    // baseline instead of drifting further with each successive run.
    RngSeedManager::ResetNextStreamIndex();

    // flows already hold positions in g_nodes (resolved in main()).
    const std::vector<FlowPair>& resolvedFlows = flows;
    if (resolvedFlows.empty()) {
        std::cerr << "No flows given to trace replay\n";
        return PerfMetrics();
    }
    g_oracleSource = resolvedFlows.front().senderIdx;
    g_oracleDestination = resolvedFlows.front().receiverIdx;
    g_oracle = ComputeOracleMetrics();

    NodeContainer nodes;
    nodes.Create(g_nodes.size());

    // Stationary nodes placed in a circle; positions are irrelevant here,
    // the trace loss model supplies explicit per-pair loss values.
    Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
    for (uint32_t i = 0; i < g_nodes.size(); ++i) {
        double angle = (2.0 * M_PI * i) / (double)g_nodes.size();
        posAlloc->Add(Vector(50.0 * std::cos(angle), 50.0 * std::sin(angle), 0.0));
    }
    MobilityHelper mob;
    mob.SetPositionAllocator(posAlloc);
    mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    mob.Install(nodes);

    for (uint32_t i = 0; i < nodes.GetN(); ++i)
        g_traceMobModels.push_back(nodes.Get(i)->GetObject<MobilityModel>());

    if (g_frameDimension != nodes.GetN()) {
        std::cerr << "Warning: loaded frame dimension (" << g_frameDimension
                   << ") does not match replay node count (" << nodes.GetN()
                   << "); DoCalcRxPower will fall back to DefaultLoss for "
                      "any mismatched pair.\n";
    }

    Ptr<TraceMatrixPropagationLossModel> mp = CreateObject<TraceMatrixPropagationLossModel>();
    mp->InitializeNodes(g_traceMobModels);
    mp->SetDefaultLoss(defaultLossDb);
    mp->SetStorageMode(TraceMatrixPropagationLossModel::StorageMode::SPARSE);
    mp->SetSymmetric(true);
    mp->SetSparseThreshold(g_lossThresholdDb);
    mp->SetInterpolate(g_traceInterpolate);
    g_traceLossModel = mp;

    Ptr<YansWifiChannel> channel = CreateObject<YansWifiChannel>();
    channel->SetPropagationLossModel(mp);
    channel->SetPropagationDelayModel(CreateObject<ConstantSpeedPropagationDelayModel>());

    YansWifiPhyHelper phy;
    phy.SetChannel(channel);
    // The loaded loss values are path loss only (rxPower = txPower - loss),
    // so the TX power configured here must match whatever TX power was
    // actually in effect wherever this CSV's frames were originally
    // produced, or every replayed rx power is off by a constant offset.
    phy.Set("TxPowerStart", DoubleValue(txPowerDbm));
    phy.Set("TxPowerEnd",   DoubleValue(txPowerDbm));
    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");
    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211g);
    NetDeviceContainer devices = wifi.Install(phy, mac, nodes);
    WifiHelper::AssignStreams(devices, kWifiStreamBase);
    for (uint32_t i = 0; i < devices.GetN(); ++i) {
        Ptr<WifiNetDevice> wifiDevice = DynamicCast<WifiNetDevice>(devices.Get(i));
        if (wifiDevice) g_nodeByMacAddress[Mac48Address::ConvertFrom(wifiDevice->GetAddress())] = i;
    }

    InternetStackHelper internet;
    if (routing == "static") {
        Ipv4StaticRoutingHelper staticRouting;
        internet.SetRoutingHelper(staticRouting);
    } else if (routing == "aodv") {
        AodvHelper aodv;
        internet.SetRoutingHelper(aodv);
    } else if (routing == "dsdv") {
        DsdvHelper dsdv;
        internet.SetRoutingHelper(dsdv);
    } else {
        OlsrHelper olsr;
        internet.SetRoutingHelper(olsr);
    }
    internet.Install(nodes);
    internet.AssignStreams(nodes, kRoutingStreamBase);

    Ipv4AddressGenerator::Reset();
    Ipv4AddressHelper addr;
    addr.SetBase("10.1.0.0", "255.255.0.0");
    Ipv4InterfaceContainer ifc = addr.Assign(devices);
    if (g_a3Instrumentation) {
        for (uint32_t i = 0; i < resolvedFlows.size(); ++i) {
            const auto& flow = resolvedFlows[i];
            g_flowIndexByAddress[{ifc.GetAddress(flow.senderIdx).Get(),
                                  ifc.GetAddress(flow.receiverIdx).Get()}] = i;
        }
    }
    g_replayNodes = nodes;
    g_replayInterfaces = ifc;
    g_oracleDestinationAddress = ifc.GetAddress(g_oracleDestination);
    if (routing == "static") {
        for (uint32_t i = 0; i < nodes.GetN(); ++i) {
            Ptr<Ipv4> ipv4 = nodes.Get(i)->GetObject<Ipv4>();
            g_staticRoutes.push_back(Ipv4RoutingHelper::GetRouting<Ipv4StaticRouting>(
                ipv4->GetRoutingProtocol()));
        }
    }

    g_traceTracker.reset();

    // stopTime comes straight from the last frame's own recorded
    // timestamp, not from a separately-supplied interval * frame count.
    const double stopTime = g_frames.empty() ? 0.0 : g_frames.back().time;
    DataRate dr(dataRate);
    double intervalSec = (double)packetSize * 8.0 / (double)dr.GetBitRate();

    UdpServerHelper udpServer(APP_PORT);
    ApplicationContainer sinkApps;
    ApplicationContainer clientApps;
    std::set<uint32_t> sinkInstalled;
    for (uint32_t flowIndex = 0; flowIndex < resolvedFlows.size(); ++flowIndex) {
        const auto& flow = resolvedFlows[flowIndex];
        if (sinkInstalled.insert(flow.receiverIdx).second) {
            sinkApps.Add(udpServer.Install(nodes.Get(flow.receiverIdx)));
        }
        UdpClientHelper udpClient(ifc.GetAddress(flow.receiverIdx), APP_PORT);
        udpClient.SetAttribute("MaxPackets", UintegerValue(std::numeric_limits<uint32_t>::max()));
        udpClient.SetAttribute("Interval",   TimeValue(Seconds(intervalSec)));
        udpClient.SetAttribute("PacketSize", UintegerValue(packetSize));
        ApplicationContainer client = udpClient.Install(nodes.Get(flow.senderIdx));
        if (g_a3Instrumentation) {
            client.Get(0)->TraceConnectWithoutContext("Tx",
                MakeBoundCallback(&TraceUdpClientTxForFlow, flowIndex));
        } else {
            client.Get(0)->TraceConnectWithoutContext("Tx", MakeCallback(&TraceUdpClientTx));
        }
        clientApps.Add(client);
        if (g_a3Instrumentation) {
            const double start = g_warmupEffective + 0.1 +
                static_cast<double>(flowIndex) / resolvedFlows.size();
            g_flowStatistics[flowIndex].configuredStartTime = start;
            client.Start(Seconds(start));
            client.Stop(Seconds(stopTime));
        }
    }
    sinkApps.Start(Seconds(0.0));
    sinkApps.Stop(Seconds(stopTime + 1.0));
    if (!g_a3Instrumentation) {
        clientApps.Start(Seconds(g_warmupEffective + 0.1));
        clientApps.Stop(Seconds(stopTime));
    }

    // Safe high loss before the first frame is applied.
    g_traceLossModel->SetAllLoss(defaultLossDb);

    // Schedule each frame at i / fps (frame 0 lands at t=0, immediately
    // overwriting the SetAllLoss() call above).
    for (uint32_t t = 0; t < g_frames.size(); ++t) {
        Simulator::Schedule(Seconds(g_frames[t].time), &TraceApplyFrame, t);
        if (routing == "static" && g_staticOracleMode == "frame")
            Simulator::Schedule(Seconds(g_frames[t].time), &UpdateOracleStaticRoutes, t);
    }
    if (routing == "static" && g_staticOracleMode == "usable") {
        std::set<double> routeUpdateTimes;
        for (const auto& frame : g_frames) routeUpdateTimes.insert(frame.time);
        if (g_traceInterpolate) {
            const double usableLossLimitDb = g_txPowerDbm - g_rxSensitivityDbm;
            for (size_t i = 0; i + 1 < g_frames.size(); ++i) {
                const double span = g_frames[i + 1].time - g_frames[i].time;
                if (span <= 0.0) continue;
                for (const auto& [a, b, rawCurrentLoss] : g_frames[i].entries) {
                    const double rawNextLoss = FrameLoss(g_frames[i + 1], a, b);
                    const double currentLoss = rawCurrentLoss < g_lossThresholdDb
                        ? rawCurrentLoss : g_defaultLossDb;
                    const double nextLoss = rawNextLoss < g_lossThresholdDb
                        ? rawNextLoss : g_defaultLossDb;
                    if (currentLoss == nextLoss) continue;
                    const double alpha = (usableLossLimitDb - currentLoss) /
                                         (nextLoss - currentLoss);
                    if (alpha > 0.0 && alpha < 1.0)
                        routeUpdateTimes.insert(g_frames[i].time + alpha * span);
                }
            }
        }
        for (double time : routeUpdateTimes)
            Simulator::Schedule(Seconds(time), &UpdateOracleStaticRoutesAtUsableTime, time);
    }

    for (uint32_t i = 0; i < nodes.GetN(); ++i) {
        Ptr<Ipv4> ipv4 = nodes.Get(i)->GetObject<Ipv4>();
        if (ipv4) {
            ipv4->TraceConnectWithoutContext("Tx",   MakeCallback(&TraceIpTxCb));
            ipv4->TraceConnectWithoutContext("Rx",   MakeCallback(&TraceIpRxCb));
            ipv4->TraceConnectWithoutContext("Drop", MakeCallback(&TraceIpDropCb));
            if (g_a3Instrumentation) {
                const Ptr<Node> node = ipv4->GetObject<Node>();
                if (node) ipv4->TraceConnectWithoutContext("UnicastForward",
                    MakeBoundCallback(&TraceIpForward, node->GetId()));
            }
        }
        for (uint32_t j = 0; j < nodes.Get(i)->GetNDevices(); ++j) {
            Ptr<WifiNetDevice> wd = DynamicCast<WifiNetDevice>(nodes.Get(i)->GetDevice(j));
            if (wd) {
                wd->GetPhy()->TraceConnectWithoutContext("PhyTxDrop", MakeCallback(&TracePhyTxDrop));
                wd->GetPhy()->TraceConnectWithoutContext("PhyRxDrop",
                    MakeBoundCallback(&TracePhyRxDrop, i));
                if (g_dumpRoutes || g_a3Instrumentation) {
                    wd->GetMac()->TraceConnectWithoutContext("MacTxDrop",
                        MakeBoundCallback(&TraceMacTxDropForNode, i));
                    Ptr<WifiMacQueue> queue = wd->GetMac()->GetTxopQueue(AC_BE_NQOS);
                    if (queue)
                        queue->TraceConnectWithoutContext("Drop",
                            MakeBoundCallback(&TraceMacQueueDropForNode, i));
                }
                if (g_a3Instrumentation) {
                    Ptr<WifiRemoteStationManager> stationManager = wd->GetRemoteStationManager();
                    if (stationManager) {
                        stationManager->TraceConnectWithoutContext("MacTxDataFailed",
                            MakeBoundCallback(&TraceMacDataFailed, i));
                        stationManager->TraceConnectWithoutContext("MacTxFinalDataFailed",
                            MakeBoundCallback(&TraceMacFinalDataFailed, i));
                    }
                }
            }
        }
    }

    if (g_dumpRoutes) {
        Ptr<OutputStreamWrapper> rt =
            Create<OutputStreamWrapper>(g_outDir + "/routes_" + routing + ".txt", std::ios::out);
        Ipv4RoutingHelper::PrintRoutingTableAllEvery(Seconds(1.0), rt);
    }

    Simulator::Stop(Seconds(stopTime));

    auto         wallStart = std::chrono::high_resolution_clock::now();
    std::clock_t cpuStart  = std::clock();

    Simulator::Run();

    std::clock_t cpuEnd  = std::clock();
    auto         wallEnd = std::chrono::high_resolution_clock::now();

    PerfMetrics p;
    p.wall_time_s       = std::chrono::duration<double>(wallEnd - wallStart).count();
    p.cpu_time_s        = double(cpuEnd - cpuStart) / CLOCKS_PER_SEC;
    p.ip_tx_cb_calls    = g_traceTxCb;
    p.ip_rx_cb_calls    = g_traceRxCb;
    p.frame_apply_calls = g_traceApplyCb;
    p.routing_tx        = g_traceRoutingTx;
    p.routing_rx        = g_traceRoutingRx;
    FillAppMetrics(p, g_traceTracker, stopTime);
    for (const auto& [kind, count] : g_controlPackets) {
        p.control_packets += count;
        p.control_message_counts[kind] = count;
    }
    for (const auto& [kind, bytes] : g_controlBytes) {
        p.control_bytes += bytes;
        p.control_message_bytes[kind] = bytes;
    }
    p.routing_efficiency = g_oracle.uptimeRatio > 0.0
        ? p.pdr / g_oracle.uptimeRatio : std::numeric_limits<double>::quiet_NaN();

    const double frameDuration = 1.0 / g_framesPerSecond;
    for (size_t i = 0; i < g_oracle.connected.size();) {
        if (g_oracle.connected[i]) {
            ++i;
            continue;
        }
        const size_t outageStart = i;
        while (i < g_oracle.connected.size() && !g_oracle.connected[i]) ++i;
        p.recovered_outage_durations.push_back((i - outageStart) * frameDuration);
        double reestablishment = std::numeric_limits<double>::quiet_NaN();
        if (i < g_oracle.connected.size()) {
            const double linkUpTime = g_frames[g_traceStartFrame + i].time;
            size_t nextDown = i + 1;
            while (nextDown < g_oracle.connected.size() && g_oracle.connected[nextDown]) ++nextDown;
            const double nextDownTime = nextDown < g_oracle.connected.size()
                ? g_frames[g_traceStartFrame + nextDown].time
                : stopTime + frameDuration;
            auto delivered = std::find_if(g_traceTracker.rxTimes.begin(), g_traceTracker.rxTimes.end(),
                [linkUpTime, nextDownTime](double t) { return t >= linkUpTime && t < nextDownTime; });
            if (delivered != g_traceTracker.rxTimes.end()) reestablishment = *delivered - linkUpTime;
        }
        p.reestablishment_times.push_back(reestablishment);
    }

    if (g_dumpRoutes) {
        const TrafficWindowOracleMetrics windowOracle = ComputeTrafficWindowOracleMetrics();
        std::ofstream tf(g_outDir + "/times_" + routing + ".csv");
        tf << "kind,t\n" << std::fixed << std::setprecision(6);
        for (double v : g_traceTracker.txTimes) tf << "tx," << v << "\n";
        for (double v : g_traceTracker.rxTimes) tf << "rx," << v << "\n";

        std::ofstream pf(g_outDir + "/packets_" + routing + ".csv");
        pf << "event,sequence,app_tx_time_s,event_time_s,delay_s,frame_connected,usable_connected\n"
           << std::fixed << std::setprecision(9);
        for (const auto& event : g_traceTracker.packetEvents) {
            pf << event.kind << ',' << event.sequence << ',';
            if (std::isfinite(event.appTxTime)) pf << event.appTxTime;
            pf << ',' << event.eventTime << ',';
            if (std::isfinite(event.delay)) pf << event.delay;
            pf << ',' << (event.frameConnected ? 1 : 0)
               << ',' << (event.usableConnected ? 1 : 0) << '\n';
        }

        std::ofstream df(g_outDir + "/packet_diagnostics_" + routing + ".csv");
        df << "app_tx_packets,sink_rx_total,sink_rx_unique,sink_rx_duplicates,"
              "app_ip_no_route_drops,app_ip_route_error_drops,mac_queue_drop_callbacks,"
              "mac_tx_drop_callbacks,phy_tx_drop_callbacks,phy_rx_drop_callbacks\n"
           << g_traceTracker.appTxPkts << ',' << g_traceTracker.appRxPkts << ','
           << g_traceTracker.rxSequences.size() << ',' << g_traceTracker.duplicateRxPkts << ','
           << g_traceTracker.appIpDropNoRoute << ',' << g_traceTracker.appIpDropRouteErr << ','
           << g_traceTracker.macQueueDrop << ',' << g_traceTracker.macTxDrop << ','
           << g_traceTracker.phyTxDrop << ',' << g_traceTracker.phyRxDrop << '\n';

        std::ofstream of(g_outDir + "/oracle_diagnostics_" + routing + ".csv");
        of << "trace_frame_uptime,traffic_start_s,traffic_stop_s,traffic_window_s,"
              "traffic_frame_uptime,traffic_usable_uptime,usable_loss_limit_db\n"
           << std::fixed << std::setprecision(9)
           << g_oracle.uptimeRatio << ',' << windowOracle.startTime << ','
           << windowOracle.stopTime << ','
           << windowOracle.stopTime - windowOracle.startTime << ','
           << windowOracle.frameUptime << ',' << windowOracle.usableUptime << ','
           << g_txPowerDbm - g_rxSensitivityDbm << '\n';
    }

    if (g_a3bForwardLog.is_open()) {
        g_a3bForwardLog.flush();
        g_a3bForwardLog.close();
    }
    if (g_a3bControlLog.is_open()) {
        g_a3bControlLog.flush();
        g_a3bControlLog.close();
    }
    Simulator::Destroy();
    return p;
}

static void
ComputeStaticHopDistances()
{
    std::vector<std::set<uint32_t>> adjacency(g_frameDimension);
    for (const auto& frame : g_frames) {
        for (const auto& [a, b, loss] : frame.entries) {
            if (loss == g_linkUpLossDb) {
                adjacency[a].insert(b);
                adjacency[b].insert(a);
            }
        }
    }
    g_staticHopDistances.assign(g_frameDimension, std::vector<int>(g_frameDimension, -1));
    for (uint32_t source = 0; source < g_frameDimension; ++source) {
        std::queue<uint32_t> pending;
        g_staticHopDistances[source][source] = 0;
        pending.push(source);
        while (!pending.empty()) {
            const uint32_t here = pending.front();
            pending.pop();
            for (uint32_t next : adjacency[here]) {
                if (g_staticHopDistances[source][next] < 0) {
                    g_staticHopDistances[source][next] = g_staticHopDistances[source][here] + 1;
                    pending.push(next);
                }
            }
        }
    }
}

static void
InitializeA3OutputFiles()
{
    std::ofstream flows(g_outDir + "/flows.csv", std::ios::out | std::ios::trunc);
    flows << "protocol,flow_id,source,destination,is_probe,static_hop_distance,offered_packets,"
             "delivered_unique_packets,median_delay_s,p95_delay_s,first_delivery_s,"
             "probe_convergence_s\n";
    std::ofstream nodes(g_outDir + "/node_diagnostics.csv", std::ios::out | std::ios::trunc);
    nodes << "protocol,node_id,metric,message_type,phy_reason,value\n";
    std::ofstream distances(g_outDir + "/static_hop_distances.csv", std::ios::out | std::ios::trunc);
    distances << "source,destination,static_hop_distance\n";
    for (uint32_t source = 0; source < g_frameDimension; ++source) {
        for (uint32_t destination = source + 1; destination < g_frameDimension; ++destination) {
            distances << g_nodes[source] << ',' << g_nodes[destination] << ','
                      << g_staticHopDistances[source][destination] << '\n';
        }
    }
}

static double
ProbeConvergenceTime(const FlowStatistics& stats, double stopTime)
{
    constexpr double kWindowSeconds = 10.0;
    const double firstFullWindow = stats.configuredStartTime + kWindowSeconds;
    if (stopTime < firstFullWindow) return std::numeric_limits<double>::quiet_NaN();
    std::set<double> windowEnds{firstFullWindow, stopTime};
    auto addBoundaries = [&](const std::vector<double>& times) {
        for (double time : times) {
            if (time >= firstFullWindow && time <= stopTime) windowEnds.insert(time);
            const double expiry = time + kWindowSeconds;
            if (expiry >= firstFullWindow && expiry <= stopTime) windowEnds.insert(expiry);
        }
    };
    addBoundaries(stats.txTimes);
    addBoundaries(stats.rxTimes);

    std::vector<double> ends(windowEnds.begin(), windowEnds.end());
    std::vector<bool> passes;
    passes.reserve(ends.size());
    for (double end : ends) {
        const double begin = end - kWindowSeconds;
        const auto txBegin = std::upper_bound(stats.txTimes.begin(), stats.txTimes.end(), begin);
        const auto txEnd = std::upper_bound(stats.txTimes.begin(), stats.txTimes.end(), end);
        const auto rxBegin = std::upper_bound(stats.rxTimes.begin(), stats.rxTimes.end(), begin);
        const auto rxEnd = std::upper_bound(stats.rxTimes.begin(), stats.rxTimes.end(), end);
        const auto txCount = std::distance(txBegin, txEnd);
        const auto rxCount = std::distance(rxBegin, rxEnd);
        passes.push_back(txCount > 0 && static_cast<double>(rxCount) / txCount >= 0.99);
    }
    bool suffixPasses = true;
    double convergence = std::numeric_limits<double>::quiet_NaN();
    for (size_t i = ends.size(); i-- > 0;) {
        suffixPasses = suffixPasses && passes[i];
        if (suffixPasses) convergence = ends[i];
    }
    return convergence;
}

static void
AppendA3RunOutputs(const std::string& protocol, double stopTime)
{
    std::ofstream flows(g_outDir + "/flows.csv", std::ios::out | std::ios::app);
    for (uint32_t i = 0; i < g_activeFlows.size(); ++i) {
        const auto& flow = g_activeFlows[i];
        const auto& stats = g_flowStatistics[i];
        const int hops = g_staticHopDistances[flow.senderIdx][flow.receiverIdx];
        const double firstDelivery = stats.rxTimes.empty() ? std::numeric_limits<double>::quiet_NaN()
                                                           : *std::min_element(stats.rxTimes.begin(), stats.rxTimes.end());
        const double convergence = flow.probe ? ProbeConvergenceTime(stats, stopTime)
                                              : std::numeric_limits<double>::quiet_NaN();
        flows << protocol << ',' << i << ',' << g_nodes[flow.senderIdx] << ',' << g_nodes[flow.receiverIdx]
              << ',' << (flow.probe ? 1 : 0) << ',';
        if (hops < 0) flows << "NA";
        else flows << hops;
        flows << ',' << stats.offered << ',' << stats.delivered << ',' << std::fixed << std::setprecision(9)
              << Quantile(stats.delays, 0.5) << ',' << Quantile(stats.delays, 0.95) << ','
              << firstDelivery << ',' << convergence << '\n';
    }

    std::ofstream nodes(g_outDir + "/node_diagnostics.csv", std::ios::out | std::ios::app);
    auto writeMetric = [&](uint32_t node, const std::string& metric,
                           const std::string& messageType, const std::string& phyReason, uint64_t value) {
        nodes << protocol << ',' << node << ',' << metric << ',' << messageType << ','
              << phyReason << ',' << value << '\n';
    };
    std::vector<std::string> controlKinds = {
        "olsr_hello", "olsr_tc", "olsr_mid", "olsr_hna", "olsr_other",
        "aodv_hello", "aodv_rreq", "aodv_rrep", "aodv_rerr", "aodv_rrep_ack", "aodv_other",
        "dsdv_update", "dsdv_other", "static_other"
    };
    if (g_emitControlUnparsedColumns) controlKinds.push_back("olsr_unparsed");
    const std::vector<std::string> classes = {
        "below_sensitivity", "collision_interference", "other_unclassified"
    };
    for (uint32_t node = 0; node < g_nodes.size(); ++node) {
        for (const auto& kind : controlKinds) {
            const uint64_t packets = g_nodeControlPackets[node][kind];
            const uint64_t bytes = g_nodeControlBytes[node][kind];
            writeMetric(node, "control_tx_packets", kind, "", packets);
            writeMetric(node, "control_tx_bytes", kind, "", bytes);
        }
        writeMetric(node, "forwarded_app_packets_ipv4", "", "", g_nodeForwardedData[node]);
        writeMetric(node, "mac_data_failed_events", "", "", g_nodeMacDataFailed[node]);
        writeMetric(node, "mac_final_data_failed", "", "", g_nodeMacFinalDataFailed[node]);
        writeMetric(node, "mac_tx_drops", "", "", g_nodeMacTxDrop[node]);
        writeMetric(node, "mac_queue_drops", "", "", g_nodeMacQueueDrop[node]);
        for (const auto& [reason, count] : g_nodePhyRxReasons[node])
            writeMetric(node, "phy_rx_drop_raw_reason", "", reason, count);
        for (const auto& category : classes)
            writeMetric(node, "phy_rx_drop_class", "", category, g_nodePhyRxClasses[node][category]);
    }
}

static bool
SameFlowSelection(const std::vector<FlowPair>& left, const std::vector<FlowPair>& right)
{
    if (left.size() != right.size()) return false;
    for (size_t i = 0; i < left.size(); ++i) {
        if (left[i].senderIdx != right[i].senderIdx ||
            left[i].receiverIdx != right[i].receiverIdx || left[i].probe != right[i].probe)
            return false;
    }
    return true;
}

static int
RunA3HelperSelfTests()
{
    bool selectionPass = true;
    bool sawReverseDirection = false;
    for (uint32_t n : {4U, 8U}) {
        for (double fraction : {0.0, 0.1, 0.25, 0.5, 0.75}) {
            for (uint32_t seed : {11U, 29U, 47U}) {
                const FlowPair probe{0, n - 1, true};
                std::string error;
                const auto selected = GenerateFractionFlowPairs(n, fraction, probe, seed, error);
                const auto repeated = GenerateFractionFlowPairs(n, fraction, probe, seed, error);
                const uint64_t expected = static_cast<uint64_t>(std::llround(
                    fraction * static_cast<uint64_t>(n) * (n - 1) / 2));
                std::set<std::pair<uint32_t, uint32_t>> unordered;
                bool valid = error.empty() && selected.size() == expected + 1 &&
                             SameFlowSelection(selected, repeated) && selected.front().probe;
                for (size_t i = 0; i < selected.size(); ++i) {
                    const auto& flow = selected[i];
                    valid = valid && flow.senderIdx != flow.receiverIdx &&
                            flow.probe == (i == 0);
                    const auto pair = std::minmax(flow.senderIdx, flow.receiverIdx);
                    valid = valid && unordered.insert(pair).second;
                    if (i > 0) {
                        valid = valid && pair != std::minmax(probe.senderIdx, probe.receiverIdx);
                        sawReverseDirection = sawReverseDirection || flow.senderIdx > flow.receiverIdx;
                    }
                }
                selectionPass = selectionPass && valid;
            }
        }
    }

    auto makeStats = [](uint32_t firstRx, bool alternate) {
        FlowStatistics stats;
        stats.configuredStartTime = 0.0;
        for (uint32_t t = 0; t <= 40; ++t) {
            stats.txTimes.push_back(static_cast<double>(t));
            if ((alternate && t % 2 == 0) || (!alternate && t >= firstRx))
                stats.rxTimes.push_back(static_cast<double>(t));
        }
        return stats;
    };
    const auto immediate = makeStats(0, false);
    const auto delayed = makeStats(15, false);
    const auto never = makeStats(0, true);
    const double immediateConvergence = ProbeConvergenceTime(immediate, 40.0);
    const double delayedConvergence = ProbeConvergenceTime(delayed, 40.0);
    const double neverConvergence = ProbeConvergenceTime(never, 40.0);
    const bool convergencePass = immediate.rxTimes.front() == 0.0 && immediateConvergence == 10.0 &&
                                 delayed.rxTimes.front() == 15.0 && delayedConvergence == 24.0 &&
                                 never.rxTimes.front() == 0.0 && std::isnan(neverConvergence);

    std::ofstream out(g_outDir + "/a3_selftest.json");
    out << "{\n  \"flow_selection_pass\": " << (selectionPass ? "true" : "false")
        << ",\n  \"reverse_direction_observed\": " << (sawReverseDirection ? "true" : "false")
        << ",\n  \"probe_convergence_pass\": " << (convergencePass ? "true" : "false")
        << ",\n  \"immediate_convergence_s\": " << immediateConvergence
        << ",\n  \"delayed_convergence_s\": " << delayedConvergence
        << ",\n  \"never_convergence_is_nan\": " << (std::isnan(neverConvergence) ? "true" : "false")
        << "\n}\n";
    std::cout << "A3 helper self-tests: flow_selection=" << (selectionPass ? "PASS" : "FAIL")
              << ", convergence=" << (convergencePass ? "PASS" : "FAIL") << "\n";
    return selectionPass && sawReverseDirection && convergencePass ? 0 : 1;
}

// ============================================================
//  Split a comma-separated protocol list, validating each entry.
// ============================================================
static std::vector<std::string>
ResolveProtocolList(const std::string& routing)
{
    if (routing == "all") return {"olsr", "aodv", "dsdv"};

    std::vector<std::string> out;
    std::stringstream ss(routing);
    std::string tok;
    while (std::getline(ss, tok, ',')) {
        while (!tok.empty() && isspace((unsigned char)tok.front())) tok.erase(tok.begin());
        while (!tok.empty() && isspace((unsigned char)tok.back()))  tok.pop_back();
        if (tok != "olsr" && tok != "aodv" && tok != "dsdv" && tok != "static") {
            std::cerr << "Unknown routing protocol '" << tok
                      << "'. Expected one of: olsr, aodv, dsdv, static, all\n";
            continue;
        }
        out.push_back(tok);
    }
    return out;
}

// ============================================================
//  Main
// ============================================================
int
main(int argc, char* argv[])
{
    std::string framesCsv      = "";     // required: path to the dense adjacency-matrix CSV
    std::string outDir         = "scratch/trace-replay-results";
    std::string routing        = "all";  // olsr|aodv|dsdv|all, or comma list
    uint32_t    numFlows       = 30;
    std::string flowsArg       = "";     // explicit flows "SrcLabel:DstLabel[,...]"; overrides numFlows
    bool        a3Instrumentation = false;
    bool        a3SelfTest      = false;
    bool        a3bForwardLog   = false;
    bool        emitControlUnparsed = false;
    double      flowFraction   = 0.0;
    uint32_t    flowSeed       = 9001;
    uint32_t    seed           = 42;
    std::string dataRate       = "50kbps";
    uint32_t    packetSize     = 1024;
    double      lossThresholdDb = 150.0; // still passed to SetSparseThreshold
    bool        interpolate     = true;
    std::string channelProfile  = "legacy";
    double      defaultLossDb   = 1e6;   // loss (dB) before frame 0 is applied
    double      txPowerDbm      = 20.0;  // must match TX power used to produce the CSV
    double      linkUpLossDb    = 10.0;  // loss (dB) for a 1 in the adjacency matrix
    double      linkDownLossDb  = 125.0; // below sparse threshold; attenuated below receiver sensitivity
    double      fps             = 1.0;   // frame i -> time i/fps (no timestamps in this format)
    std::string sourceGitHash   = "";
    std::string ns3Commit       = "";

    CommandLine cmd;
    cmd.AddValue("framesCsv",      "Path to the dense adjacency-matrix CSV to replay (required)", framesCsv);
    cmd.AddValue("sourceGitHash",  "Optional J2 source revision for run config metadata", sourceGitHash);
    cmd.AddValue("ns3Commit",      "Optional ns-3 commit for run config metadata", ns3Commit);
    cmd.AddValue("outDir",         "Output directory for the results CSV",              outDir);
    cmd.AddValue("routing",        "olsr|aodv|dsdv|all, or a comma list",               routing);
    cmd.AddValue("numFlows",       "Number of sender->receiver traffic pairs (random, seeded)", numFlows);
    cmd.AddValue("flows",          "Explicit flows as SrcLabel:DstLabel[,SrcLabel:DstLabel...] "
                                   "(node labels from the CSV header); overrides numFlows", flowsArg);
    cmd.AddValue("instrumentation", "Enable opt-in A3 flow and per-node diagnostics", a3Instrumentation);
    cmd.AddValue("a3SelfTest",     "Run offline A3 flow-selection/convergence self-tests only", a3SelfTest);
    cmd.AddValue("a3bForwardLog",  "Write opt-in A3b packet and AODV control diagnostic logs", a3bForwardLog);
    cmd.AddValue("emitControlUnparsed", "Append control_unparsed_packets/bytes when true", emitControlUnparsed);
    cmd.AddValue("flowFraction",   "Background unordered-pair fraction for A3 (requires instrumentation)", flowFraction);
    cmd.AddValue("flowSeed",       "Independent A3 flow-selection seed", flowSeed);
    cmd.AddValue("seed",           "RNG seed (same seed -> same flows and ns-3 streams)", seed);
    cmd.AddValue("dataRate",       "Application data rate (e.g. 1Mbps)",                dataRate);
    cmd.AddValue("packetSize",     "Application packet size in bytes",                  packetSize);
    cmd.AddValue("lossThresholdDb","Loss (dB) threshold passed to SetSparseThreshold",  lossThresholdDb);
    cmd.AddValue("channelProfile", "legacy|v2; v2 opts into no interpolation", channelProfile);
    cmd.AddValue("interpolate",    "Linearly interpolate loss (dB) between frames",     interpolate);
    cmd.AddValue("defaultLossDb",  "Loss (dB) applied before frame 0 is scheduled",     defaultLossDb);
    cmd.AddValue("txPowerDbm",     "WifiPhy TX power (dBm); match the CSV's capture setup", txPowerDbm);
    cmd.AddValue("linkUpLossDb",   "Loss (dB) written for a 1 in the adjacency matrix", linkUpLossDb);
    cmd.AddValue("linkDownLossDb", "Loss (dB) written for a 0 in the adjacency matrix", linkDownLossDb);
    cmd.AddValue("fps",            "Frames per second; frame i occurs at time i/fps",   fps);
    cmd.AddValue("warmup",         "Warm-up seconds before the trace: all links ever up are held up, "
                                   "traffic starts after it; rounded up to whole frames (0 = off)", g_warmupSec);
    cmd.AddValue("warmupMode",     "union|first: warm-up topology = all links ever up, or trace frame 0", g_warmupMode);
    cmd.AddValue("dumpRoutes",     "Write routes_<proto>.txt (1 Hz routing tables) and times_<proto>.csv", g_dumpRoutes);
    cmd.AddValue("staticOracleMode", "frame|usable: static route updates from binary frames or interpolated usable links", g_staticOracleMode);
    cmd.Parse(argc, argv);
    g_outDir = outDir;
    g_a3Instrumentation = a3Instrumentation;
    g_a3bForwardLogEnabled = a3bForwardLog;
    g_emitControlUnparsedColumns = emitControlUnparsed;
    g_flowFraction = flowFraction;
    g_flowSeed = flowSeed;

    if (framesCsv.empty()) {
        std::cerr << "Missing required --framesCsv=<path>\n";
        return 1;
    }
    if (!FileExists(framesCsv)) {
        std::cerr << "Frames CSV not found: " << framesCsv << "\n";
        return 1;
    }
    if (fps <= 0.0) {
        std::cerr << "--fps must be > 0 (got " << fps << ")\n";
        return 1;
    }
    if (!std::isfinite(flowFraction) || flowFraction < 0.0 || flowFraction > 1.0) {
        std::cerr << "--flowFraction must be finite and in [0,1]\n";
        return 1;
    }
    if (!a3Instrumentation && flowFraction != 0.0) {
        std::cerr << "--flowFraction requires --instrumentation=true\n";
        return 1;
    }
    if (a3bForwardLog && !a3Instrumentation) {
        std::cerr << "--a3bForwardLog requires --instrumentation=true\n";
        return 1;
    }
    if (a3Instrumentation && flowsArg.empty()) {
        std::cerr << "A3 instrumentation requires exactly one explicit --flows probe pair\n";
        return 1;
    }
    if (channelProfile != "legacy" && channelProfile != "v2") {
        std::cerr << "--channelProfile must be 'legacy' or 'v2' (got "
                  << channelProfile << ")\n";
        return 1;
    }
    if (channelProfile == "v2") {
        // Opt-in v2 semantics. The legacy profile remains the default, and
        // explicit legacy interpolation arguments retain their old behavior.
        interpolate = false;
    }
    if (g_staticOracleMode != "frame" && g_staticOracleMode != "usable") {
        std::cerr << "--staticOracleMode must be 'frame' or 'usable' (got "
                  << g_staticOracleMode << ")\n";
        return 1;
    }

    g_lossThresholdDb  = lossThresholdDb;
    g_traceInterpolate = interpolate;
    g_linkUpLossDb     = linkUpLossDb;
    g_linkDownLossDb   = linkDownLossDb;
    g_defaultLossDb    = defaultLossDb;
    g_txPowerDbm       = txPowerDbm;
    g_framesPerSecond  = fps;

    // The original comparison script only ever set RngSeedManager's
    // seed/run inside its full-simulation phases; a trace-only run had no
    // path that did so, so --seed silently only affected flow-pair
    // selection and not ns-3's own RNG streams. Set it explicitly here so
    // one --seed argument actually controls reproducibility end to end.
    RngSeedManager::SetSeed(seed);
    RngSeedManager::SetRun(1);
    RngSeedManager::ResetNextStreamIndex();

    std::cout << "Loading frames from " << framesCsv << " ...\n";
    if (!LoadFramesCsv(framesCsv)) {
        std::cerr << "Failed to load " << framesCsv << "\n";
        return 1;
    }
    ComputeStaticHopDistances();
    if (a3SelfTest) {
        std::filesystem::create_directories(outDir);
        InitializeA3OutputFiles();
        return RunA3HelperSelfTests();
    }
    std::cout << "  Loaded " << g_frames.size() << " frames, "
              << g_nodes.size() << " nodes, dimension " << g_frameDimension << "\n";
    if (!g_frames.empty()) {
        std::cout << "  Time span: " << g_frames.front().time
                  << "s .. " << g_frames.back().time << "s\n";
    }

    const std::vector<std::string> protocols = ResolveProtocolList(routing);
    if (protocols.empty()) {
        std::cerr << "No valid routing protocols selected\n";
        return 1;
    }

    std::vector<FlowPair> flows;
    if (!flowsArg.empty()) {
        // Explicit flows: labels must match the CSV header exactly, so the
        // pair a DG was built for is the pair the network actually carries.
        std::stringstream fs(flowsArg);
        std::string item;
        while (std::getline(fs, item, ',')) {
            const auto colon = item.find(':');
            if (colon == std::string::npos) {
                std::cerr << "Bad --flows entry '" << item << "' (expected Src:Dst)\n";
                return 1;
            }
            const std::string src = item.substr(0, colon);
            const std::string dst = item.substr(colon + 1);
            auto pos = [&](const std::string& label) {
                for (uint32_t i = 0; i < g_nodes.size(); ++i)
                    if (g_nodes[i] == label) return (int)i;
                return -1;
            };
            const int si = pos(src);
            const int di = pos(dst);
            if (si < 0 || di < 0 || si == di) {
                std::cerr << "--flows entry '" << item << "': "
                          << (si < 0 ? "sender label not in CSV header; " : "")
                          << (di < 0 ? "receiver label not in CSV header; " : "")
                          << (si == di ? "sender equals receiver; " : "") << "\n";
                return 1;
            }
            flows.push_back({(uint32_t)si, (uint32_t)di});
        }
    } else {
        flows = GenerateFlowPairs(g_nodes.size(), numFlows, seed);
        if (flows.size() < numFlows) {
            std::cerr << "Warning: only generated " << flows.size() << " of " << numFlows
                      << " requested flows (" << g_nodes.size() << " nodes limits distinct pairs)\n";
        }
    }
    if (flows.empty()) {
        std::cerr << "No traffic flows generated; nothing to replay\n";
        return 1;
    }
    if (a3Instrumentation) {
        if (flows.size() != 1) {
            std::cerr << "A3 instrumentation requires exactly one explicit --flows probe pair\n";
            return 1;
        }
        flows.front().probe = true;
        std::string flowError;
        flows = GenerateFractionFlowPairs(g_nodes.size(), flowFraction, flows.front(), flowSeed, flowError);
        if (!flowError.empty() || flows.empty()) {
            std::cerr << "A3 flow generation failed: " << flowError << "\n";
            return 1;
        }
    }
    std::cout << "Traffic flows (" << flows.size() << "):";
    for (const auto& f : flows) {
        std::cout << " " << g_nodes[f.senderIdx] << "->" << g_nodes[f.receiverIdx];
    }
    std::cout << "\n";

    std::filesystem::create_directories(outDir);
    if (a3Instrumentation) InitializeA3OutputFiles();
    const std::string resultsFile = outDir + "/trace_replay_results.csv";
        std::ofstream config(outDir + "/config.json");
        config << std::fixed << std::setprecision(6)
            << "{\n  \"source_git_hash\": "
            << (sourceGitHash.empty() ? "null" : "\"" + JsonEscape(sourceGitHash) + "\"")
            << ",\n  \"ns3_commit\": "
            << (ns3Commit.empty() ? "null" : "\"" + JsonEscape(ns3Commit) + "\"")
            << ",\n  \"ns3_version\": \"unknown\",\n"
            << "  \"created_at_epoch_s\": " << std::time(nullptr) << ",\n"
            << "  \"frames_csv\": \"" << JsonEscape(framesCsv) << "\",\n"
            << "  \"out_dir\": \"" << JsonEscape(outDir) << "\",\n"
            << "  \"routing\": \"" << JsonEscape(routing) << "\",\n"
            << "  \"protocols\": [";
        for (size_t i = 0; i < protocols.size(); ++i) {
         if (i) config << ", ";
         config << "\"" << JsonEscape(protocols[i]) << "\"";
        }
        config << "],\n  \"flows\": [";
        for (size_t i = 0; i < flows.size(); ++i) {
         if (i) config << ", ";
         config << "{\"source\": \"" << JsonEscape(g_nodes[flows[i].senderIdx])
             << "\", \"destination\": \""
             << JsonEscape(g_nodes[flows[i].receiverIdx]) << "\"}";
        }
        config << "],\n  \"seed\": " << seed
            << ",\n  \"data_rate\": \"" << JsonEscape(dataRate) << "\",\n"
            << "  \"packet_size_bytes\": " << packetSize << ",\n"
            << "  \"channel_profile\": \"" << JsonEscape(channelProfile) << "\",\n"
            << "  \"loss_threshold_db\": " << lossThresholdDb << ",\n"
            << "  \"interpolate\": " << (interpolate ? "true" : "false") << ",\n"
            << "  \"default_loss_db\": " << defaultLossDb << ",\n"
            << "  \"tx_power_dbm\": " << txPowerDbm << ",\n"
            << "  \"link_up_loss_db\": " << linkUpLossDb << ",\n"
            << "  \"link_down_loss_db\": " << linkDownLossDb << ",\n"
            << "  \"fps\": " << fps << ",\n"
            << "  \"frame_duration_s\": " << 1.0 / fps << ",\n"
            << "  \"warmup_requested_s\": " << g_warmupSec << ",\n"
            << "  \"warmup_effective_s\": " << g_warmupEffective << ",\n"
            << "  \"warmup_mode\": \"" << JsonEscape(g_warmupMode) << "\",\n"
            << "  \"static_oracle_mode\": \"" << JsonEscape(g_staticOracleMode) << "\"";
        if (g_a3Instrumentation) {
            config << ",\n  \"a3_instrumentation\": true,\n"
                   << "  \"flow_fraction\": " << g_flowFraction << ",\n"
                     << "  \"flow_seed\": " << g_flowSeed << ",\n"
                     << "  \"a3b_forward_log\": " << (g_a3bForwardLogEnabled ? "true" : "false") << "\n";
        } else {
            config << "\n";
        }
        config << "}\n";
        config.close();

    std::map<std::string, PerfMetrics> metrics;
    std::cout << "\n=== Trace replay (matrix-based connectivity) ===\n";
    for (const auto& proto : protocols) {
        std::cout << "  [" << proto << "] ... ";
        std::cout.flush();

        metrics[proto] = runTraceReplay(proto, flows, dataRate, packetSize,
                                         defaultLossDb, txPowerDbm);
        if (g_a3Instrumentation) {
            const double stopTime = g_frames.empty() ? 0.0 : g_frames.back().time;
            AppendA3RunOutputs(proto, stopTime);
        }

        std::cout << "wall=" << std::fixed << std::setprecision(3)
                  << metrics[proto].wall_time_s << "s  cpu="
                  << metrics[proto].cpu_time_s  << "s  "
                  << "tx_cb=" << metrics[proto].ip_tx_cb_calls
                  << "  rx_cb=" << metrics[proto].ip_rx_cb_calls
                  << "  apply_frames=" << metrics[proto].frame_apply_calls
                  << "  pdr=" << metrics[proto].pdr << "\n";
    }

    std::ofstream ofs(resultsFile);
    ofs << "scenario,protocol,"
           "wall_time_s,cpu_time_s,"
           "ip_tx_cb_calls,ip_rx_cb_calls,"
           "frame_apply_calls,"
           "routing_tx,routing_rx,"
           "pdr,goodput_mbps,eed_mean_s,"
           "app_tx_pkts,app_rx_pkts,"
           "ip_drop_no_route,ip_drop_route_err,"
           "phy_tx_drop,phy_rx_drop,"
           "routing_efficiency,control_packets,control_bytes,"
           "control_packets_per_delivered,control_bytes_per_delivered,"
           "oracle_uptime_ratio,oracle_mean_up_run_s,oracle_median_up_run_s,"
           "oracle_p90_up_run_s,oracle_up_runs_s,oracle_transition_count,"
           "oracle_path_identity_retention,oracle_has_alternative_paths,"
           "oracle_outage_durations_s,reestablishment_times_s,reestablishment_outage_durations_s";
    const std::vector<std::string> controlKinds = {
        "olsr_hello", "olsr_tc", "olsr_mid", "olsr_hna", "olsr_other",
        "aodv_hello", "aodv_rreq", "aodv_rrep", "aodv_rerr", "aodv_rrep_ack", "aodv_other",
        "dsdv_update", "dsdv_other", "static_other"
    };
    for (const auto& kind : controlKinds)
        ofs << "," << kind << "_packets," << kind << "_bytes";
    if (g_emitControlUnparsedColumns)
        ofs << ",control_unparsed_packets,control_unparsed_bytes";
    ofs << "\n";
    for (const auto& proto : protocols) {
        const PerfMetrics& m = metrics[proto];
        ofs << "trace," << proto << ","
            << std::fixed << std::setprecision(6)
            << m.wall_time_s << "," << m.cpu_time_s << ","
            << m.ip_tx_cb_calls << "," << m.ip_rx_cb_calls << ","
            << m.frame_apply_calls << ","
            << m.routing_tx << "," << m.routing_rx << ","
            << m.pdr << "," << m.goodput_mbps << "," << m.eed_mean_s << ","
            << m.app_tx_pkts << "," << m.app_rx_pkts << ","
            << m.ip_drop_no_route << "," << m.ip_drop_route_err << ","
            << m.phy_tx_drop << "," << m.phy_rx_drop << ","
            << m.routing_efficiency << "," << m.control_packets << "," << m.control_bytes << ","
            << (m.app_rx_pkts ? static_cast<double>(m.control_packets) / m.app_rx_pkts
                              : std::numeric_limits<double>::quiet_NaN()) << ","
            << (m.app_rx_pkts ? static_cast<double>(m.control_bytes) / m.app_rx_pkts
                              : std::numeric_limits<double>::quiet_NaN()) << ","
            << g_oracle.uptimeRatio << "," << g_oracle.meanUpRunSeconds << ","
            << g_oracle.medianUpRunSeconds << "," << g_oracle.p90UpRunSeconds << ","
            << FormatList(g_oracle.upRuns) << "," << g_oracle.transitions << ","
            << g_oracle.pathRetention << "," << (g_oracle.hasAlternativePaths ? 1 : 0) << ","
            << FormatList(g_oracle.outages) << ","
            << FormatList(m.reestablishment_times) << ","
            << FormatList(m.recovered_outage_durations);
        for (const auto& kind : controlKinds) {
            const auto count = m.control_message_counts.find(kind);
            const auto bytes = m.control_message_bytes.find(kind);
            ofs << "," << (count == m.control_message_counts.end() ? 0 : count->second)
                << "," << (bytes == m.control_message_bytes.end() ? 0 : bytes->second);
        }
        if (g_emitControlUnparsedColumns) {
            const auto count = m.control_message_counts.find("olsr_unparsed");
            const auto bytes = m.control_message_bytes.find("olsr_unparsed");
            ofs << "," << (count == m.control_message_counts.end() ? 0 : count->second)
                << "," << (bytes == m.control_message_bytes.end() ? 0 : bytes->second);
        }
        ofs << "\n";
    }
    ofs.close();

    std::cout << "\nReplay results written to: " << resultsFile << "\n";
    return 0;
}