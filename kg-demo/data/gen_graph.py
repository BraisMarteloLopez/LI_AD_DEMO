"""
Synthetic Knowledge Graph generator for the LI_AD KG demo.

Domain: state-sponsored cyberwarfare / threat intelligence.

Outputs:
  - graph.json      : nodes + edges + community assignment (for the JS render)
  - COMMUNITIES.md  : human-readable summary of the 8 communities

Deterministic: seed is fixed so the graph is reproducible between runs.
Louvain is executed as a sanity check; the JSON's `community` field uses the
hand-curated assignment (which is what we want to render), and the Louvain
result is reported in COMMUNITIES.md so we can eyeball divergence.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import networkx as nx
from networkx.algorithms.community import louvain_communities, modularity

SEED = 42
random.seed(SEED)

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1. Communities (hand-curated taxonomy)
# ---------------------------------------------------------------------------
# Each node is a (id, label, type, description).
# Types: threat_actor, agency, malware, vulnerability, incident, target_sector,
#        vendor, alliance.

COMMUNITIES: dict[str, dict] = {
    "russia": {
        "label": "Russia-aligned",
        "nodes": [
            ("apt28", "APT28 (Fancy Bear)", "threat_actor",
             "GRU Unit 26165 cyber-espionage group; political and military targets in NATO states."),
            ("apt29", "APT29 (Cozy Bear)", "threat_actor",
             "SVR-linked APT specialising in long-dwell intrusions of government and think-tanks."),
            ("sandworm", "Sandworm (Unit 74455)", "threat_actor",
             "GRU destructive operations unit behind power-grid and wiper campaigns."),
            ("turla", "Turla (Snake)", "threat_actor",
             "FSB-aligned actor known for satellite-based C2 and long-running espionage."),
            ("gamaredon", "Gamaredon", "threat_actor",
             "FSB-attributed Ukraine-focused operator with high-volume, low-stealth ops."),
            ("gru", "GRU (military intel)", "agency",
             "Russian military intelligence directorate, parent of Units 26165 and 74455."),
            ("svr", "SVR", "agency",
             "Russian Foreign Intelligence Service; sponsor of APT29-class operations."),
            ("fsb", "FSB", "agency",
             "Russian Federal Security Service; sponsor of Turla and Gamaredon."),
            ("notpetya", "NotPetya", "malware",
             "Destructive wiper disguised as ransomware; spread via MEDoc update channel in 2017."),
            ("industroyer", "Industroyer / CrashOverride", "malware",
             "First malware framework purpose-built to attack industrial control systems."),
            ("blackenergy", "BlackEnergy", "malware",
             "Modular toolkit used in early Ukraine grid intrusions; precursor to Industroyer."),
            ("caddywiper", "CaddyWiper", "malware",
             "Disk wiper deployed against Ukrainian targets during the 2022 invasion."),
        ],
    },
    "china": {
        "label": "China-aligned",
        "nodes": [
            ("apt1", "APT1 (Comment Crew)", "threat_actor",
             "PLA Unit 61398; long-running IP theft operations exposed by Mandiant in 2013."),
            ("apt10", "APT10 (Stone Panda)", "threat_actor",
             "MSS-linked group focused on managed service providers (Operation Cloud Hopper)."),
            ("apt41", "APT41 (Double Dragon)", "threat_actor",
             "Dual-use MSS contractor blending state espionage with financially motivated ops."),
            ("volt_typhoon", "Volt Typhoon", "threat_actor",
             "Living-off-the-land intrusions of US critical infrastructure for pre-positioning."),
            ("salt_typhoon", "Salt Typhoon", "threat_actor",
             "Telecommunications-focused PRC actor exposed in late 2024 US telco compromises."),
            ("hafnium", "Hafnium", "threat_actor",
             "MSS-linked actor behind the 2021 ProxyLogon mass-exploitation of Exchange servers."),
            ("mustang_panda", "Mustang Panda", "threat_actor",
             "PRC actor targeting NGOs and diplomatic missions across South-East Asia and Europe."),
            ("mss", "MSS (Ministry of State Security)", "agency",
             "China's civilian intelligence service; primary sponsor of contemporary PRC APTs."),
            ("pla_61398", "PLA Unit 61398", "agency",
             "Shanghai-based PLA signals intelligence unit; APT1's home unit."),
            ("plugx", "PlugX (Korplug)", "malware",
             "Modular RAT shared across multiple PRC clusters since 2012."),
            ("shadowpad", "ShadowPad", "malware",
             "Successor to PlugX; sold across MSS-linked clusters as a turnkey backdoor."),
            ("proxylogon", "ProxyLogon (CVE-2021-26855)", "vulnerability",
             "Exchange Server SSRF chain enabling unauthenticated RCE; mass-exploited by Hafnium."),
        ],
    },
    "north_korea": {
        "label": "North Korea-aligned",
        "nodes": [
            ("lazarus", "Lazarus Group", "threat_actor",
             "DPRK umbrella cluster behind destructive, espionage and financial operations."),
            ("kimsuky", "Kimsuky", "threat_actor",
             "RGB-aligned espionage cluster focused on policy and nuclear research targets."),
            ("bluenoroff", "BlueNoroff", "threat_actor",
             "Financial heist sub-cluster of Lazarus targeting banks and crypto firms."),
            ("andariel", "Andariel", "threat_actor",
             "DPRK actor blending defence-sector espionage with ransomware-for-revenue."),
            ("rgb_121", "RGB Bureau 121", "agency",
             "Reconnaissance General Bureau cyber arm; parent of the DPRK APT ecosystem."),
            ("wannacry", "WannaCry", "malware",
             "Worming ransomware leveraging EternalBlue; attributed to Lazarus in May 2017."),
            ("applejeus", "AppleJeus", "malware",
             "Trojanised crypto-trading apps used to compromise exchanges and individuals."),
            ("sony_2014", "Sony Pictures hack 2014", "incident",
             "Destructive intrusion in retaliation for 'The Interview'; FBI attributed to DPRK."),
            ("bangladesh_bank", "Bangladesh Bank heist 2016", "incident",
             "SWIFT-network theft of USD 81M from the central bank; linked to BlueNoroff."),
            ("ronin_bridge", "Ronin Bridge heist 2022", "incident",
             "USD 620M theft from the Axie Infinity bridge attributed to Lazarus by FBI."),
        ],
    },
    "iran": {
        "label": "Iran-aligned",
        "nodes": [
            ("apt33", "APT33 (Elfin / Refined Kitten)", "threat_actor",
             "IRGC-linked actor targeting aerospace and energy sectors across the Gulf."),
            ("apt34", "APT34 (OilRig)", "threat_actor",
             "MOIS-attributed cluster focused on the Middle East energy and government sectors."),
            ("apt35", "APT35 (Charming Kitten)", "threat_actor",
             "IRGC-attributed credential-phishing operator targeting journalists and academics."),
            ("muddywater", "MuddyWater", "threat_actor",
             "MOIS subcontractor running broad regional campaigns with off-the-shelf tooling."),
            ("irgc", "IRGC", "agency",
             "Islamic Revolutionary Guard Corps; sponsor of APT33 and APT35."),
            ("mois", "MOIS", "agency",
             "Iran's Ministry of Intelligence and Security; sponsor of APT34 and MuddyWater."),
            ("shamoon", "Shamoon / DistTrack", "malware",
             "Disk wiper deployed against Saudi Aramco in 2012 and reused through 2018."),
            ("aramco_2012", "Saudi Aramco attack 2012", "incident",
             "Shamoon wiped ~35,000 workstations at the world's largest oil producer."),
            ("albania_2022", "Albania attack 2022", "incident",
             "MuddyWater wiper campaign that severed diplomatic relations with Tehran."),
        ],
    },
    "western": {
        "label": "Western intel (Five Eyes + allies)",
        "nodes": [
            ("nsa_tao", "NSA / Tailored Access Ops", "agency",
             "US signals-intel offensive arm; developer of bespoke implants and zero-days."),
            ("cia", "CIA", "agency",
             "US foreign intelligence service; covert cyber capability exposed via Vault 7."),
            ("gchq", "GCHQ", "agency",
             "UK signals intelligence agency and Five Eyes partner."),
            ("equation_group", "Equation Group", "threat_actor",
             "Cluster widely linked to the NSA; high-end implants disclosed by Kaspersky in 2015."),
            ("unit_8200", "IDF Unit 8200", "agency",
             "Israeli signals-intel unit; co-developer of Stuxnet under Operation Olympic Games."),
            ("stuxnet", "Stuxnet", "malware",
             "Worm that sabotaged Natanz centrifuges; opened the era of cyber-physical warfare."),
            ("eternalblue", "EternalBlue (CVE-2017-0144)", "vulnerability",
             "SMBv1 RCE developed by NSA TAO; leaked by Shadow Brokers in April 2017."),
            ("vault_7", "Vault 7 leak 2017", "incident",
             "WikiLeaks disclosure of CIA cyber-capabilities and implant frameworks."),
            ("shadow_brokers", "Shadow Brokers leak 2016", "incident",
             "Unknown group released NSA TAO tooling, including EternalBlue and DoublePulsar."),
            ("five_eyes", "Five Eyes alliance", "alliance",
             "AUS-CAN-NZ-UK-US signals-intelligence sharing arrangement."),
        ],
    },
    "critical_infra": {
        "label": "Critical infrastructure incidents",
        "nodes": [
            ("colonial_pipeline", "Colonial Pipeline 2021", "incident",
             "DarkSide ransomware halted US East Coast fuel distribution for six days."),
            ("ukraine_grid_2015", "Ukraine power grid 2015", "incident",
             "First confirmed blackout caused by a cyber-attack; ~225,000 customers affected."),
            ("ukraine_grid_2016", "Ukraine power grid 2016", "incident",
             "Industroyer-driven outage in Kyiv; first ICS-tailored framework in the wild."),
            ("triton", "Triton / Trisis", "malware",
             "ICS malware targeting Schneider Triconex safety controllers in a Saudi facility."),
            ("oldsmar_water", "Oldsmar water plant 2021", "incident",
             "Remote intruder briefly altered sodium hydroxide setpoints at a Florida utility."),
            ("darkside", "DarkSide RaaS", "threat_actor",
             "Russian-speaking ransomware affiliate program responsible for Colonial Pipeline."),
            ("energy_sector", "Energy sector targets", "target_sector",
             "Power generation, transmission and oil-and-gas operators."),
            ("water_utilities", "Water and wastewater utilities", "target_sector",
             "Municipal and regional water systems; frequently low-maturity OT environments."),
            ("ics_scada", "ICS / SCADA systems", "target_sector",
             "Industrial control systems and the protocols they speak (Modbus, DNP3, S7)."),
        ],
    },
    "supply_chain": {
        "label": "Supply chain campaigns",
        "nodes": [
            ("solarwinds", "SolarWinds / SUNBURST 2020", "incident",
             "Trojanised Orion updates gave SVR access to ~18,000 organisations worldwide."),
            ("sunburst_malware", "SUNBURST backdoor", "malware",
             "Stealthy .NET implant injected into SolarWinds.Orion.Core.BusinessLayer.dll."),
            ("kaseya", "Kaseya VSA 2021", "incident",
             "REvil exploitation of VSA pushed ransomware to hundreds of downstream MSP clients."),
            ("3cx", "3CX supply chain 2023", "incident",
             "Trojanised desktop client distributed via signed installers; DPRK attribution."),
            ("moveit", "MOVEit Transfer 2023", "incident",
             "Cl0p mass-exploitation of CVE-2023-34362 against thousands of file-transfer servers."),
            ("ccleaner_2017", "CCleaner 2017", "incident",
             "Trojanised CCleaner update reached ~2.27M users; second-stage filter selected APT10 targets."),
            ("xz_utils", "XZ Utils backdoor 2024", "incident",
             "Multi-year social-engineering of an OSS maintainer yielded a near-miss sshd backdoor."),
            ("cl0p", "Cl0p ransomware gang", "threat_actor",
             "Russian-speaking extortion group specialising in zero-day mass exploitation."),
        ],
    },
    "spyware": {
        "label": "Commercial spyware / mercenary",
        "nodes": [
            ("nso_group", "NSO Group", "vendor",
             "Israeli spyware vendor whose Pegasus implant has been deployed in 45+ countries."),
            ("pegasus", "Pegasus", "malware",
             "Zero-click iOS/Android implant marketed for 'lawful intercept'."),
            ("candiru", "Candiru", "vendor",
             "Israeli vendor sanctioned by the US in 2021 alongside NSO Group."),
            ("hacking_team", "Hacking Team", "vendor",
             "Italian vendor whose source code was leaked in 2015, exposing global clientele."),
            ("cytrox", "Cytrox", "vendor",
             "North Macedonian vendor and developer of the Predator implant."),
            ("predator_spyware", "Predator spyware", "malware",
             "Mobile implant marketed by Cytrox/Intellexa; tracked by Citizen Lab and Google TAG."),
            ("finfisher", "FinFisher / FinSpy", "malware",
             "Long-running commercial implant family marketed to law-enforcement agencies."),
            ("journalist_targets", "Journalists and dissidents", "target_sector",
             "Recurring target population for commercial spyware operators worldwide."),
        ],
    },
}


# ---------------------------------------------------------------------------
# 2. Intra-community edges (domain-logical)
# ---------------------------------------------------------------------------
# Each tuple is (source_id, target_id, relation_type).

INTRA_EDGES: dict[str, list[tuple[str, str, str]]] = {
    "russia": [
        ("apt28", "gru", "operated_by"),
        ("sandworm", "gru", "operated_by"),
        ("apt29", "svr", "operated_by"),
        ("turla", "fsb", "operated_by"),
        ("gamaredon", "fsb", "operated_by"),
        ("sandworm", "notpetya", "deployed"),
        ("sandworm", "industroyer", "deployed"),
        ("sandworm", "blackenergy", "deployed"),
        ("sandworm", "caddywiper", "deployed"),
        ("apt28", "apt29", "shares_targets"),
        ("blackenergy", "industroyer", "evolved_into"),
        ("notpetya", "blackenergy", "shares_code"),
        ("apt28", "turla", "shares_infra"),
        ("apt29", "turla", "shares_targets"),
    ],
    "china": [
        ("apt1", "pla_61398", "operated_by"),
        ("apt10", "mss", "operated_by"),
        ("apt41", "mss", "operated_by"),
        ("volt_typhoon", "mss", "operated_by"),
        ("salt_typhoon", "mss", "operated_by"),
        ("hafnium", "mss", "operated_by"),
        ("mustang_panda", "mss", "operated_by"),
        ("apt10", "plugx", "uses"),
        ("apt41", "shadowpad", "uses"),
        ("mustang_panda", "plugx", "uses"),
        ("hafnium", "proxylogon", "exploits"),
        ("plugx", "shadowpad", "evolved_into"),
        ("apt41", "apt10", "shares_tooling"),
        ("volt_typhoon", "salt_typhoon", "shares_targets"),
    ],
    "north_korea": [
        ("lazarus", "rgb_121", "operated_by"),
        ("bluenoroff", "rgb_121", "operated_by"),
        ("andariel", "rgb_121", "operated_by"),
        ("kimsuky", "rgb_121", "operated_by"),
        ("bluenoroff", "lazarus", "subgroup_of"),
        ("andariel", "lazarus", "subgroup_of"),
        ("lazarus", "wannacry", "deployed"),
        ("lazarus", "applejeus", "deployed"),
        ("bluenoroff", "applejeus", "deployed"),
        ("lazarus", "sony_2014", "conducted"),
        ("bluenoroff", "bangladesh_bank", "conducted"),
        ("lazarus", "ronin_bridge", "conducted"),
        ("kimsuky", "lazarus", "shares_infra"),
    ],
    "iran": [
        ("apt33", "irgc", "operated_by"),
        ("apt35", "irgc", "operated_by"),
        ("apt34", "mois", "operated_by"),
        ("muddywater", "mois", "operated_by"),
        ("apt33", "shamoon", "deployed"),
        ("apt33", "aramco_2012", "conducted"),
        ("muddywater", "albania_2022", "conducted"),
        ("apt34", "apt35", "shares_infra"),
        ("apt33", "muddywater", "shares_targets"),
        ("shamoon", "aramco_2012", "deployed_in"),
    ],
    "western": [
        ("equation_group", "nsa_tao", "attributed_to"),
        ("nsa_tao", "stuxnet", "co_developed"),
        ("unit_8200", "stuxnet", "co_developed"),
        ("nsa_tao", "eternalblue", "developed"),
        ("shadow_brokers", "eternalblue", "leaked"),
        ("shadow_brokers", "nsa_tao", "exfiltrated_from"),
        ("vault_7", "cia", "exfiltrated_from"),
        ("nsa_tao", "five_eyes", "member_of"),
        ("gchq", "five_eyes", "member_of"),
        ("nsa_tao", "gchq", "shares_intel"),
        ("equation_group", "stuxnet", "linked_to"),
        ("cia", "nsa_tao", "shares_intel"),
    ],
    "critical_infra": [
        ("darkside", "colonial_pipeline", "conducted"),
        ("colonial_pipeline", "energy_sector", "targeted"),
        ("ukraine_grid_2015", "energy_sector", "targeted"),
        ("ukraine_grid_2016", "energy_sector", "targeted"),
        ("triton", "ics_scada", "targets"),
        ("oldsmar_water", "water_utilities", "targeted"),
        ("ukraine_grid_2015", "ics_scada", "targeted"),
        ("ukraine_grid_2016", "ics_scada", "targeted"),
        ("triton", "energy_sector", "targets"),
    ],
    "supply_chain": [
        ("solarwinds", "sunburst_malware", "delivered"),
        ("cl0p", "moveit", "conducted"),
        ("cl0p", "kaseya", "linked_to"),
        ("solarwinds", "kaseya", "preceded"),
        ("3cx", "xz_utils", "shares_pattern"),
        ("ccleaner_2017", "solarwinds", "preceded"),
        ("moveit", "kaseya", "shares_pattern"),
    ],
    "spyware": [
        ("nso_group", "pegasus", "vendor_of"),
        ("cytrox", "predator_spyware", "vendor_of"),
        ("hacking_team", "finfisher", "shares_market"),
        ("candiru", "nso_group", "shares_market"),
        ("pegasus", "predator_spyware", "shares_capability"),
        ("nso_group", "journalist_targets", "implicated_in_targeting"),
        ("cytrox", "journalist_targets", "implicated_in_targeting"),
        ("finfisher", "journalist_targets", "deployed_against"),
        ("hacking_team", "candiru", "shares_market"),
    ],
}


# ---------------------------------------------------------------------------
# 3. Cross-community edges (story-rich bridges, all geopolitically plausible)
# ---------------------------------------------------------------------------

INTER_EDGES: list[tuple[str, str, str]] = [
    # Russia ↔ Supply chain (SVR was behind SolarWinds)
    ("apt29", "solarwinds", "conducted"),
    ("apt29", "sunburst_malware", "deployed"),
    # Russia ↔ Critical infra (Sandworm did the Ukraine grid + NotPetya)
    ("sandworm", "ukraine_grid_2015", "conducted"),
    ("sandworm", "ukraine_grid_2016", "conducted"),
    ("industroyer", "ukraine_grid_2016", "deployed_in"),
    ("blackenergy", "ukraine_grid_2015", "deployed_in"),
    # Russia ↔ Critical infra (DarkSide is Russian-speaking)
    ("darkside", "fsb", "tolerated_by"),
    # Russia ↔ Western (Shadow Brokers leak benefited Russia)
    ("shadow_brokers", "gru", "suspected_link"),
    # NotPetya ↔ Supply chain
    ("notpetya", "solarwinds", "shares_pattern"),
    # China ↔ Supply chain (CCleaner was APT10)
    ("apt10", "ccleaner_2017", "conducted"),
    # NK ↔ Supply chain (3CX was DPRK)
    ("lazarus", "3cx", "conducted"),
    # NK ↔ Western (WannaCry used EternalBlue)
    ("wannacry", "eternalblue", "exploits"),
    # Western ↔ Russia (Stuxnet was Western, used in Iran but also Russia tracked it)
    ("apt28", "shadow_brokers", "benefited_from"),
    # Western ↔ Iran (Stuxnet hit Iran)
    ("stuxnet", "irgc", "targeted"),
    # Iran ↔ Critical infra (Shamoon at Aramco is also crit-infra adjacent)
    ("shamoon", "energy_sector", "targeted"),
    ("aramco_2012", "energy_sector", "targeted"),
    # Cl0p ↔ Russia (Russian-speaking gang)
    ("cl0p", "fsb", "tolerated_by"),
    # Spyware ↔ Western (Pegasus deployed by some Western LEAs)
    ("pegasus", "gchq", "procured_by"),
    # Spyware ↔ Iran (Iran allegedly uses commercial spyware)
    ("predator_spyware", "mois", "procured_by"),
    # Spyware ↔ China (some PRC use of commercial implants reported)
    ("finfisher", "mss", "procured_by"),
    # Supply chain ↔ China (ProxyLogon was supply-chain-adjacent)
    ("proxylogon", "moveit", "shares_pattern"),
    # Critical infra ↔ Western (Stuxnet was the original ICS attack)
    ("stuxnet", "ics_scada", "targets"),
    # Lazarus ↔ Crit infra (Lazarus has targeted defense)
    ("lazarus", "energy_sector", "targeted"),
    # APT41 ↔ Spyware (financial dual-use overlap)
    ("apt41", "journalist_targets", "targeted"),
    # Volt Typhoon ↔ Crit infra
    ("volt_typhoon", "energy_sector", "targeted"),
    ("volt_typhoon", "water_utilities", "targeted"),
    ("salt_typhoon", "energy_sector", "targeted"),
    # APT33 ↔ Crit infra
    ("apt33", "energy_sector", "targeted"),
    # APT28 ↔ Western (GRU targeted Five Eyes orgs)
    ("apt28", "five_eyes", "targeted"),
    ("apt29", "five_eyes", "targeted"),
    # Triton attribution overlap with Russia (TsNIIKhM linked)
    ("triton", "gru", "linked_to"),
    # SolarWinds ↔ Western (CISA/NSA were the discoverers; targeted)
    ("solarwinds", "five_eyes", "targeted"),
]


# ---------------------------------------------------------------------------
# 4. Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> tuple[nx.Graph, dict[str, str], dict[str, dict]]:
    """Returns (G, community_of_node, node_meta)."""
    G = nx.Graph()
    community_of_node: dict[str, str] = {}
    node_meta: dict[str, dict] = {}

    for community_id, payload in COMMUNITIES.items():
        for nid, label, ntype, description in payload["nodes"]:
            G.add_node(nid)
            community_of_node[nid] = community_id
            node_meta[nid] = {
                "id": nid,
                "label": label,
                "type": ntype,
                "community": community_id,
                "community_label": payload["label"],
                "description": description,
            }

    def add_edge(u: str, v: str, rel: str) -> None:
        if u not in node_meta or v not in node_meta:
            raise KeyError(f"edge references unknown node: {u} -> {v}")
        if G.has_edge(u, v):
            existing = G[u][v]["type"]
            if existing != rel:
                G[u][v]["type"] = f"{existing}, {rel}"
            return
        G.add_edge(u, v, type=rel)

    for community_id, edges in INTRA_EDGES.items():
        for u, v, rel in edges:
            add_edge(u, v, rel)

    for u, v, rel in INTER_EDGES:
        add_edge(u, v, rel)

    return G, community_of_node, node_meta


# ---------------------------------------------------------------------------
# 5. Louvain sanity check + serialise
# ---------------------------------------------------------------------------

def run_louvain(G: nx.Graph) -> list[set[str]]:
    return louvain_communities(G, seed=SEED)


def summarise_louvain(
    G: nx.Graph,
    louvain_groups: list[set[str]],
    intended: dict[str, str],
) -> dict:
    intended_to_louvain: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    louvain_index: dict[str, int] = {}
    for i, group in enumerate(louvain_groups):
        for n in group:
            louvain_index[n] = i

    for n, intended_id in intended.items():
        intended_to_louvain[intended_id][louvain_index[n]] += 1

    mod = modularity(G, louvain_groups)
    return {
        "n_louvain_groups": len(louvain_groups),
        "modularity": mod,
        "intended_to_louvain": {
            k: dict(v) for k, v in intended_to_louvain.items()
        },
        "louvain_index": louvain_index,
    }


def to_json_payload(
    G: nx.Graph, node_meta: dict[str, dict]
) -> dict:
    degrees = dict(G.degree())
    nodes_out = []
    for nid, meta in node_meta.items():
        nodes_out.append({
            **meta,
            "degree": degrees[nid],
        })
    edges_out = [
        {"source": u, "target": v, "type": data.get("type", "related")}
        for u, v, data in G.edges(data=True)
    ]
    nodes_out.sort(key=lambda n: (n["community"], -n["degree"], n["id"]))
    edges_out.sort(key=lambda e: (e["source"], e["target"]))
    return {"nodes": nodes_out, "edges": edges_out}


def write_communities_md(
    path: Path,
    intended: dict[str, str],
    node_meta: dict[str, dict],
    louvain_summary: dict,
    n_nodes: int,
    n_edges: int,
) -> None:
    lines: list[str] = []
    lines.append("# Synthetic KG — Communities (cyberwarfare / threat intel)")
    lines.append("")
    lines.append(f"- Nodes: **{n_nodes}**")
    lines.append(f"- Edges: **{n_edges}**")
    lines.append(f"- Intended communities (hand-curated): **{len(COMMUNITIES)}**")
    lines.append(
        f"- Louvain communities (sanity check, seed={SEED}): "
        f"**{louvain_summary['n_louvain_groups']}**, "
        f"modularity={louvain_summary['modularity']:.3f}"
    )
    lines.append("")
    lines.append(
        "The JSON's `community` field uses the hand-curated assignment "
        "below. Louvain is reported only to verify that the graph is "
        "actually separable along the intended cuts."
    )
    lines.append("")

    by_community: dict[str, list[dict]] = defaultdict(list)
    for nid, meta in node_meta.items():
        by_community[meta["community"]].append(meta)

    for community_id, payload in COMMUNITIES.items():
        members = sorted(by_community[community_id], key=lambda m: m["label"])
        lines.append(f"## {payload['label']} (`{community_id}`)")
        lines.append("")
        lines.append("| Label | Type | Description |")
        lines.append("|---|---|---|")
        for m in members:
            lines.append(f"| {m['label']} | `{m['type']}` | {m['description']} |")
        lines.append("")

    lines.append("## Louvain vs intended cross-tab")
    lines.append("")
    lines.append(
        "Rows = intended community. Columns = Louvain group index. "
        "Off-diagonal mass = nodes that Louvain assigned to a different group."
    )
    lines.append("")
    cross = louvain_summary["intended_to_louvain"]
    louvain_cols = sorted({c for row in cross.values() for c in row})
    header = "| intended \\ louvain | " + " | ".join(str(c) for c in louvain_cols) + " | total |"
    sep = "|" + "---|" * (len(louvain_cols) + 2)
    lines.append(header)
    lines.append(sep)
    for community_id in COMMUNITIES:
        row = cross.get(community_id, {})
        cells = [str(row.get(c, 0)) for c in louvain_cols]
        total = sum(row.values())
        lines.append(f"| {community_id} | " + " | ".join(cells) + f" | {total} |")
    lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    G, community_of_node, node_meta = build_graph()
    louvain_groups = run_louvain(G)
    louvain_summary = summarise_louvain(G, louvain_groups, community_of_node)

    payload = to_json_payload(G, node_meta)
    (HERE / "graph.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    write_communities_md(
        HERE / "COMMUNITIES.md",
        intended=community_of_node,
        node_meta=node_meta,
        louvain_summary=louvain_summary,
        n_nodes=G.number_of_nodes(),
        n_edges=G.number_of_edges(),
    )

    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    print(f"intended communities={len(COMMUNITIES)} louvain={louvain_summary['n_louvain_groups']}")
    print(f"modularity={louvain_summary['modularity']:.3f}")
    print("wrote graph.json + COMMUNITIES.md")


if __name__ == "__main__":
    main()
