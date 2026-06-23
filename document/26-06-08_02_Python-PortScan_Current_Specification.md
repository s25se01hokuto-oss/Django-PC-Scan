# Python-PortScan / Django-Ping — Current System Specification

**Document ID:** 26-06-08_02  
**Date:** June 8, 2026  
**Classification:** System Specification  

---

## 1. System Overview

The **Classroom PC Live Status Map** is a Django-based web application that monitors the power state of Windows PCs in a classroom LAN environment. The system displays a real-time seat map dashboard where each PC is colour-coded: **green (Alive)** or **red (Dead)**.

### Key Design Constraint

Standard host-detection methods (ICMP ping, TCP port scanning) are **blocked** by the target Windows PCs' firewalls and/or network switch ACLs. The system overcomes this by reading the **Linux ARP cache** on the monitoring server — a completely passive, firewall-proof technique.

---

## 2. Architecture

### 2.1 High-Level Data Flow

```
┌───────────────┐   cron (*/5)   ┌──────────────────────┐
│  Linux Kernel │ ←────────────  │  Django Management   │
│   ARP Cache   │   arp -an      │  Command: check_arp  │
│  (enp1s0)     │ ──────────→    │                      │
└───────────────┘   stdout       └──────────┬───────────┘
                                            │ ORM update
                                            ▼
                                 ┌──────────────────────┐
                                 │   SQLite Database     │
                                 │   (db.sqlite3)        │
                                 │   Seat.status field   │
                                 └──────────┬───────────┘
                                            │ query
                                            ▼
┌───────────────┐   HTTP 200     ┌──────────────────────┐
│  User Browser │ ←────────────  │  Django View:        │
│  (auto-reload │   HTML+CSS     │  seat_map_view       │
│   every 5s)   │                │                      │
└───────────────┘                └──────────────────────┘
```

### 2.2 Technology Stack

| Layer             | Technology         | Version              |
| :---------------- | :----------------- | :------------------- |
| Language          | Python             | 3.14.0               |
| Framework         | Django             | 6.0.5                |
| Database          | SQLite3            | (bundled)            |
| Scheduler         | Ubuntu system cron | —                    |
| OS                | Ubuntu Linux       | —                    |
| Network Interface | enp1s0             | LAN 192.168.203.0/24 |

---

## 3. Why the ARP Cache Method Works

### 3.1 Problem: Firewall Blocks Active Probes

Windows Defender Firewall blocks:
- **ICMP Echo Request** (ping) — dropped silently, returns "Dead" even when the host is powered on.
- **TCP SYN to Port 445 (SMB)** — dropped or filtered by switch/firewall, connection times out.
- **TCP SYN to Port 135 (RPC)** — same result; timeout returns "Dead".

### 3.2 Solution: Passive ARP Cache Reading

The Linux kernel maintains an ARP (Address Resolution Protocol) cache table mapping IP addresses to MAC (hardware) addresses for all hosts that have recently communicated on the local network segment.

When `arp -an` is executed, the output contains lines such as:

```
? (192.168.203.14) at b0:7b:25:19:4a:d7 [ether] on enp1s0
? (192.168.203.151) at <不完全> on enp1s0
```

**Detection Logic:**
1. If the IP has a valid MAC address (e.g., `b0:7b:25:19:4a:d7`) → **Alive**
2. If the IP shows `<incomplete>` or `<不完全>` (locale-dependent) → **Dead**
3. If the IP is entirely absent from the table → **Dead**

### 3.3 Why This Bypasses Firewalls

- ARP operates at **Layer 2** (Data Link Layer), below the IP firewall.
- The monitoring server does not send any packets to the target; it simply reads its own kernel's cache.
- Windows background services (NetBIOS, mDNS, LLMNR, etc.) generate broadcast/multicast traffic that populates the ARP table passively.

### 3.4 MAC Address Validation

A valid MAC is matched with the regex pattern:

```
(?:[0-9a-fA-F]{1,2}:){5}[0-9a-fA-F]{1,2}
```

The `<incomplete>` / `<不完全>` check uses a dual-condition to handle multiple OS locales:

```python
is_incomplete = "<" in line or "incomplete" in line
```

---

## 4. Project Directory Structure

```
/home/ubuntu/Develop/Django-Ping/
├── manage.py                        # Django management entry point
├── requirements.txt                 # django>=4.2, markdown>=3.0
├── db.sqlite3                       # SQLite database
├── seed_data.py                     # Initial data seeder
├── document/                        # Generated reports
│   └── 26-06-08_01_*.md
├── classroom_ping/                  # Django project settings
│   ├── settings.py                  # INSTALLED_APPS, ROOT_URLCONF, etc.
│   ├── urls.py                      # Root URL routing
│   ├── wsgi.py
│   └── asgi.py
├── alive_check/                     # Main monitoring app
│   ├── models.py                    # Seat model (row, col, type, ip, status, last_checked)
│   ├── views.py                     # seat_map_view, reports_list_view, report_detail_view
│   ├── urls.py                      # App-level URL routing
│   ├── admin.py
│   ├── apps.py
│   ├── tests.py
│   ├── templates/
│   │   └── seat_map.html            # Cyberpunk-styled dashboard template
│   └── management/
│       └── commands/
│           └── check_arp.py         # Custom management command
└── Python-PortScan/                 # Standalone test scripts
    ├── arp_check.py                 # ARP-based alive check script
    └── ping_check.py                # TCP port scan alive check script
```

