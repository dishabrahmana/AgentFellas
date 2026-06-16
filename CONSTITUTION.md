# WorkTracker AI Agent — Konstitusi Proyek

## 1. Identitas & Tujuan

**Nama Proyek:** WorkTracker AI Agent
**Tujuan:** AI Agent berbasis Telegram untuk mencatat pekerjaan (worklog) dan mengelola stakeholder beserta interaksinya. Terintegrasi dengan email dan device untuk monitoring menyeluruh.

**Tech Stack:**
- **Bahasa:** Python 3.11+
- **Bot Framework:** `python-telegram-bot` v21.x (async)
- **Database:** SQLite (dev) → PostgreSQL (prod) via SQLAlchemy 2.0
- **ORM:** SQLAlchemy 2.0 + Pydantic v2
- **AI/NLP:** DeepSeek V3 API + Gemini Flash (fallback)
- **Task Scheduler:** APScheduler
- **Async HTTP:** httpx
- **Email:** Gmail API (google-auth + google-api-python-client)
- **Hosting:** Hetzner Cloud CX22 (2GB, 1 vCPU, Ubuntu 24.04)

---

## 2. Arsitektur Sistem

```
┌──────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Telegram    │◄──▶│                  │    │  Gmail API  │
│   (Pengguna)  │    │   AI Agent Core  │◄──▶│  (Email)    │
└──────────────┘    │   (Python)        │    └─────────────┘
                    │                   │
┌──────────────┐    │  ┌─────────────┐  │
│ Mac Device   │───▶│  │  SQLite/DB  │  │
│ (launchd)    │    │  └─────────────┘  │
└──────────────┘    └──────────────────┘
```

### 2.1 Alur Data

1. **Input:** Telegram chat / Email / Device script
2. **Parser:** Intent Classification → Entity Extraction → Context Merge
3. **Aksi:** CRUD Database → Generate Response
4. **Output:** Telegram balasan / Email label / Notification

### 2.2 Intent Categories

| Intent | Trigger | Action |
|--------|---------|--------|
| `WORK_CREATE` | "lagi ngerjain fitur X" | Insert worklog |
| `WORK_UPDATE` | "task Y udah selesai" | Update status worklog |
| `WORK_STATUS` | "progress hari ini" | Query + report |
| `WORK_LIST` | "tampilkan task aktif" | List worklogs by filter |
| `STAKEHOLDER_ADD` | "tambah stakeholder Andi" | Insert stakeholder |
| `STAKEHOLDER_INFO` | "info stakeholder Budi" | Query stakeholder detail |
| `STAKEHOLDER_LIST` | "siapa aja stakeholder" | List all stakeholders |
| `INTERACTION_LOG` | "tadi rapat dengan client" | Insert interaction |
| `INTERACTION_SUM` | "ringkasan meeting Budi" | Query interaction + summary |
| `REPORT_DAILY` | "report hari ini" | Generate daily report |
| `REPORT_WEEKLY` | "report minggu ini" | Generate weekly report |
| `REMINDER_SET` | "ingatkan 3 hari lagi" | Schedule reminder |
| `ASK_QUERY` | "siapa paling sering ditemui?" | Natural language query to DB |

---

## 3. Database Schema

### 3.1 Tabel: `worklog_entries`

Menyatakan setiap pekerjaan/task yang dicatat.

| Kolom | Tipe | Default | Keterangan |
|-------|------|---------|------------|
| id | INTEGER PK | auto | Auto-increment |
| user_id | TEXT | required | Telegram user ID |
| title | TEXT | required | Judul pekerjaan |
| description | TEXT | null | Deskripsi detail |
| status | TEXT | 'in_progress' | todo \| in_progress \| done \| blocked \| cancelled |
| priority | TEXT | 'medium' | low \| medium \| high \| critical |
| start_time | DATETIME | null | Waktu mulai |
| end_time | DATETIME | null | Waktu selesai |
| estimated_hours | REAL | null | Estimasi jam |
| actual_hours | REAL | null | Realisasi jam |
| tags | TEXT (JSON) | '[]' | Array: ["dev", "bug", "frontend"] |
| stakeholder_id | INTEGER FK | null | Relasi ke stakeholders |
| created_at | DATETIME | now | Auto |
| updated_at | DATETIME | now | Auto |

