# Security Tooling Reference — Black Arch vs Kali (Niche / Special-Use-Case)

**For:** the operator · building a red-team / recon / cloud / OSINT workstation on Black Arch or Kali
**Date:** 2026-08-29 · **Scope:** niche, special-use-case tools across 4 categories (famous defaults noted only as baseline)
**Legend:** ✅ = ships in that distro's default repo (verified) · `pip`/`git` = install that way · ⚠️ = absent from both default repos, install via pip/git/go

> Distro coverage verified 2026-08-29 against `blackarch.org/tools.html` (2,859 pkgs) and `pkg.kali.org/pkg/<name>` (kali-rolling).

---

## 0. The distro call (read this first)

| Factor | Kali (Debian) | Black Arch (Arch) |
|---|---|---|
| Package count | ~600 curated menu tools | 2,859 (broadest) |
| Out-of-box menu | Yes (full categorized GUI) | No — `pacman -S` groups |
| Niche coverage | Operator favorites (trivy, gitleaks, peirates, bloodhound, certipy-ad) | Widest niche (evilginx2, modlishka, scarecrow, havoc, kube-hunter, scoutsuite, prowler) |
| Install ergonomics | `apt install` / `pipx` | `pacman -S` / AUR-adjacent |
| Cloud multi-audit (scoutsuite/prowler/kube-hunter) | ⚠️ not in default repos | ✅ native |
| Azure AD tooling (ROADtools/cloudsplaining/MSOLSpray/MFASweep) | ⚠️ neither distro | ⚠️ neither distro — pip/git on both |
| Best for | fastest productive setup, beginners, training labs | maximal tool breadth, bleeding-edge, minimal ISO |

**Recommendation:** If you want the most niche tools with least yak-shaving, **Black Arch** ships more of the special-use-case items natively. If you want the smoothest day-one experience, **Kali** + a `pipx`/`pip` layer for the cloud/Azure tools it lacks.

---

## 1. Red Teaming / Offensive

**Baseline (not detailed):** `metasploit-framework`, `nmap`, `masscan`.

### 1a. Initial access & phishing
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| GoPhish | `gophish` | `gophish` | Full email-phish sim w/ landing pages + tracking | https://github.com/gophish/gophish |
| Evilginx2 | `evilginx` | `evilginx2` | MITM reverse-proxy; steals live 2FA session cookies | https://github.com/kgretzky/evilginx2 |
| Modlishka | ⚠️ git | `modlishka` | Plugin-driven transparent proxy, 2FA bypass | https://github.com/drk1wi/Modlishka |
| Luce | ⚠️ git | `luce` | Turnkey Evilginx2 campaign orchestration | https://github.com/hugsy/luce |
| Karkinos | ⚠️ git | `karkinos` | Bundle: encoding + cred test + phish-page gen | https://github.com/entynetproject/karkinos |
| King Phisher | `king-phisher` | `king-phisher` | Templates, SMS lures, remote-access client | https://github.com/securestate/king-phisher |

### 1b. C2 frameworks (beyond Cobalt Strike)
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Sliver | `sliver` | `sliver` | Free multi-platform C2, MTLS/DNS/HTTP2, no license | https://github.com/BishopFox/sliver |
| Mythic | ⚠️ own installer | `mythic` | Multi-user, Dockerized agents, collab ops | https://github.com/its-a-feature/Mythic |
| Covenant | ⚠️ own installer | `covenant` | .NET Core graph-based C2 | https://github.com/cobbr/Covenant |
| Merlin | ⚠️ own installer | `merlin` | Go C2 over HTTP/2 for protocol evasion | https://github.com/Ne0nd0g/merlin |
| PoshC2 | `poshc2` | `posh-c2` | PowerShell/.NET/C# implants, OneNote delivery | https://github.com/nettitude/PoshC2 |
| Havoc | ⚠️ git | `havoc` | Modern UI, Demon agent, EDR-evasion focus | https://github.com/HavocFramework/Havoc |

