#include <cassert>
#include <cstdint>
#include <iostream>
#include <map>
#include <string>
#include <vector>

// Mirrors the pure byte/port guard used by ControlMessageKind in graph-run.patched.cc.
// The real A4 regression and canary then exercise the integrated copied/applied source.
static std::string classify(uint16_t sourcePort, uint16_t destinationPort,
                            const std::vector<uint8_t>& bytes)
{
    if (sourcePort != 698 || destinationPort != 698) return "olsr_other";
    if (bytes.size() < 16) return "olsr_unparsed";
    auto readU16 = [&bytes](size_t offset) -> uint16_t {
        if (offset + 1 >= bytes.size()) return 0;
        return static_cast<uint16_t>((static_cast<uint16_t>(bytes[offset]) << 8) |
                                     static_cast<uint16_t>(bytes[offset + 1]));
    };
    const uint32_t packetLength = readU16(0);
    if (packetLength != bytes.size() || packetLength < 16) return "olsr_unparsed";
    uint32_t offset = 4;
    uint8_t firstType = 0;
    while (offset < packetLength) {
        if (packetLength - offset < 12) return "olsr_unparsed";
        const uint8_t type = bytes[offset];
        const uint32_t messageLength = readU16(offset + 2);
        if (type < 1 || type > 4 || messageLength < 12 ||
            messageLength > packetLength - offset) return "olsr_unparsed";
        if (offset == 4) firstType = type;
        offset += messageLength;
    }
    if (offset != packetLength) return "olsr_unparsed";
    switch (firstType) {
    case 1: return "olsr_hello";
    case 2: return "olsr_tc";
    case 3: return "olsr_mid";
    case 4: return "olsr_hna";
    default: return "olsr_unparsed";
    }
}

static std::vector<uint8_t> aggregate(uint8_t firstType)
{
    return {0,28,0,7,
            firstType,0,0,12,10,0,0,1,1,0,0,1,
            2,0,0,12,10,0,0,2,1,0,0,2};
}

int main()
{
    const auto valid=aggregate(3);
    const auto malformed=aggregate(0);
    auto truncated=valid;
    truncated.resize(20); // declared packet length remains 28
    const std::vector<std::pair<uint16_t,std::vector<uint8_t>>> fixtures={
        {698,valid},{698,malformed},{698,truncated},{9999,malformed}};
    std::map<std::string,uint64_t> packetsByClass,bytesByClass;
    uint64_t allPackets=0,allBytes=0;
    for (const auto& [destinationPort,bytes] : fixtures) {
        const std::string kind=classify(destinationPort==9999?49152:698,destinationPort,bytes);
        ++packetsByClass[kind];
        bytesByClass[kind]+=bytes.size();
        ++allPackets;
        allBytes+=bytes.size();
    }
    assert(packetsByClass["olsr_mid"]==1);
    assert(packetsByClass["olsr_unparsed"]==2);
    assert(packetsByClass["olsr_other"]==1);
    assert(packetsByClass["olsr_mid"]+packetsByClass["olsr_unparsed"]+
           packetsByClass["olsr_other"]==allPackets);
    assert(bytesByClass["olsr_mid"]+bytesByClass["olsr_unparsed"]+
           bytesByClass["olsr_other"]==allBytes);
    assert(bytesByClass["olsr_unparsed"]==malformed.size()+truncated.size());
    std::cout << "valid_aggregate=olsr_mid\n"
              << "malformed_first_type=olsr_unparsed\n"
              << "truncated_packet=olsr_unparsed\n"
              << "non_OLSR_UDP=olsr_other\n"
              << "unparsed_packet_byte_sums=pass\n";
}