### 3.2 Tabel: `stakeholders`

Menyimpan data stakeholder (client, partner, vendor, manager, dll).

| Kolom | Tipe | Default | Keterangan |
|-------|------|---------|------------|
| id | INTEGER PK | auto | Auto-increment |
| user_id | TEXT | required | Telegram user ID |
| name | TEXT | required | Nama lengkap |
| role | TEXT | null | client \| manager \| partner \| vendor \| internal \| other |
| company | TEXT | null | Nama perusahaan/instansi |
| contact_info | TEXT (JSON) | '{}' | {telegram, email, phone, linkedin} |
| notes | TEXT | null | Catatan umum |
| priority | TEXT | 'medium' | low \| medium \| high |
| is_active | BOOLEAN | 1 | Soft delete |
| created_at | DATETIME | now | Auto |
| updated_at | DATETIME | now | Auto |

### 3.3 Tabel: `interactions`

Riwayat interaksi/pertemuan dengan stakeholder.

| Kolom | Tipe | Default | Keterangan |
|-------|------|---------|------------|
| id | INTEGER PK | auto | Auto-increment |
| stakeholder_id | INTEGER FK | required | Relasi ke stakeholders |
| type | TEXT | required | meeting \| call \| email \| chat \| briefing \| other |
| title | TEXT | required | Topik |
| summary | TEXT | null | Notulensi/rangkuman |
| outcome | TEXT | null | Hasil konkret |
| action_items | TEXT (JSON) | '[]' | Array: ["follow up invoice", ...] |
| date | DATETIME | required | Tanggal interaksi |
| next_action_date | DATETIME | null | Follow-up date |
| created_at | DATETIME | now | Auto |

### 3.4 Tabel: `reminders`

Reminder dan scheduled tasks.

| Kolom | Tipe | Default | Keterangan |
|-------|------|---------|------------|
| id | INTEGER PK | auto | Auto-increment |
| user_id | TEXT | required | Telegram user ID |
| title | TEXT | required | Judul reminder |
| description | TEXT | null | Deskripsi |
| due_date | DATETIME | required | Waktu reminder |
| is_done | BOOLEAN | 0 |已完成 |
| related_type | TEXT | null | worklog \| stakeholder \| interaction |
| related_id | INTEGER | null | ID dari related_type |
| created_at | DATETIME | now | Auto |

### 3.5 Tabel: `sessions`

Menyimpan konteks percakapan user dengan AI.

| Kolom | Tipe | Default | Keterangan |
|-------|------|---------|------------|
| id | INTEGER PK | auto | Auto-increment |
| user_id | TEXT | required | Telegram user ID |
| chat_id | TEXT | required | Telegram chat ID |
| context | TEXT (JSON) | '{}' | Konteks percakapan |
| last_intent | TEXT | null | Intent terakhir |
| last_entity | TEXT (JSON) | '{}' | Entity terakhir |
| conversation_history | TEXT (JSON) | '[]' | History percakapan (max 20) |
| created_at | DATETIME | now | Auto |
| updated_at | DATETIME | now | Auto |

---

## 4. Coding Conventions

### 4.1 Struktur File & Impor