---

## 5. Component Specifications

### 5.1 Database Model — `Seat`

**File:** `alive_check/models.py`

| Field          | Type                  | Description                                |
| :------------- | :-------------------- | :----------------------------------------- |
| `row`          | IntegerField          | Grid row index                             |
| `col`          | IntegerField          | Grid column index                          |
| `type`         | CharField(10)         | `seat` or `aisle`                          |
| `ip_address`   | GenericIPAddressField | Target IP (nullable for aisles)            |
| `status`       | CharField(10)         | `alive`, `dead`, or `unknown` (default)    |
| `last_checked` | DateTimeField         | Timestamp of last status update (nullable) |

**Constraints:** `unique_together = ('row', 'col')`  
**Ordering:** `['row', 'col']`

### 5.2 Custom Management Command — `check_arp`

**File:** `alive_check/management/commands/check_arp.py`  
**Invocation:** `python manage.py check_arp`

**Algorithm:**
1. Execute `subprocess.run(["arp", "-an"], capture_output=True, text=True, check=True)` — secure, no `shell=True`.
2. Parse each line: extract IP via regex `\(([\d\.]+)\)`.
3. For each IP, check `is_incomplete` and `has_valid_mac`.
4. Build a `set()` of active IPs.
5. Query all `Seat` records with `type='seat'` and a non-null `ip_address`.
6. Compare each seat's IP against the active set and update `status` + `last_checked` via `save(update_fields=[...])`.

### 5.3 View — `seat_map_view`

**File:** `alive_check/views.py`  
**Type:** Synchronous Django view (no async, no network I/O on request).

Reads cached `Seat.status` from the database and maps `(row, col)` coordinates to template variable keys (`pc1`–`pc20`) using a static dictionary. Returns boolean values for template rendering.

### 5.4 URL Routing

| URL Path        | View            | Name       |
| :-------------- | :-------------- | :--------- |
| `/`             | `seat_map_view` | `seat_map` |
| `/alive_check/` | `seat_map_view` | `seat_map` |
| `/admin/`       | Django Admin    | —          |

### 5.5 Frontend Template — `seat_map.html`

- **Design:** Cyberpunk / terminal-style dark theme with neon glow effects.
- **Grid:** CSS Grid layout (7 columns × 6 rows) mapping physical classroom seat positions.
- **Status Rendering:** `.seat.alive` (green neon) / `.seat.dead` (red neon) CSS classes applied via Django template tags.
- **Auto-Refresh:** JavaScript `setInterval(() => location.reload(), 5000)` — refreshes every 5 seconds.

---

## 6. Cron Automation Setup

### 6.1 Crontab Entry

```bash
*/5 * * * * cd /home/ubuntu/Develop/Django-Ping && /home/ubuntu/Develop/Django-Ping/.venv/bin/python manage.py check_arp >> /home/ubuntu/Develop/Django-Ping/arp_cron.log 2>&1
```

### 6.2 Scheduling Explanation

| Field   | Value | Meaning               |
| :------ | :---- | :-------------------- |
| Minute  | `*/5` | Every 5 minutes       |
| Hour    | `*`   | Every hour            |
| Day     | `*`   | Every day             |
| Month   | `*`   | Every month           |
| Weekday | `*`   | Every day of the week |

### 6.3 Management Commands

```bash
crontab -e          # Edit cron configuration
crontab -l          # Verify registered jobs
tail -f arp_cron.log  # Monitor execution logsPlease analyze the current project state and execute the following two tasks. Ensure that all generated files strictly follow our new file naming rule: `YY-mm-dd_[sequence number]_TITLE.md` inside the `document/` directory.

**Task 1: Generate Current System Specification Document**
- Inspect the current project files and configuration.
- Write a detailed system specification document covering the overall architecture, how it bypasses Windows Firewall using the Linux ARP cache (`arp -an`), the Django custom management command details, and the system `cron` automation setup.
- Save this file as: `26-06-08_02_Python-PortScan_Current_Specification.md` inside the `document/` directory.

**Task 2: Perform an Automated Operation Test & Generate Report**
- Execute an operational test (e.g., manually run the management command or test the endpoint status) to ensure the backend integration is functioning flawlessly.
- Document the execution results, target status, and verification success.
- Save this file as: `26-06-08_03_Operation_Test_Report.md` inside the `document/` directory.

Please let me know once both documents are successfully generated and saved!
```

---

## 7. Standalone Test Scripts (Python-PortScan)

### 7.1 `arp_check.py` — ARP Cache Method (Working)

Standalone script that checks if `192.168.203.14` is alive by reading the ARP cache. Returns `"Alive"` or `"Dead"`. This is the reference implementation that was integrated into the Django management command.

### 7.2 `ping_check.py` — TCP Port Scan Method (Blocked)

Standalone script that attempts a TCP connection to port 135 (RPC) with a 1-second timeout. This method was tested and confirmed to be blocked by the target's firewall, returning `"Dead"` for live hosts. Kept for reference.
