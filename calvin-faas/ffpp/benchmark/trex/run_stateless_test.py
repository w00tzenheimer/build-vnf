#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Run simple Trex stateless tests using Python automation API.
"""

import time

import stf_path
from trex.stl.api import (
    IP,
    UDP,
    Ether,
    STLClient,
    STLError,
    STLFlowLatencyStats,
    STLPktBuilder,
    STLStream,
    STLTXSingleBurst,
)

PG_ID = 17
TOTAL_PKTS = 50
PPS = 10  # Inter Packet Gap = (1 / PPS)
MONITOR_DUR = 8  # Duration to monitor the flow stats in seconds.


def rx_interation(c, tx_port, rx_port, total_pkts, pkt_len):
    c.clear_stats()
    c.start(ports=[tx_port])
    pgids = c.get_active_pgids()
    print("Currently used pgids: {0}".format(pgids))

    for _ in range(MONITOR_DUR):
        time.sleep(1)
        # Return flow stats of the given list of pgids.
        stats = c.get_pgid_stats(pgids["latency"])
        flow_stats = stats["flow_stats"].get(PG_ID)
        tx_pps = flow_stats["tx_pps"][tx_port]
        rx_pps = flow_stats["rx_pps"][rx_port]
        tx_pkts = flow_stats["tx_pkts"][tx_port]
        rx_pkts = flow_stats["rx_pkts"][rx_port]
        print(
            f"{time.time()}: tx_pkts: {tx_pkts}, tx_pps: {tx_pps}, rx_pkts:{rx_pkts} ,rx_pps: {rx_pps}"
        )
        print(flow_stats["tx_pkts"])
        print(flow_stats["rx_pkts"])
    # Block until the TX traffic finishes.
    c.wait_on_traffic(ports=[tx_port])

    stats = c.get_pgid_stats(pgids["latency"])
    flow_stats = stats["flow_stats"].get(PG_ID)
    lat_stats = stats["latency"].get(PG_ID)
    if not lat_stats:
        print("No latency stats available!")
        return False

    print("\n--- Latency stats of the test stream:")
    drops = lat_stats["err_cntrs"]["dropped"]
    ooo = lat_stats["err_cntrs"]["out_of_order"]
    print(f"Dropped: {drops}, Out-of-Order: {ooo}")
    lat = lat_stats["latency"]
    avg = lat["average"]
    jitter = lat["jitter"]
    hist = lat["histogram"]
    total_max = lat["total_max"]
    print(
        f"The average latency: {avg} usecs, total max: {total_max} usecs, jitter: {jitter} usecs"
    )
    print(hist)

    return True


if __name__ == "__main__":
    # Create a client for stateless tests.
    clt = STLClient()
    passed = True

    try:
        udp_payload = "A" * 50
        pkt = STLPktBuilder(
            pkt=Ether()
            / IP(src="192.168.17.1", dst="192.168.17.2")
            / UDP(dport=8888, sport=9999, chksum=0)
            / udp_payload
        )
        st = STLStream(
            name="udp_single_burst",
            packet=pkt,
            # Packet group id
            flow_stats=STLFlowLatencyStats(pg_id=PG_ID),
            mode=STLTXSingleBurst(total_pkts=TOTAL_PKTS, pps=PPS),
        )

        clt.connect()
        all_ports = clt.get_all_ports()
        print("All ports: {}".format(",".join(map(str, all_ports))))
        tx_port, rx_port = all_ports
        print(f"TX port: {tx_port}, RX port: {rx_port}")
        tx_port_attr = clt.get_port_attr(tx_port)
        rx_port_attr = clt.get_port_attr(rx_port)
        assert tx_port_attr["src_ipv4"] == "192.168.17.1"
        assert rx_port_attr["src_ipv4"] == "192.168.18.1"
        clt.reset(ports=all_ports)
        clt.add_streams([st], ports=[tx_port])
        print(f"Inject {TOTAL_PKTS} packets on port {all_ports[0]}")

        ret = rx_interation(clt, tx_port, rx_port, TOTAL_PKTS, pkt.get_pkt_len())
        if not ret:
            passed = False

    except STLError as e:
        passed = False
        print(e)

    finally:
        clt.disconnect()

    if passed:
        print("Latency test is passed!")
    else:
        print("Latency test failed!")