```
worktracker/
├── bot/                    # Telegram bot layer
│   ├── __init__.py
│   ├── main.py             # Entry point, dispatcher
│   ├── handlers/           # Command & message handlers
│   └── ai/                 # NLP/AI layer
├── db/                     # Database layer
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy models
│   ├── repository.py       # CRUD operations
│   └── connection.py       # Engine & session management
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── worklog_service.py
│   ├── stakeholder_service.py
│   ├── interaction_service.py
│   ├── report_service.py
│   └── reminder_service.py
├── integrations/           # External integrations
│   ├── __init__.py
│   ├── gmail_client.py     # Gmail API
│   └── device_tracker.py   # Mac device tracking
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── date_utils.py
│   ├── formatters.py
│   └── validators.py
├── config/                 # Configuration
│   ├── __init__.py
│   └── settings.py         # Pydantic settings
├── scripts/                # Deployment & maintenance
│   ├── deploy.sh
│   └── setup.sh
├── tests/                  # Unit tests
├── data/                   # SQLite file location (gitignored)
├── logs/                   # Log files (gitignored)
├── CONSTITUTION.md         # This file
├── AGENTS.md               # AI agent instructions
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

### 4.2 Python Style

- **Type hints:** WAJIB untuk semua function signature
- **Docstrings:** Google-style docstring
- **Async first:** Semua I/O pakai async/await
- **Error handling:** Gunakan custom exception classes, jangan bare `except Exception`
- **Logging:** Gunakan `structlog` atau `logging` dengan format JSON
- **Tidak ada komentar kode** kecuali sangat diperlukan (TODO, FIXME, HACK)
- **Import order:** stdlib → third-party → local

### 4.3 Database Convention

- Semua query melalui **Repository pattern** (langsung via SQLAlchemy session)
- Jangan gunakan raw SQL kecuali performa-critical
- Migration: manual via Alembic atau script SQL

### 4.4 Telegram Bot Convention

- Gunakan `python-telegram-bot` **Application** class (not Updater)
- Handler registration via `application.add_handler()`
- Command handler untuk user explicit intent
- Message handler + AI fallback untuk natural language
- Setiap handler harus return Response (str) atau None (untuk lanjut)

---

## 5. Deployment & Operasi

### 5.1 Server

- **Provider:** Hetzner Cloud CX22 (€3.49/bulan)
- **OS:** Ubuntu 24.04 LTS
- **Akses:** SSH dengan key-based auth
- **User:** `worktracker` (non-root, with sudo)

### 5.2 Deployment

```bash
# Setup awal (sekali)
ssh worktracker@<ip>
git clone <repo> ~/worktracker
cd ~/worktracker
./scripts/setup.sh

# Deploy update
./scripts/deploy.sh
```

`setup.sh` akan:
1. Install Python 3.11, pip, venv
2. Setup systemd service
3. Setup logrotate
4. Setup .env dari vault

`deploy.sh` akan:
1. Git pull
2. Activate venv
3. `pip install -r requirements.txt`
4. `systemctl restart worktracker`

### 5.3 Systemd Service

```
[Unit]
Description=WorkTracker AI Agent
After=network.target

[Service]
Type=simple
User=worktracker
WorkingDirectory=/home/worktracker/worktracker
ExecStart=/home/worktracker/worktracker/.venv/bin/python -m bot.main
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 5.4 Monitoring

- **Logs:** `/var/log/worktracker/` — auto rotate 7 hari
- **Health check:** Bot `/health` endpoint via Telegram DM
- **Restart:** systemd auto-restart on failure

---

## 6. Aturan Bisnis & Workflow

### 6.1 Workflow Pencatatan Worklog

```
User: "lagi ngerjain fitur login"
  → AI detect intent WORK_CREATE
  → Ekstrak: title="fitur login", status=in_progress
  → Simpan ke DB
  → Balas: "📝 Oke, saya catat: **fitur login** (in_progress)"
  → Tanya: "Ada estimasi waktu atau mau assign stakeholder?"
```

```
User: "task login udah selesai"
  → AI detect intent WORK_UPDATE
  → Cari worklog aktif dengan keyword match
  → Update status → done, set end_time
  → Balas: "✅ **fitur login** sudah selesai! 🎉"
  → Hitung actual_hours = end_time - start_time
```

### 6.2 Workflow Stakeholder

```
User: "tambah stakeholder baru: Budi Santoso dari PT Maju, client"
  → AI detect STAKEHOLDER_ADD
  → Ekstrak: name="Budi Santoso", company="PT Maju", role="client"
  → Simpan ke DB
  → Balas: "👤 Stakeholder baru: **Budi Santoso** (PT Maju - client)"
```

```
User: "siapa aja stakeholder aktif?"
  → AI detect STAKEHOLDER_LIST
  → Query semua stakeholder
  → Format + balas
```

### 6.3 Aturan Duplikasi

- **Worklog duplikat:** Jika title + status sama dan beda < 1 jam → merge/update
- **Stakeholder duplikat:** Jika name + company sama → return existing, kasih opsi update
- **Interaction duplikat:** Jika stakeholder_id + date + title sama → update instead of insert