### 1c. Payload / AV-evasion & obfuscation
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| ScareCrow | ⚠️ git | `scarecrow` | Process injection + AMSI/ETW bypass | https://github.com/optiv/ScareCrow |
| Donut | `donut` | `donut` | .NET/VBS/JS → in-memory shellcode, no disk | https://github.com/TheWover/donut |
| Veil | `veil` | `veil` | AV-evading loaders via multi-encoder | https://github.com/Veil-Framework/Veil |
| Chimera | ⚠️ git | `chimera` | PS obfuscator vs static AV | https://github.com/tokyoneon/Chimera |
| ThreadStackSpoofer | ⚠️ git | `threadstackspoofer` | Hides call stacks from EDR memory analysis | https://github.com/icyguider/ThreadStackSpoofer |
| NimlineWhispers | ⚠️ git | `nimlinewhispers` | Direct syscalls in Nim to dodge userland hooks | https://github.com/ajpc500/NimlineWhispers |
| ConfuserEx | ⚠️ git | `confuserex` | .NET rename + control-flow flatten + anti-tamper | https://github.com/mkaring/ConfuserEx |
| SharpGen | ⚠️ git | `sharpgen` | C# → shellcode w/o PowerShell | https://github.com/cobbr/SharpGen |
| Go-Purple | ⚠️ git | `go-purple` | Aggregates evasion/loader tools in one console | https://github.com/redteam-operator/go-purple |

### 1d. Post-exploitation & lateral movement (incl. AD)
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| NetExec (nxc) | `netexec` | `netexec` | CrackMapExec successor; SMB/WinRM/LDAP/MSSQL at scale | https://github.com/Pennyw0rth/NetExec |
| BloodHound | `bloodhound` | `bloodhound` + `bloodhound-python` | Visualizes AD attack paths (Kerberos/ACL/DACL) | https://github.com/BloodHoundAD/BloodHound |
| Impacket | `impacket` | `impacket` | psexec/secretsdump/ntlmrelayx/ticketer | https://github.com/fortra/impacket |
| Evil-WinRM | `evil-winrm` | `evil-winrm` | WinRM shell w/ SSL, up/download | https://github.com/Hackplayers/evil-winrm |
| Certipy | `certipy-ad` | `certipy` | AD CS abuse ESC1–ESC8 for domain auth | https://github.com/ly4k/Certipy |
| Kerbrute | `kerbrute` | `kerbrute` | Pre-auth user enum, AS-REP roast, SPN enum | https://github.com/ropnop/kerbrute |
| Responder | `responder` | `responder` | LLMNR/NBT-NS/mDNS poison → NetNTLM | https://github.com/lgandx/Responder |
| ldapdomaindump | `ldapdomaindump` | `ldapdomaindump` | AD JSON/HTML dumps for offline graphing | https://github.com/dirkjanm/ldapdomaindump |
| MITM6 | ⚠️ git | `mitm6` | IPv6 WPAD spoof + NTLM relay to AD | https://github.com/fox-it/mitm6 |
| DeathStar | ⚠️ git | `deathstar` | Automates BloodHound → Domain Admin via Empire | https://github.com/byt3bl33d3r/DeathStar |
| SprayingToolkit | ⚠️ git | `sprayingtoolkit` | Lync/SMB/OWA/O365 spray, lockout-aware | https://github.com/byt3bl33d3r/SprayingToolkit |
| PCredz | ⚠️ git | `pcredz` | Extracts creds/hashes from live/PCAP traffic | https://github.com/lgandx/PCredz |

