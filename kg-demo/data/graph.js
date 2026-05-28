window.GRAPH_DATA = {
  "nodes": [
    {
      "id": "mss",
      "label": "MSS (Ministry of State Security)",
      "type": "agency",
      "community": "china",
      "community_label": "China-aligned",
      "description": "China's civilian intelligence service; primary sponsor of contemporary PRC APTs.",
      "degree": 7
    },
    {
      "id": "apt10",
      "label": "APT10 (Stone Panda)",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "MSS-linked group focused on managed service providers (Operation Cloud Hopper).",
      "degree": 4
    },
    {
      "id": "apt41",
      "label": "APT41 (Double Dragon)",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Dual-use MSS contractor blending state espionage with financially motivated ops.",
      "degree": 4
    },
    {
      "id": "volt_typhoon",
      "label": "Volt Typhoon",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Living-off-the-land intrusions of US critical infrastructure for pre-positioning.",
      "degree": 4
    },
    {
      "id": "plugx",
      "label": "PlugX (Korplug)",
      "type": "malware",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Modular RAT shared across multiple PRC clusters since 2012.",
      "degree": 3
    },
    {
      "id": "salt_typhoon",
      "label": "Salt Typhoon",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Telecommunications-focused PRC actor exposed in late 2024 US telco compromises.",
      "degree": 3
    },
    {
      "id": "hafnium",
      "label": "Hafnium",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "MSS-linked actor behind the 2021 ProxyLogon mass-exploitation of Exchange servers.",
      "degree": 2
    },
    {
      "id": "mustang_panda",
      "label": "Mustang Panda",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "PRC actor targeting NGOs and diplomatic missions across South-East Asia and Europe.",
      "degree": 2
    },
    {
      "id": "proxylogon",
      "label": "ProxyLogon (CVE-2021-26855)",
      "type": "vulnerability",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Exchange Server SSRF chain enabling unauthenticated RCE; mass-exploited by Hafnium.",
      "degree": 2
    },
    {
      "id": "shadowpad",
      "label": "ShadowPad",
      "type": "malware",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Successor to PlugX; sold across MSS-linked clusters as a turnkey backdoor.",
      "degree": 2
    },
    {
      "id": "apt1",
      "label": "APT1 (Comment Crew)",
      "type": "threat_actor",
      "community": "china",
      "community_label": "China-aligned",
      "description": "PLA Unit 61398; long-running IP theft operations exposed by Mandiant in 2013.",
      "degree": 1
    },
    {
      "id": "pla_61398",
      "label": "PLA Unit 61398",
      "type": "agency",
      "community": "china",
      "community_label": "China-aligned",
      "description": "Shanghai-based PLA signals intelligence unit; APT1's home unit.",
      "degree": 1
    },
    {
      "id": "energy_sector",
      "label": "Energy sector targets",
      "type": "target_sector",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Power generation, transmission and oil-and-gas operators.",
      "degree": 10
    },
    {
      "id": "ics_scada",
      "label": "ICS / SCADA systems",
      "type": "target_sector",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Industrial control systems and the protocols they speak (Modbus, DNP3, S7).",
      "degree": 4
    },
    {
      "id": "ukraine_grid_2015",
      "label": "Ukraine power grid 2015",
      "type": "incident",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "First confirmed blackout caused by a cyber-attack; ~225,000 customers affected.",
      "degree": 4
    },
    {
      "id": "ukraine_grid_2016",
      "label": "Ukraine power grid 2016",
      "type": "incident",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Industroyer-driven outage in Kyiv; first ICS-tailored framework in the wild.",
      "degree": 4
    },
    {
      "id": "triton",
      "label": "Triton / Trisis",
      "type": "malware",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "ICS malware targeting Schneider Triconex safety controllers in a Saudi facility.",
      "degree": 3
    },
    {
      "id": "colonial_pipeline",
      "label": "Colonial Pipeline 2021",
      "type": "incident",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "DarkSide ransomware halted US East Coast fuel distribution for six days.",
      "degree": 2
    },
    {
      "id": "darkside",
      "label": "DarkSide RaaS",
      "type": "threat_actor",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Russian-speaking ransomware affiliate program responsible for Colonial Pipeline.",
      "degree": 2
    },
    {
      "id": "water_utilities",
      "label": "Water and wastewater utilities",
      "type": "target_sector",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Municipal and regional water systems; frequently low-maturity OT environments.",
      "degree": 2
    },
    {
      "id": "oldsmar_water",
      "label": "Oldsmar water plant 2021",
      "type": "incident",
      "community": "critical_infra",
      "community_label": "Critical infrastructure incidents",
      "description": "Remote intruder briefly altered sodium hydroxide setpoints at a Florida utility.",
      "degree": 1
    },
    {
      "id": "apt33",
      "label": "APT33 (Elfin / Refined Kitten)",
      "type": "threat_actor",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "IRGC-linked actor targeting aerospace and energy sectors across the Gulf.",
      "degree": 5
    },
    {
      "id": "aramco_2012",
      "label": "Saudi Aramco attack 2012",
      "type": "incident",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "Shamoon wiped ~35,000 workstations at the world's largest oil producer.",
      "degree": 3
    },
    {
      "id": "irgc",
      "label": "IRGC",
      "type": "agency",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "Islamic Revolutionary Guard Corps; sponsor of APT33 and APT35.",
      "degree": 3
    },
    {
      "id": "mois",
      "label": "MOIS",
      "type": "agency",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "Iran's Ministry of Intelligence and Security; sponsor of APT34 and MuddyWater.",
      "degree": 3
    },
    {
      "id": "muddywater",
      "label": "MuddyWater",
      "type": "threat_actor",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "MOIS subcontractor running broad regional campaigns with off-the-shelf tooling.",
      "degree": 3
    },
    {
      "id": "shamoon",
      "label": "Shamoon / DistTrack",
      "type": "malware",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "Disk wiper deployed against Saudi Aramco in 2012 and reused through 2018.",
      "degree": 3
    },
    {
      "id": "apt34",
      "label": "APT34 (OilRig)",
      "type": "threat_actor",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "MOIS-attributed cluster focused on the Middle East energy and government sectors.",
      "degree": 2
    },
    {
      "id": "apt35",
      "label": "APT35 (Charming Kitten)",
      "type": "threat_actor",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "IRGC-attributed credential-phishing operator targeting journalists and academics.",
      "degree": 2
    },
    {
      "id": "albania_2022",
      "label": "Albania attack 2022",
      "type": "incident",
      "community": "iran",
      "community_label": "Iran-aligned",
      "description": "MuddyWater wiper campaign that severed diplomatic relations with Tehran.",
      "degree": 1
    },
    {
      "id": "lazarus",
      "label": "Lazarus Group",
      "type": "threat_actor",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "DPRK umbrella cluster behind destructive, espionage and financial operations.",
      "degree": 10
    },
    {
      "id": "bluenoroff",
      "label": "BlueNoroff",
      "type": "threat_actor",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "Financial heist sub-cluster of Lazarus targeting banks and crypto firms.",
      "degree": 4
    },
    {
      "id": "rgb_121",
      "label": "RGB Bureau 121",
      "type": "agency",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "Reconnaissance General Bureau cyber arm; parent of the DPRK APT ecosystem.",
      "degree": 4
    },
    {
      "id": "andariel",
      "label": "Andariel",
      "type": "threat_actor",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "DPRK actor blending defence-sector espionage with ransomware-for-revenue.",
      "degree": 2
    },
    {
      "id": "applejeus",
      "label": "AppleJeus",
      "type": "malware",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "Trojanised crypto-trading apps used to compromise exchanges and individuals.",
      "degree": 2
    },
    {
      "id": "kimsuky",
      "label": "Kimsuky",
      "type": "threat_actor",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "RGB-aligned espionage cluster focused on policy and nuclear research targets.",
      "degree": 2
    },
    {
      "id": "wannacry",
      "label": "WannaCry",
      "type": "malware",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "Worming ransomware leveraging EternalBlue; attributed to Lazarus in May 2017.",
      "degree": 2
    },
    {
      "id": "bangladesh_bank",
      "label": "Bangladesh Bank heist 2016",
      "type": "incident",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "SWIFT-network theft of USD 81M from the central bank; linked to BlueNoroff.",
      "degree": 1
    },
    {
      "id": "ronin_bridge",
      "label": "Ronin Bridge heist 2022",
      "type": "incident",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "USD 620M theft from the Axie Infinity bridge attributed to Lazarus by FBI.",
      "degree": 1
    },
    {
      "id": "sony_2014",
      "label": "Sony Pictures hack 2014",
      "type": "incident",
      "community": "north_korea",
      "community_label": "North Korea-aligned",
      "description": "Destructive intrusion in retaliation for 'The Interview'; FBI attributed to DPRK.",
      "degree": 1
    },
    {
      "id": "sandworm",
      "label": "Sandworm (Unit 74455)",
      "type": "threat_actor",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "GRU destructive operations unit behind power-grid and wiper campaigns.",
      "degree": 7
    },
    {
      "id": "apt29",
      "label": "APT29 (Cozy Bear)",
      "type": "threat_actor",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "SVR-linked APT specialising in long-dwell intrusions of government and think-tanks.",
      "degree": 6
    },
    {
      "id": "apt28",
      "label": "APT28 (Fancy Bear)",
      "type": "threat_actor",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "GRU Unit 26165 cyber-espionage group; political and military targets in NATO states.",
      "degree": 5
    },
    {
      "id": "blackenergy",
      "label": "BlackEnergy",
      "type": "malware",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Modular toolkit used in early Ukraine grid intrusions; precursor to Industroyer.",
      "degree": 4
    },
    {
      "id": "fsb",
      "label": "FSB",
      "type": "agency",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Russian Federal Security Service; sponsor of Turla and Gamaredon.",
      "degree": 4
    },
    {
      "id": "gru",
      "label": "GRU (military intel)",
      "type": "agency",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Russian military intelligence directorate, parent of Units 26165 and 74455.",
      "degree": 4
    },
    {
      "id": "industroyer",
      "label": "Industroyer / CrashOverride",
      "type": "malware",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "First malware framework purpose-built to attack industrial control systems.",
      "degree": 3
    },
    {
      "id": "notpetya",
      "label": "NotPetya",
      "type": "malware",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Destructive wiper disguised as ransomware; spread via MEDoc update channel in 2017.",
      "degree": 3
    },
    {
      "id": "turla",
      "label": "Turla (Snake)",
      "type": "threat_actor",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "FSB-aligned actor known for satellite-based C2 and long-running espionage.",
      "degree": 3
    },
    {
      "id": "caddywiper",
      "label": "CaddyWiper",
      "type": "malware",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Disk wiper deployed against Ukrainian targets during the 2022 invasion.",
      "degree": 1
    },
    {
      "id": "gamaredon",
      "label": "Gamaredon",
      "type": "threat_actor",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "FSB-attributed Ukraine-focused operator with high-volume, low-stealth ops.",
      "degree": 1
    },
    {
      "id": "svr",
      "label": "SVR",
      "type": "agency",
      "community": "russia",
      "community_label": "Russia-aligned",
      "description": "Russian Foreign Intelligence Service; sponsor of APT29-class operations.",
      "degree": 1
    },
    {
      "id": "journalist_targets",
      "label": "Journalists and dissidents",
      "type": "target_sector",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Recurring target population for commercial spyware operators worldwide.",
      "degree": 4
    },
    {
      "id": "finfisher",
      "label": "FinFisher / FinSpy",
      "type": "malware",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Long-running commercial implant family marketed to law-enforcement agencies.",
      "degree": 3
    },
    {
      "id": "nso_group",
      "label": "NSO Group",
      "type": "vendor",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Israeli spyware vendor whose Pegasus implant has been deployed in 45+ countries.",
      "degree": 3
    },
    {
      "id": "pegasus",
      "label": "Pegasus",
      "type": "malware",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Zero-click iOS/Android implant marketed for 'lawful intercept'.",
      "degree": 3
    },
    {
      "id": "predator_spyware",
      "label": "Predator spyware",
      "type": "malware",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Mobile implant marketed by Cytrox/Intellexa; tracked by Citizen Lab and Google TAG.",
      "degree": 3
    },
    {
      "id": "candiru",
      "label": "Candiru",
      "type": "vendor",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Israeli vendor sanctioned by the US in 2021 alongside NSO Group.",
      "degree": 2
    },
    {
      "id": "cytrox",
      "label": "Cytrox",
      "type": "vendor",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "North Macedonian vendor and developer of the Predator implant.",
      "degree": 2
    },
    {
      "id": "hacking_team",
      "label": "Hacking Team",
      "type": "vendor",
      "community": "spyware",
      "community_label": "Commercial spyware / mercenary",
      "description": "Italian vendor whose source code was leaked in 2015, exposing global clientele.",
      "degree": 2
    },
    {
      "id": "solarwinds",
      "label": "SolarWinds / SUNBURST 2020",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Trojanised Orion updates gave SVR access to ~18,000 organisations worldwide.",
      "degree": 6
    },
    {
      "id": "cl0p",
      "label": "Cl0p ransomware gang",
      "type": "threat_actor",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Russian-speaking extortion group specialising in zero-day mass exploitation.",
      "degree": 3
    },
    {
      "id": "kaseya",
      "label": "Kaseya VSA 2021",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "REvil exploitation of VSA pushed ransomware to hundreds of downstream MSP clients.",
      "degree": 3
    },
    {
      "id": "moveit",
      "label": "MOVEit Transfer 2023",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Cl0p mass-exploitation of CVE-2023-34362 against thousands of file-transfer servers.",
      "degree": 3
    },
    {
      "id": "3cx",
      "label": "3CX supply chain 2023",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Trojanised desktop client distributed via signed installers; DPRK attribution.",
      "degree": 2
    },
    {
      "id": "ccleaner_2017",
      "label": "CCleaner 2017",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Trojanised CCleaner update reached ~2.27M users; second-stage filter selected APT10 targets.",
      "degree": 2
    },
    {
      "id": "sunburst_malware",
      "label": "SUNBURST backdoor",
      "type": "malware",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Stealthy .NET implant injected into SolarWinds.Orion.Core.BusinessLayer.dll.",
      "degree": 2
    },
    {
      "id": "xz_utils",
      "label": "XZ Utils backdoor 2024",
      "type": "incident",
      "community": "supply_chain",
      "community_label": "Supply chain campaigns",
      "description": "Multi-year social-engineering of an OSS maintainer yielded a near-miss sshd backdoor.",
      "degree": 1
    },
    {
      "id": "nsa_tao",
      "label": "NSA / Tailored Access Ops",
      "type": "agency",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "US signals-intel offensive arm; developer of bespoke implants and zero-days.",
      "degree": 7
    },
    {
      "id": "five_eyes",
      "label": "Five Eyes alliance",
      "type": "alliance",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "AUS-CAN-NZ-UK-US signals-intelligence sharing arrangement.",
      "degree": 5
    },
    {
      "id": "stuxnet",
      "label": "Stuxnet",
      "type": "malware",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "Worm that sabotaged Natanz centrifuges; opened the era of cyber-physical warfare.",
      "degree": 5
    },
    {
      "id": "shadow_brokers",
      "label": "Shadow Brokers leak 2016",
      "type": "incident",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "Unknown group released NSA TAO tooling, including EternalBlue and DoublePulsar.",
      "degree": 4
    },
    {
      "id": "eternalblue",
      "label": "EternalBlue (CVE-2017-0144)",
      "type": "vulnerability",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "SMBv1 RCE developed by NSA TAO; leaked by Shadow Brokers in April 2017.",
      "degree": 3
    },
    {
      "id": "gchq",
      "label": "GCHQ",
      "type": "agency",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "UK signals intelligence agency and Five Eyes partner.",
      "degree": 3
    },
    {
      "id": "cia",
      "label": "CIA",
      "type": "agency",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "US foreign intelligence service; covert cyber capability exposed via Vault 7.",
      "degree": 2
    },
    {
      "id": "equation_group",
      "label": "Equation Group",
      "type": "threat_actor",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "Cluster widely linked to the NSA; high-end implants disclosed by Kaspersky in 2015.",
      "degree": 2
    },
    {
      "id": "unit_8200",
      "label": "IDF Unit 8200",
      "type": "agency",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "Israeli signals-intel unit; co-developer of Stuxnet under Operation Olympic Games.",
      "degree": 1
    },
    {
      "id": "vault_7",
      "label": "Vault 7 leak 2017",
      "type": "incident",
      "community": "western",
      "community_label": "Western intel (Five Eyes + allies)",
      "description": "WikiLeaks disclosure of CIA cyber-capabilities and implant frameworks.",
      "degree": 1
    }
  ],
  "edges": [
    {
      "source": "3cx",
      "target": "xz_utils",
      "type": "shares_pattern"
    },
    {
      "source": "andariel",
      "target": "rgb_121",
      "type": "operated_by"
    },
    {
      "source": "apt1",
      "target": "pla_61398",
      "type": "operated_by"
    },
    {
      "source": "apt10",
      "target": "apt41",
      "type": "shares_tooling"
    },
    {
      "source": "apt10",
      "target": "ccleaner_2017",
      "type": "conducted"
    },
    {
      "source": "apt10",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "apt10",
      "target": "plugx",
      "type": "uses"
    },
    {
      "source": "apt28",
      "target": "apt29",
      "type": "shares_targets"
    },
    {
      "source": "apt28",
      "target": "five_eyes",
      "type": "targeted"
    },
    {
      "source": "apt28",
      "target": "gru",
      "type": "operated_by"
    },
    {
      "source": "apt28",
      "target": "shadow_brokers",
      "type": "benefited_from"
    },
    {
      "source": "apt28",
      "target": "turla",
      "type": "shares_infra"
    },
    {
      "source": "apt29",
      "target": "five_eyes",
      "type": "targeted"
    },
    {
      "source": "apt29",
      "target": "solarwinds",
      "type": "conducted"
    },
    {
      "source": "apt29",
      "target": "sunburst_malware",
      "type": "deployed"
    },
    {
      "source": "apt29",
      "target": "svr",
      "type": "operated_by"
    },
    {
      "source": "apt29",
      "target": "turla",
      "type": "shares_targets"
    },
    {
      "source": "apt33",
      "target": "aramco_2012",
      "type": "conducted"
    },
    {
      "source": "apt33",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "apt33",
      "target": "irgc",
      "type": "operated_by"
    },
    {
      "source": "apt33",
      "target": "muddywater",
      "type": "shares_targets"
    },
    {
      "source": "apt33",
      "target": "shamoon",
      "type": "deployed"
    },
    {
      "source": "apt34",
      "target": "apt35",
      "type": "shares_infra"
    },
    {
      "source": "apt34",
      "target": "mois",
      "type": "operated_by"
    },
    {
      "source": "apt35",
      "target": "irgc",
      "type": "operated_by"
    },
    {
      "source": "apt41",
      "target": "journalist_targets",
      "type": "targeted"
    },
    {
      "source": "apt41",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "apt41",
      "target": "shadowpad",
      "type": "uses"
    },
    {
      "source": "aramco_2012",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "blackenergy",
      "target": "ukraine_grid_2015",
      "type": "deployed_in"
    },
    {
      "source": "bluenoroff",
      "target": "applejeus",
      "type": "deployed"
    },
    {
      "source": "bluenoroff",
      "target": "bangladesh_bank",
      "type": "conducted"
    },
    {
      "source": "bluenoroff",
      "target": "rgb_121",
      "type": "operated_by"
    },
    {
      "source": "candiru",
      "target": "hacking_team",
      "type": "shares_market"
    },
    {
      "source": "cia",
      "target": "vault_7",
      "type": "exfiltrated_from"
    },
    {
      "source": "colonial_pipeline",
      "target": "darkside",
      "type": "conducted"
    },
    {
      "source": "colonial_pipeline",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "cytrox",
      "target": "journalist_targets",
      "type": "implicated_in_targeting"
    },
    {
      "source": "cytrox",
      "target": "predator_spyware",
      "type": "vendor_of"
    },
    {
      "source": "equation_group",
      "target": "stuxnet",
      "type": "linked_to"
    },
    {
      "source": "eternalblue",
      "target": "shadow_brokers",
      "type": "leaked"
    },
    {
      "source": "finfisher",
      "target": "journalist_targets",
      "type": "deployed_against"
    },
    {
      "source": "five_eyes",
      "target": "solarwinds",
      "type": "targeted"
    },
    {
      "source": "fsb",
      "target": "cl0p",
      "type": "tolerated_by"
    },
    {
      "source": "fsb",
      "target": "darkside",
      "type": "tolerated_by"
    },
    {
      "source": "gamaredon",
      "target": "fsb",
      "type": "operated_by"
    },
    {
      "source": "gchq",
      "target": "five_eyes",
      "type": "member_of"
    },
    {
      "source": "gchq",
      "target": "pegasus",
      "type": "procured_by"
    },
    {
      "source": "gru",
      "target": "shadow_brokers",
      "type": "suspected_link"
    },
    {
      "source": "gru",
      "target": "triton",
      "type": "linked_to"
    },
    {
      "source": "hacking_team",
      "target": "finfisher",
      "type": "shares_market"
    },
    {
      "source": "hafnium",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "hafnium",
      "target": "proxylogon",
      "type": "exploits"
    },
    {
      "source": "industroyer",
      "target": "blackenergy",
      "type": "evolved_into"
    },
    {
      "source": "industroyer",
      "target": "ukraine_grid_2016",
      "type": "deployed_in"
    },
    {
      "source": "irgc",
      "target": "stuxnet",
      "type": "targeted"
    },
    {
      "source": "kaseya",
      "target": "cl0p",
      "type": "linked_to"
    },
    {
      "source": "kaseya",
      "target": "moveit",
      "type": "shares_pattern"
    },
    {
      "source": "kimsuky",
      "target": "rgb_121",
      "type": "operated_by"
    },
    {
      "source": "lazarus",
      "target": "3cx",
      "type": "conducted"
    },
    {
      "source": "lazarus",
      "target": "andariel",
      "type": "subgroup_of"
    },
    {
      "source": "lazarus",
      "target": "applejeus",
      "type": "deployed"
    },
    {
      "source": "lazarus",
      "target": "bluenoroff",
      "type": "subgroup_of"
    },
    {
      "source": "lazarus",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "lazarus",
      "target": "kimsuky",
      "type": "shares_infra"
    },
    {
      "source": "lazarus",
      "target": "rgb_121",
      "type": "operated_by"
    },
    {
      "source": "lazarus",
      "target": "ronin_bridge",
      "type": "conducted"
    },
    {
      "source": "lazarus",
      "target": "sony_2014",
      "type": "conducted"
    },
    {
      "source": "lazarus",
      "target": "wannacry",
      "type": "deployed"
    },
    {
      "source": "mois",
      "target": "predator_spyware",
      "type": "procured_by"
    },
    {
      "source": "moveit",
      "target": "cl0p",
      "type": "conducted"
    },
    {
      "source": "mss",
      "target": "finfisher",
      "type": "procured_by"
    },
    {
      "source": "muddywater",
      "target": "albania_2022",
      "type": "conducted"
    },
    {
      "source": "muddywater",
      "target": "mois",
      "type": "operated_by"
    },
    {
      "source": "mustang_panda",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "mustang_panda",
      "target": "plugx",
      "type": "uses"
    },
    {
      "source": "notpetya",
      "target": "blackenergy",
      "type": "shares_code"
    },
    {
      "source": "notpetya",
      "target": "solarwinds",
      "type": "shares_pattern"
    },
    {
      "source": "nsa_tao",
      "target": "cia",
      "type": "shares_intel"
    },
    {
      "source": "nsa_tao",
      "target": "equation_group",
      "type": "attributed_to"
    },
    {
      "source": "nsa_tao",
      "target": "eternalblue",
      "type": "developed"
    },
    {
      "source": "nsa_tao",
      "target": "five_eyes",
      "type": "member_of"
    },
    {
      "source": "nsa_tao",
      "target": "gchq",
      "type": "shares_intel"
    },
    {
      "source": "nsa_tao",
      "target": "shadow_brokers",
      "type": "exfiltrated_from"
    },
    {
      "source": "nsa_tao",
      "target": "stuxnet",
      "type": "co_developed"
    },
    {
      "source": "nso_group",
      "target": "candiru",
      "type": "shares_market"
    },
    {
      "source": "nso_group",
      "target": "journalist_targets",
      "type": "implicated_in_targeting"
    },
    {
      "source": "nso_group",
      "target": "pegasus",
      "type": "vendor_of"
    },
    {
      "source": "oldsmar_water",
      "target": "water_utilities",
      "type": "targeted"
    },
    {
      "source": "pegasus",
      "target": "predator_spyware",
      "type": "shares_capability"
    },
    {
      "source": "plugx",
      "target": "shadowpad",
      "type": "evolved_into"
    },
    {
      "source": "proxylogon",
      "target": "moveit",
      "type": "shares_pattern"
    },
    {
      "source": "salt_typhoon",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "salt_typhoon",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "sandworm",
      "target": "blackenergy",
      "type": "deployed"
    },
    {
      "source": "sandworm",
      "target": "caddywiper",
      "type": "deployed"
    },
    {
      "source": "sandworm",
      "target": "gru",
      "type": "operated_by"
    },
    {
      "source": "sandworm",
      "target": "industroyer",
      "type": "deployed"
    },
    {
      "source": "sandworm",
      "target": "notpetya",
      "type": "deployed"
    },
    {
      "source": "sandworm",
      "target": "ukraine_grid_2015",
      "type": "conducted"
    },
    {
      "source": "sandworm",
      "target": "ukraine_grid_2016",
      "type": "conducted"
    },
    {
      "source": "shamoon",
      "target": "aramco_2012",
      "type": "deployed_in"
    },
    {
      "source": "shamoon",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "solarwinds",
      "target": "ccleaner_2017",
      "type": "preceded"
    },
    {
      "source": "solarwinds",
      "target": "kaseya",
      "type": "preceded"
    },
    {
      "source": "solarwinds",
      "target": "sunburst_malware",
      "type": "delivered"
    },
    {
      "source": "stuxnet",
      "target": "ics_scada",
      "type": "targets"
    },
    {
      "source": "triton",
      "target": "energy_sector",
      "type": "targets"
    },
    {
      "source": "triton",
      "target": "ics_scada",
      "type": "targets"
    },
    {
      "source": "turla",
      "target": "fsb",
      "type": "operated_by"
    },
    {
      "source": "ukraine_grid_2015",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "ukraine_grid_2015",
      "target": "ics_scada",
      "type": "targeted"
    },
    {
      "source": "ukraine_grid_2016",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "ukraine_grid_2016",
      "target": "ics_scada",
      "type": "targeted"
    },
    {
      "source": "unit_8200",
      "target": "stuxnet",
      "type": "co_developed"
    },
    {
      "source": "volt_typhoon",
      "target": "energy_sector",
      "type": "targeted"
    },
    {
      "source": "volt_typhoon",
      "target": "mss",
      "type": "operated_by"
    },
    {
      "source": "volt_typhoon",
      "target": "salt_typhoon",
      "type": "shares_targets"
    },
    {
      "source": "volt_typhoon",
      "target": "water_utilities",
      "type": "targeted"
    },
    {
      "source": "wannacry",
      "target": "eternalblue",
      "type": "exploits"
    }
  ]
};