### 6.4 Aturan Reminder

- Reminder otomatis di-check setiap 60 detik oleh APScheduler
- Yang due dalam 5 menit → kirim notifikasi ke Telegram
- User bisa snooze (tunda 1 jam) atau done

---

## 7. API Integrasi

### 7.1 DeepSeek V3 API

- **Endpoint:** `https://api.deepseek.com/v1/chat/completions`
- **Model:** `deepseek-chat`
- **System Prompt:** Konteks bot + skema database
- **Rate Limit:** 200 req/min (cukup untuk personal)
- **Biaya:** ~$0.5–1.5/bulan untuk pemakaian normal

### 7.2 Gmail API

- **Auth:** OAuth 2.0 dengan `gmail.readonly` + `gmail.modify`
- **Polling:** Setiap 60 detik via APScheduler
- **Filter:** Hanya email yang tidak dibaca (UNREAD) + label WAJIB follow-up
- **Parser:** Subject → intent, Body → entity extraction

### 7.3 Telegram Bot API

- **Token:** Dari @BotFather
- **Mode:** Polling (sederhana, cocok untuk single user)
- **Webhook:** Optional jika pakai domain/SSL

---

## 8. Environment Variables

Semua konfigurasi via environment variables, didefinisikan di `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Ya | - | Token dari @BotFather |
| `TELEGRAM_USER_ID` | Ya | - | User ID pemilik bot |
| `DEEPSEEK_API_KEY` | Ya | - | API key DeepSeek |
| `DEEPSEEK_API_URL` | Tidak | https://api.deepseek.com/v1 | Base URL DeepSeek |
| `GEMINI_API_KEY` | Tidak | - | API key Gemini (fallback) |
| `DATABASE_URL` | Tidak | sqlite+aiosqlite:///data/worktracker.db | DB connection |
| `LOG_LEVEL` | Tidak | INFO | Logging level |
| `LOG_DIR` | Tidak | ./logs | Directory log |
| `GMAIL_CREDENTIALS_FILE` | Tidak | - | Path ke Gmail OAuth JSON |
| `DEVICE_TOKEN` | Tidak | - | Token untuk device auth |
| `TZ` | Tidak | Asia/Jakarta | Timezone |
| `ADMIN_IDS` | Tidak | - | Comma-separated admin Telegram IDs |

---

## 9. Changelog

### 2026-06-16 — Fitur Prioritas Tinggi

| Perubahan | Detail |
|-----------|--------|
| **Export CSV** | `/export` — export semua worklog ke file CSV |
| **Edit Worklog** | `/work_edit <id> <field=value>` — edit field worklog individual |
| **Delete Worklog** | `/work_delete <id>` — hapus worklog permanent |
| **Search** | `/search <keyword>` — cari worklog & stakeholder berdasarkan keyword |
| **Missing handlers** | 4 command handler baru: work_status, stakeholder_info, remind, ask |
| **Missing intents** | 3 intent handler: STAKEHOLDER_INFO, INTERACTION_SUM, ASK_QUERY |
| **Scheduler** | APScheduler integration untuk reminder check tiap 60 detik + Gmail polling |
| **Gmail fix** | Wrapping sync Google API calls dengan `asyncio.to_thread()` untuk non-blocking |

### 2026-06-15 — Inisialisasi Proyek

| Perubahan | Detail |
|-----------|--------|
| **Struktur** | Setup folder `worktracker/` dengan arsitektur modular |
| **Konstitusi** | `CONSTITUTION.md` — dokumentasi arsitektur & aturan main |
| **AGENTS.md** | `AGENTS.md` — instruksi untuk AI agent di project ini |
| **Database** | 5 tabel: worklog_entries, stakeholders, interactions, reminders, sessions |
| **Telegram Bot** | Boilerplate bot dengan command & AI fallback |
| **AI Layer** | Intent classifier + entity extractor via DeepSeek V3 |
| **Services** | CRUD untuk worklog, stakeholder, interaction, report, reminder |
| **Integrasi** | Gmail API client + device tracker placeholder |
| **Deploy** | Dockerfile, docker-compose, systemd service script |