### 1e. Exploit dev & fuzzing
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| pwntools | `pwntools` | `pwntools` | ROP/tubes/shellcraft automation | https://github.com/Gallopsled/pwntools |
| AFL++ | `afl++` | `aflpp` | Coverage-guided fuzz; QEMU/Unicorn/Frida modes | https://github.com/AFLplusplus/AFLplusplus |
| Boofuzz | `boofuzz` | `boofuzz` | Protocol-aware fuzz w/ crash monitoring | https://github.com/jtpereyda/boofuzz |
| Frida | `frida` | `frida` | Runtime hooking w/o source | https://github.com/frida/frida |
| Ropper | ⚠️ git | `ropper` | ROP/JOP gadget finder + chaining | https://github.com/sashs/Ropper |

---

## 2. Node Discovery / Recon / Attack-Surface Mapping

**Baseline (not detailed):** `nmap`, `masscan`, `nessus`.

### 2a. Internet-wide scanning & exposure mapping
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Shodan CLI | `shodan` | `shodan` | Passive exposure map w/o sending a packet | https://github.com/achillean/shodan-python |
| Censys | `censys` | `censys` | Cert-transparency view; find hosts behind CDNs | https://github.com/censys/censys-python |
| ZoomEye | ⚠️ git | `zoomeye` | Strong APAC/industrial coverage | https://github.com/knownsec/zoomeye-python |
| ONYPHE | ⚠️ git | `onyphe` | Reputation + historical exposure correlation | https://github.com/Onyphe-io/onyphe |
| FOFA | ⚠️ git | `fofa` | Favicon/body-hash APAC asset discovery | https://github.com/knownsec/fofa-py |
| GreyNoise | ⚠️ git | `greynoise` | Filter mass-scanner noise from perimeter | https://github.com/GreyNoise-Intelligence/pygreynoise |
| BinaryEdge | ⚠️ git | `binaryedge` | IoT/OT exposure intel | https://github.com/binaryedge/pybinaryedge |
| InternetDB | `shodan` + API | `shodan` + API | Instant open-port + vuln triage per IP | https://internetdb.shodan.io/ |

### 2b. Asset discovery & enumeration
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| amass | `amass` | `amass` | Graph-based subdomain mapping, huge passive list | https://github.com/owasp-amass/amass |
| subfinder | `subfinder` | `subfinder` | Stealthy passive-only subdomain enum | https://github.com/projectdiscovery/subfinder |
| assetfinder | ⚠️ git | `assetfinder` | Quick passive lookups, minimal deps | https://github.com/tomnomnom/assetfinder |
| dnsx | `dnsx` | `dnsx` | Mass DNS validation, wildcard filtering | https://github.com/projectdiscovery/dnsx |
| findomain | ⚠️ git | `findomain` | CT + API enum, no brute | https://github.com/Findomain/Findomain |
| shuffledns | ⚠️ git | `shuffledns` | MassDNS-powered high-speed resolution | https://github.com/projectdiscovery/shuffledns |
| puredns | ⚠️ git | `puredns` | Wildcard elimination for zero false positives | https://github.com/d3mondev/puredns |
| dnsgen | ⚠️ git | `dnsgen` | Permutation discovery from known hosts | https://github.com/ProjectAnte/dnsgen |
| dnsprobe | ⚠️ git | `dnsprobe` | Combined A/AAAA/CNAME/MX/TXT probe | https://github.com/projectdiscovery/dnsprobe |

### 2c. Port & service discovery
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| rustscan | `rustscan` | `rustscan` | Thousands of ports/sec → feeds nmap | https://github.com/RustScan/RustScan |
| naabu | `naabu` | `naabu` | Fast port discovery, passive+active | https://github.com/projectdiscovery/naabu |
| httpx | `httpx` | `httpx` | Title/status/tech/TLS/screenshot at scale | https://github.com/projectdiscovery/httpx |
| feroxbuster | `feroxbuster` | `feroxbuster` | Adaptive recursive content discovery | https://github.com/epi052/feroxbuster |
| gospider | ⚠️ git | `gospider` | Form/JS/robots/sitemap crawler | https://github.com/jaeles-project/gospider |
| katana | ⚠️ git | `katana` | Headless JS rendering; SPA endpoint discovery | https://github.com/projectdiscovery/katana |
| gau | ⚠️ git | `gau` | Historical URLs from Wayback/CommonCrawl/OTX | https://github.com/lc/gau |
| waybackurls | ⚠️ git | `waybackurls` | Quick passive endpoint enum | https://github.com/tomnomnom/waybackurls |
| massdns | ⚠️ git | `massdns` | Millions of resolutions/sec | https://github.com/blechschmidt/massdns |

