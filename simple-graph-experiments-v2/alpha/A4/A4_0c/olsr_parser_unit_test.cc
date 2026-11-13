#include "ns3/olsr-header.h"
#include "ns3/packet.h"
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <csignal>
#include <array>
#include <cstdint>
#include <iostream>
#include <vector>

using ns3::Create;
using ns3::Ptr;
using ns3::Packet;

static std::vector<uint8_t> aggregate(uint8_t firstType)
{
    // OLSR PacketHeader(len=28, seq=7), then two 12-byte message headers.
    // MID has an empty address list; TC has an empty neighbor list.
    return {0,28,0,7,
            firstType,0,0,12,10,0,0,1,1,0,0,1,
            2,0,0,12,10,0,0,2,1,0,0,2};
}

static bool oldParserAborts(const std::vector<uint8_t>& bytes)
{
    const pid_t pid=fork();
    if(pid==0)
    {
        auto p=Create<Packet>(bytes.data(),static_cast<uint32_t>(bytes.size()));
        ns3::olsr::PacketHeader packetHeader;
        ns3::olsr::MessageHeader messageHeader;
        p->RemoveHeader(packetHeader);
        p->PeekHeader(messageHeader); // exact legacy assertion path
        _exit(0);
    }
    int status=0;
    waitpid(pid,&status,0);
    return WIFSIGNALED(status) && WTERMSIG(status)==SIGABRT;
}

static bool patchedGuardReturnsOther(const std::vector<uint8_t>& bytes)
{
    auto p=Create<Packet>(bytes.data(),static_cast<uint32_t>(bytes.size()));
    ns3::olsr::PacketHeader packetHeader;
    if(p->GetSize()<4 || !p->PeekHeader(packetHeader) ||
       packetHeader.GetPacketLength()<16 || packetHeader.GetPacketLength()>p->GetSize()) return true;
    p->RemoveHeader(packetHeader);
    uint8_t type=0;
    if(p->GetSize()==0 || p->CopyData(&type,1)!=1 || type<1 || type>4) return true;
    return false;
}

int main()
{
    const auto valid=aggregate(3); // valid MID followed by valid TC
    const auto malformed=aggregate(0); // invalid first type, valid second message
    const bool validOk=!oldParserAborts(valid);
    const bool legacyReproduced=oldParserAborts(malformed);
    const bool patchedSafe=patchedGuardReturnsOther(malformed);
    std::cout << "valid_two_message_aggregate_no_assert=" << validOk << '\n'
              << "malformed_aggregate_legacy_SIGABRT=" << legacyReproduced << '\n'
              << "patched_guard_rejects_without_deserialize=" << patchedSafe << '\n';
    return (validOk && legacyReproduced && patchedSafe) ? 0 : 1;
}
