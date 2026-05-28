# Synthetic KG — Communities (cyberwarfare / threat intel)

- Nodes: **78**
- Edges: **120**
- Intended communities (hand-curated): **8**
- Louvain communities (sanity check, seed=42): **9**, modularity=0.674

The JSON's `community` field uses the hand-curated assignment below. Louvain is reported only to verify that the graph is actually separable along the intended cuts.

## Russia-aligned (`russia`)

| Label | Type | Description |
|---|---|---|
| APT28 (Fancy Bear) | `threat_actor` | GRU Unit 26165 cyber-espionage group; political and military targets in NATO states. |
| APT29 (Cozy Bear) | `threat_actor` | SVR-linked APT specialising in long-dwell intrusions of government and think-tanks. |
| BlackEnergy | `malware` | Modular toolkit used in early Ukraine grid intrusions; precursor to Industroyer. |
| CaddyWiper | `malware` | Disk wiper deployed against Ukrainian targets during the 2022 invasion. |
| FSB | `agency` | Russian Federal Security Service; sponsor of Turla and Gamaredon. |
| GRU (military intel) | `agency` | Russian military intelligence directorate, parent of Units 26165 and 74455. |
| Gamaredon | `threat_actor` | FSB-attributed Ukraine-focused operator with high-volume, low-stealth ops. |
| Industroyer / CrashOverride | `malware` | First malware framework purpose-built to attack industrial control systems. |
| NotPetya | `malware` | Destructive wiper disguised as ransomware; spread via MEDoc update channel in 2017. |
| SVR | `agency` | Russian Foreign Intelligence Service; sponsor of APT29-class operations. |
| Sandworm (Unit 74455) | `threat_actor` | GRU destructive operations unit behind power-grid and wiper campaigns. |
| Turla (Snake) | `threat_actor` | FSB-aligned actor known for satellite-based C2 and long-running espionage. |

## China-aligned (`china`)

| Label | Type | Description |
|---|---|---|
| APT1 (Comment Crew) | `threat_actor` | PLA Unit 61398; long-running IP theft operations exposed by Mandiant in 2013. |
| APT10 (Stone Panda) | `threat_actor` | MSS-linked group focused on managed service providers (Operation Cloud Hopper). |
| APT41 (Double Dragon) | `threat_actor` | Dual-use MSS contractor blending state espionage with financially motivated ops. |
| Hafnium | `threat_actor` | MSS-linked actor behind the 2021 ProxyLogon mass-exploitation of Exchange servers. |
| MSS (Ministry of State Security) | `agency` | China's civilian intelligence service; primary sponsor of contemporary PRC APTs. |
| Mustang Panda | `threat_actor` | PRC actor targeting NGOs and diplomatic missions across South-East Asia and Europe. |
| PLA Unit 61398 | `agency` | Shanghai-based PLA signals intelligence unit; APT1's home unit. |
| PlugX (Korplug) | `malware` | Modular RAT shared across multiple PRC clusters since 2012. |
| ProxyLogon (CVE-2021-26855) | `vulnerability` | Exchange Server SSRF chain enabling unauthenticated RCE; mass-exploited by Hafnium. |
| Salt Typhoon | `threat_actor` | Telecommunications-focused PRC actor exposed in late 2024 US telco compromises. |
| ShadowPad | `malware` | Successor to PlugX; sold across MSS-linked clusters as a turnkey backdoor. |
| Volt Typhoon | `threat_actor` | Living-off-the-land intrusions of US critical infrastructure for pre-positioning. |

## North Korea-aligned (`north_korea`)

| Label | Type | Description |
|---|---|---|
| Andariel | `threat_actor` | DPRK actor blending defence-sector espionage with ransomware-for-revenue. |
| AppleJeus | `malware` | Trojanised crypto-trading apps used to compromise exchanges and individuals. |
| Bangladesh Bank heist 2016 | `incident` | SWIFT-network theft of USD 81M from the central bank; linked to BlueNoroff. |
| BlueNoroff | `threat_actor` | Financial heist sub-cluster of Lazarus targeting banks and crypto firms. |
| Kimsuky | `threat_actor` | RGB-aligned espionage cluster focused on policy and nuclear research targets. |
| Lazarus Group | `threat_actor` | DPRK umbrella cluster behind destructive, espionage and financial operations. |
| RGB Bureau 121 | `agency` | Reconnaissance General Bureau cyber arm; parent of the DPRK APT ecosystem. |
| Ronin Bridge heist 2022 | `incident` | USD 620M theft from the Axie Infinity bridge attributed to Lazarus by FBI. |
| Sony Pictures hack 2014 | `incident` | Destructive intrusion in retaliation for 'The Interview'; FBI attributed to DPRK. |
| WannaCry | `malware` | Worming ransomware leveraging EternalBlue; attributed to Lazarus in May 2017. |

## Iran-aligned (`iran`)

| Label | Type | Description |
|---|---|---|
| APT33 (Elfin / Refined Kitten) | `threat_actor` | IRGC-linked actor targeting aerospace and energy sectors across the Gulf. |
| APT34 (OilRig) | `threat_actor` | MOIS-attributed cluster focused on the Middle East energy and government sectors. |
| APT35 (Charming Kitten) | `threat_actor` | IRGC-attributed credential-phishing operator targeting journalists and academics. |
| Albania attack 2022 | `incident` | MuddyWater wiper campaign that severed diplomatic relations with Tehran. |
| IRGC | `agency` | Islamic Revolutionary Guard Corps; sponsor of APT33 and APT35. |
| MOIS | `agency` | Iran's Ministry of Intelligence and Security; sponsor of APT34 and MuddyWater. |
| MuddyWater | `threat_actor` | MOIS subcontractor running broad regional campaigns with off-the-shelf tooling. |
| Saudi Aramco attack 2012 | `incident` | Shamoon wiped ~35,000 workstations at the world's largest oil producer. |
| Shamoon / DistTrack | `malware` | Disk wiper deployed against Saudi Aramco in 2012 and reused through 2018. |