### 2d. Network mapping & SNMP/LLMNR/mDNS
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| netdiscover | `netdiscover` | `netdiscover` | ARP recon on switched L2 w/o DHCP | https://github.com/netdiscover-scanner/netdiscover |
| arp-scan | `arp-scan` | `arp-scan` | L2 host ID via MAC OUI | https://github.com/royhills/arp-scan |
| nbtscan | `nbtscan` | `nbtscan` | NetBIOS enum w/o SMB auth | https://github.com/resurrecting-open-source-projects/nbtscan |
| onesixtyone | `onesixtyone` | `onesixtyone` | Fast SNMP community-string brute | https://github.com/trailofbits/onesixtyone |
| enum4linux-ng | `enum4linux-ng` | `enum4linux-ng` | SMB null-session/RID/group/user enum | https://github.com/cddmp/enum4linux-ng |
| recon-ng | `recon-ng` | `recon-ng` | Metasploit-like OSINT workspace | https://github.com/lanmaster53/recon-ng |

### 2e. Wireless & Bluetooth node discovery
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| bettercap | `bettercap` | `bettercap` | WiFi/BLE/network MITM + scripting caplets | https://github.com/bettercap/bettercap |
| kismet | `kismet` | `kismet` | Passive 802.11/RF/BT/zigbee IDS | https://www.kismetwireless.net/ |
| aircrack-ng | `aircrack-ng` | `aircrack-ng` | Monitor-mode AP/client discovery | https://www.aircrack-ng.org/ |
| btscanner | ⚠️ | `btscanner` | BT device discovery, names, classes | https://www.blackarch.org/package.html?name=btscanner |
| spooftooph | ⚠️ | `spooftooph` | Clone/spoof BT MAC/name for covert emulation | https://www.blackarch.org/package.html?name=spooftooph |
| hcxpcapngtool | `hcxtools` | `hcxtools` | WiFi handshake → hashcat-ready | https://github.com/ZerBea/hcxtools |

### 2f. IoT/OT discovery
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| firmwalker | ⚠️ git | `firmwalker` | Grep firmware for keys/backdoors/secrets | https://github.com/craigz28/firmwalker |
| binwalk | `binwalk` | `binwalk` | Carve embedded FS/OTA images | https://github.com/ReFirmLabs/binwalk |

---

## 3. Cloud Security / Cloud Attack (AWS · Azure · GCP · K8s)

**Verified availability (2026-08-29):**
- ✅ Black Arch native: `pacu`, `scoutsuite`, `prowler`, `kube-hunter`, `weirdaal`, `enumerate-iam`, `o365enum`, `azurehound`, `trufflehog`, `kubestriker`, `gcpbucketbrute`
- ✅ Kali native: `pacu`, `trivy`, `peirates`, `gitleaks`
- ⚠️ absent from BOTH default repos (pip/git/go on either): `roadtools`, `cloudsplaining`, `kube-bench`, `cloudfox`, `gcp_enum`, `endgame`, `principalmapper`, `aws_consoler`, `msolspray`, `mfasweep`, `scoutsuite`+`prowler`+`kube-hunter` (Kali side only)

### 3a. Cloud enumeration & recon
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| ScoutSuite | ⚠️ pip | ✅ `scoutsuite` | Multi-cloud config audit (AWS/Azure/GCP) | https://github.com/nccgroup/ScoutSuite |
| Prowler | ⚠️ pip | ✅ `prowler` | Compliance + misconfig scanning | https://github.com/prowler-cloud/prowler |
| CloudMapper | ⚠️ git | ⚠️ git | AWS network viz + exposure map | https://github.com/duo-labs/cloudmapper |
| cartography | ⚠️ git | ⚠️ git | Graph DB of cloud attack surface | https://github.com/lyft/cartography |
| cloudsplaining | ⚠️ pip | ⚠️ pip | IAM policy risk scanner | https://github.com/kmcquade/cloudsplaining |
| Steampipe | ⚠️ own | ⚠️ own | SQL queries over cloud APIs | https://steampipe.io/ |

### 3b. AWS attack & exploitation
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Pacu | ✅ `pacu` | ✅ `pacu` | "Metasploit of AWS" — module exploits | https://github.com/RhinoSecurityLabs/pacu |
| weirdAAL | ⚠️ git | ✅ `weirdaal` | AWS attack library, low-noise | https://github.com/trimarc/weirdAAL |
| enumerate-iam | ⚠️ git | ✅ `enumerate-iam` | IAM perm enum w/o writes | https://github.com/andresriancho/enumerate-iam |
| CloudFox | ⚠️ git | ⚠️ git | AWS/Azure attack-path discovery | https://github.com/ChurchOfMax/CloudFox |
| aws_consoler | ⚠️ git | ⚠️ git | Convert keys → console URL | https://github.com/NetSPI/aws_consoler |
| Endgame | ⚠️ git | ⚠️ git | Pacu-style privesc modules | https://github.com/vectra-ai-research/Endgame |
| pmapper / principalmapper | ⚠️ pip | ⚠️ pip | IAM privilege-path graph | https://github.com/nccgroup/pmapper |
| IAM-Vulnerable | ⚠️ git | ⚠️ git | Lab to practice AWS privesc | https://github.com/BishopFox/iam-vulnerable |

### 3c. Azure AD / Entra attack
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| ROADtools | ⚠️ pip | ⚠️ pip | Azure AD recon + auth + privesc | https://github.com/dirkjanm/ROADtools |
| AADInternals | ⚠️ ps | ⚠️ ps | Azure/M365 internals abuse | https://github.com/Gerenios/AADInternals |
| o365enum | ⚠️ git | ✅ `o365enum` | O365 user enumeration | https://github.com/nyxgeek/o365enum |
| MSOLSpray | ⚠️ git | ⚠️ git | Azure/M365 password spray | https://github.com/dafthack/MSOLSpray |
| MFASweep | ⚠️ git | ⚠️ git | Check MFA across Azure endpoints | https://github.com/dafthack/MFASweep |
| AzureHound | ⚠️ git | ✅ `azurehound` | Azure ingest for BloodHound | https://github.com/BloodHoundAD/AzureHound |

### 3d. GCP attack
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| GCPBucketBrute | ⚠️ git | ✅ `gcpbucketbrute` | GCP storage enum/brute | https://github.com/RhinoSecurityLabs/GCPBucketBrute |
| gcp_enum | ⚠️ git | ⚠️ git | GCP permission enum | https://github.com/NetSPI/gcp_enum |
| GCP-IAM-Collector | ⚠️ git | ⚠️ git | IAM policy aggregation | https://github.com/ScaleSec/gcp-iam-collector |

### 3e. Container & Kubernetes security
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| kube-hunter | ⚠️ git | ✅ `kube-hunter` | Remote K8s cluster vuln scan | https://github.com/aquasecurity/kube-hunter |
| kube-bench | ⚠️ go | ⚠️ git | CIS K8s benchmark audit | https://github.com/aquasecurity/kube-bench |
| Trivy | ✅ `trivy` | ⚠️ go | Image/FS/IaC vuln + secret scan | https://github.com/aquasecurity/trivy |
| kubestriker | ⚠️ git | ✅ `kubestriker` | K8s attack-surface scanner | https://github.com/vchinnipilli/kubestriker |
| peirates | ✅ `peirates` | ⚠️ git | K8s privesc + lateral movement | https://github.com/inguardians/peirates |