## Western intel (Five Eyes + allies) (`western`)

| Label | Type | Description |
|---|---|---|
| CIA | `agency` | US foreign intelligence service; covert cyber capability exposed via Vault 7. |
| Equation Group | `threat_actor` | Cluster widely linked to the NSA; high-end implants disclosed by Kaspersky in 2015. |
| EternalBlue (CVE-2017-0144) | `vulnerability` | SMBv1 RCE developed by NSA TAO; leaked by Shadow Brokers in April 2017. |
| Five Eyes alliance | `alliance` | AUS-CAN-NZ-UK-US signals-intelligence sharing arrangement. |
| GCHQ | `agency` | UK signals intelligence agency and Five Eyes partner. |
| IDF Unit 8200 | `agency` | Israeli signals-intel unit; co-developer of Stuxnet under Operation Olympic Games. |
| NSA / Tailored Access Ops | `agency` | US signals-intel offensive arm; developer of bespoke implants and zero-days. |
| Shadow Brokers leak 2016 | `incident` | Unknown group released NSA TAO tooling, including EternalBlue and DoublePulsar. |
| Stuxnet | `malware` | Worm that sabotaged Natanz centrifuges; opened the era of cyber-physical warfare. |
| Vault 7 leak 2017 | `incident` | WikiLeaks disclosure of CIA cyber-capabilities and implant frameworks. |

## Critical infrastructure incidents (`critical_infra`)

| Label | Type | Description |
|---|---|---|
| Colonial Pipeline 2021 | `incident` | DarkSide ransomware halted US East Coast fuel distribution for six days. |
| DarkSide RaaS | `threat_actor` | Russian-speaking ransomware affiliate program responsible for Colonial Pipeline. |
| Energy sector targets | `target_sector` | Power generation, transmission and oil-and-gas operators. |
| ICS / SCADA systems | `target_sector` | Industrial control systems and the protocols they speak (Modbus, DNP3, S7). |
| Oldsmar water plant 2021 | `incident` | Remote intruder briefly altered sodium hydroxide setpoints at a Florida utility. |
| Triton / Trisis | `malware` | ICS malware targeting Schneider Triconex safety controllers in a Saudi facility. |
| Ukraine power grid 2015 | `incident` | First confirmed blackout caused by a cyber-attack; ~225,000 customers affected. |
| Ukraine power grid 2016 | `incident` | Industroyer-driven outage in Kyiv; first ICS-tailored framework in the wild. |
| Water and wastewater utilities | `target_sector` | Municipal and regional water systems; frequently low-maturity OT environments. |

## Supply chain campaigns (`supply_chain`)

| Label | Type | Description |
|---|---|---|
| 3CX supply chain 2023 | `incident` | Trojanised desktop client distributed via signed installers; DPRK attribution. |
| CCleaner 2017 | `incident` | Trojanised CCleaner update reached ~2.27M users; second-stage filter selected APT10 targets. |
| Cl0p ransomware gang | `threat_actor` | Russian-speaking extortion group specialising in zero-day mass exploitation. |
| Kaseya VSA 2021 | `incident` | REvil exploitation of VSA pushed ransomware to hundreds of downstream MSP clients. |
| MOVEit Transfer 2023 | `incident` | Cl0p mass-exploitation of CVE-2023-34362 against thousands of file-transfer servers. |
| SUNBURST backdoor | `malware` | Stealthy .NET implant injected into SolarWinds.Orion.Core.BusinessLayer.dll. |
| SolarWinds / SUNBURST 2020 | `incident` | Trojanised Orion updates gave SVR access to ~18,000 organisations worldwide. |
| XZ Utils backdoor 2024 | `incident` | Multi-year social-engineering of an OSS maintainer yielded a near-miss sshd backdoor. |

## Commercial spyware / mercenary (`spyware`)

| Label | Type | Description |
|---|---|---|
| Candiru | `vendor` | Israeli vendor sanctioned by the US in 2021 alongside NSO Group. |
| Cytrox | `vendor` | North Macedonian vendor and developer of the Predator implant. |
| FinFisher / FinSpy | `malware` | Long-running commercial implant family marketed to law-enforcement agencies. |
| Hacking Team | `vendor` | Italian vendor whose source code was leaked in 2015, exposing global clientele. |
| Journalists and dissidents | `target_sector` | Recurring target population for commercial spyware operators worldwide. |
| NSO Group | `vendor` | Israeli spyware vendor whose Pegasus implant has been deployed in 45+ countries. |
| Pegasus | `malware` | Zero-click iOS/Android implant marketed for 'lawful intercept'. |
| Predator spyware | `malware` | Mobile implant marketed by Cytrox/Intellexa; tracked by Citizen Lab and Google TAG. |

## Louvain vs intended cross-tab

Rows = intended community. Columns = Louvain group index. Off-diagonal mass = nodes that Louvain assigned to a different group.

| intended \ louvain | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | total |
|---|---|---|---|---|---|---|---|---|---|---|
| russia | 6 | 2 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 12 |
| china | 0 | 2 | 2 | 8 | 0 | 0 | 0 | 0 | 0 | 12 |
| north_korea | 0 | 0 | 0 | 0 | 0 | 1 | 9 | 0 | 0 | 10 |
| iran | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 9 |
| western | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 1 | 0 | 10 |
| critical_infra | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 9 |
| supply_chain | 0 | 3 | 0 | 1 | 2 | 0 | 2 | 0 | 0 | 8 |
| spyware | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 |