### 3f. CI/CD & secrets
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| gitleaks | ✅ `gitleaks` | ⚠️ go | Git history secret scan | https://github.com/gitleaks/gitleaks |
| trufflehog | ✅ `trufflehog` | ✅ `trufflehog` | Deep secret verification in repos | https://github.com/trufflesecurity/trufflehog |
| gitrob | ⚠️ git | ⚠️ git | Sensitive-file finder in orgs | https://github.com/michenriksen/gitrob |

---

## 4. OSINT Gathering

**Baseline (not detailed):** `theharvester`, `maltego`.

### 4a. People & social media
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Sherlock | `pipx` | `sherlock` | Username sweep across 400+ sites | https://github.com/sherlock-project/sherlock |
| Maigret | `pip` | `maigret` | Dossier builder, 3000+ sites, low FP | https://github.com/soxoj/maigret |
| Twint | `pip` | `twint` | Twitter scrape w/o API | https://github.com/twintproject/twint |
| Nexfil | `pip` | `nexfil` | Fast 328-site bulk username sweep | https://github.com/thewhiteh4t/nexfil |
| Holehe | `holehe` | `holehe` | Email→registered-site via pw-reset | https://github.com/megadose/holehe |
| Mosint | `pip` | `pip` | All-in-one email OSINT | https://github.com/alpkeskin/mosint |
| GHunt | `ghunt` | ⚠️ git | Reverse Gmail/Google ID → profile | https://github.com/mxrch/GHunt |
| InstagramOSINT | `instagramosint` | `instagramosint` | IG account recon | https://github.com/sc1341/InstagramOSINT |
| linkedin2username | `linkedin2username` | `linkedin2username` | LinkedIn → username lists for spray | https://github.com/initstring/linkedin2username |
| social-analyzer | `social-analyzer` | `social-analyzer` | 999-site profile correlation w/ OCR | https://github.com/qeeqbox/social-analyzer |

### 4b. Username / email correlation
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| WhatsMyName | `pip` | ⚠️ git | Canonical site-detection DB | https://github.com/WebBreacher/WhatsMyName |
| Blackbird | `pip` | ⚠️ git | Email-aware username hunt + export | https://github.com/p1ngul1n0/blackbird |
| socialscan | `pip` | `pip` | Signup-API verify (100% accuracy) | https://github.com/iojw/socialscan |
| Trape | ⚠️ git | `trape` | Real-time online trace tracking | https://github.com/jofpin/trape |
| Cr3dov3r | `cr3dov3r` | ⚠️ git | Email → leak + cred test on 16 sites | https://github.com/D4Vinci/Cr3dov3r |

### 4c. Dorking & scraping frameworks
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Dorkbot | `pip` | ⚠️ git | Dork URL finder + vuln scan | https://github.com/utiso/dorkbot |
| Photon | `photon` | ⚠️ git | Crawl URLs/secrets/buckets/endpoints | https://github.com/s0md3v/Photon |
| Metagoofil | `metagoofil` | `metagoofil` | Doc metadata harvest | https://github.com/laramies/metagoofil |
| DataSploit | `git` | ⚠️ git | Domain/person/phone/BTC aggregation | https://github.com/DataSploit/datasploit |
| Dorkscout | `git` | `dorkscout` | Continuous dork monitoring | https://blackarch.org/automation.html |

### 4d. Documents & metadata
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Exiftool | `libimage-exiftool-perl` | `exiftool` | Read/write metadata 100+ types | https://exiftool.org/ |
| FOCA | `foca` | ⚠️ git | Metadata in scanned docs | https://github.com/ElevenPaths/FOCA |

### 4e. Geospatial & imagery
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| OSRFramework | `pip` | `osrframework` | mailfy/usufy/entify recon | https://github.com/sep0lkit/osrframework |
| Geopy | `pip` | `pip` | Geocoding + distance enrichment | https://github.com/geopy/geopy |
| PhoneInfoga | `phoneinfoga` | `phoneinfoga` | Phone carrier/VoIP/line type | https://github.com/sundowndev/phoneinfoga |
| Creepy | `git` | ⚠️ git | Geotagged-photo movement map | https://github.com/ilektrojohn/creepy |
| Ignorant | `git` | ⚠️ git | Phone→Snapchat/IG registration | https://github.com/megadose/ignorant |

### 4f. Infrastructure & domain OSINT
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Dnsrecon | `dnsrecon` | `dnsrecon` | Zones/brute/SRV/MX enum | https://github.com/darkoperator/dnsrecon |
| Knockpy | `pip` | `knockpy` | Subdomain brute, no API key | https://github.com/guelfoweb/knock |
| Whois | `whois` | `whois` | Ownership/registrar pivots | https://github.com/rfc1036/whois |
| Cymruwhois | `python3-cymruwhois` | `pip` | Bulk IP→ASN via Team Cymru | https://pypi.org/project/cymruwhois/ |
| cloud_enum | `git` | `cloud_enum` | AWS/Azure/GCP public resource enum | https://github.com/initstring/cloud_enum |
| bbot | `pip` | `bbot` | Recursive internet-scale recon graph | https://github.com/blacklanternsecurity/bbot |
| Spiderfoot | `spiderfoot` | `spiderfoot` | 200+ source automated OSINT | https://github.com/smicallef/spiderfoot |

### 4g. Breach / credential & leak search
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| H8mail | `h8mail` | `h8mail` | Email + breach hunting | https://github.com/khast3x/h8mail |
| Cardpwn | `git` | ⚠️ git | Breached card lookup | https://github.com/expl1t3r/cardpwn |
| Dehashed-cli | `pip` | ⚠️ git | Dehashed API queries | https://github.com/dehashed/dehashed-cli |
| Breach-parse | `git` | ⚠️ git | Local breach dump search | https://github.com/hmaverickadams/breach-parse |

### 4h. Other niche
| Tool | Kali | Black Arch | Niche use case | Source |
|---|---|---|---|---|
| Crosslinked | `crosslinked` | `crosslinked` | LinkedIn employee-name scrape | https://github.com/m8r0wn/crosslinked |
| Dnstwist | `dnstwist` | ⚠️ git | Typosquat/phishing domain detect | https://github.com/elceef/dnstwist |
| Waybackpy | `pip` | `pip` | Wayback API: URLs/snapshots/CDX | https://github.com/akamhy/waybackpy |

---

## 5. Quick-reference install cheats

```bash
# Kali — verify + install native packages
apt-cache search <name> && sudo apt install <name>
# Cloud/Azure tools Kali lacks:
pipx install scoutsuite prowler cloudsplaining roadtools
pip install gcp_enum principalmapper

# Black Arch — verify + install (enable repo first: see blackarch.org/downloads)
pacman -Ss <name> && sudo pacman -S <name>
# Azure/Cloudfox tools BA lacks:
pip install roadtools cloudsplaining
```

## 6. Legal boundary
Everything here is for **authorized** testing, your own lab, or bug-bounty scopes you're cleared for. Searching public indexes and running these against systems you don't have written permission to test is illegal in most jurisdictions. Build the lab, get the auth, then run.

---
*Sources: blackarch.org (package index, 2,859 pkgs), pkg.kali.org (kali-rolling trackers), and per-tool GitHub/homepage links above. Package availability verified 2026-08-29; re-verify with `pacman -Ss` / `apt-cache search` before scripting installs, as repos shift.*