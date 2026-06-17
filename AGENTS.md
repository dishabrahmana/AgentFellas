# WorkTracker AI Agent — Instruksi untuk AI Agent

## Cara Membaca Project Ini

1. **CONSTITUTION.md** adalah sumber kebenaran utama — baca ini dulu sebelum menyentuh kode apa pun
2. **AGENTS.md** adalah file ini — instruksi khusus untuk AI agent
3. Semua konfigurasi ada di `config/settings.py`
4. Semua model database ada di `db/models.py`
5. Semua CRUD ada di `db/repository.py`
6. Handler Telegram ada di `bot/handlers/`
7. AI/NLP logic ada di `bot/ai/`
8. Business logic ada di `services/`

## Aturan Umum untuk AI Agent

1. **JANGAN** mengubah CONSTITUTION.md kecuali user meminta perubahan arsitektur
2. **JANGAN** mengubah AGENTS.md kecuali user meminta
3. **JANGAN** menambah komentar kode (tidak ada komentar di codebase ini)
4. **WAJIB** baca CONSTITUTION.md dulu sebelum melakukan perubahan apa pun
5. **WAJIB** update konstituen jika ada perubahan arsitektur/database/skema

## Keyword untuk Menemukan Kode yang Relevan

| Yang Dicari | Cari di |
|-------------|---------|
| Intent classification | `bot/ai/classifier.py` |
| Entity extraction | `bot/ai/extractor.py` |
| Command handler | `bot/handlers/commands.py` |
| AI fallback handler | `bot/handlers/messages.py` |
| Worklog CRUD | `services/worklog_service.py` |
| Stakeholder CRUD | `services/stakeholder_service.py` |
| Database model | `db/models.py` |
| Repository | `db/repository.py` |
| Gmail integration | `integrations/gmail_client.py` |
| Settings | `config/settings.py` |

## Saat Ada Error/Issue

1. Cek logs: `journalctl -u worktracker -n 50 --no-pager`
2. Cek file CONFIGURATION.md (jika user update environment)
3. Cek isi database: jalankan `worktracker/scripts/db_inspect.py`
4. Jangan asal restart — baca error log dulu

## Saat User Minta Fitur Baru

1. Baca CONSTITUTION.md — pastikan fitur sesuai arsitektur
2. Cari kode yang mirip di codebase untuk dijadikan referensi
3. Buat perubahan, pastikan type hints benar
4. Update CONSTITUTION.md jika ada perubahan arsitektur

## Konvensi Respons

- Respons ke user dalam Bahasa Indonesia
- Respons dari AI agent harus informatif, langsung ke inti
- Jangan ajak diskusi panjang — langsung eksekusi

## Riwayat Perubahan oleh AI Agent

### 2026-06-17 — Google Drive/Sheets/Docs Integration
- `integrations/google_drive_client.py` — client baru untuk baca Google Sheets, Docs, dan Drive via API
- Gmail OAuth scopes diperluas: +drive.readonly, +spreadsheets.readonly, +documents.readonly
- Google URL auto-detection di `messages.py` — kalau user kirim link Google Docs/Sheets, bot otomatis baca dan tampilkan isinya
- `/gdoc <url>` — command manual untuk baca Google Docs/Sheets
- `device_tracker.py` — baca active browser tab (Chrome/Safari/Arc) dengan URL

### 2026-06-16 — AI Personality Upgrade: Teman Curhat + Mentor
- System prompt di `bot/ai/llm_client.py` diubah total — bot sekarang punya 3 peran: teman curhat (emotional intelligence), asisten pribadi (proaktif), mentor (saran & insight dari pengetahuan DeepSeek)
- Temperature 0.7 → 0.8 (lebih natural, variatif)
- Max tokens 800 → 1200 (respons lebih panjang untuk percakapan mendalam)

### 2026-06-16 — JSON Parser Fix + History Consistency
- `_parse_response()` di `llm_client.py` — ganti regex `\{.*\}` dengan `json.JSONDecoder.raw_decode()` untuk handle braces di dalam teks respons
- Conversation history di `messages.py` — sekarang simpan FULL JSON result (bukan cuma teks) biar LLM konsisten format outputnya

### 2026-06-16 — Fitur Prioritas Tinggi
- `/export` — Export worklog ke CSV
- `/work_edit` — Edit field worklog individual (title, description, status, priority, estimated_hours)
- `/work_delete` — Hapus worklog permanent
- `/search` — Cari worklog & stakeholder berdasarkan keyword
- Bug fix: Gmail client async wrapping (`.execute()` via `asyncio.to_thread()`)
- APScheduler integration: reminder check tiap 60 detik + Gmail polling tiap 120 detik
- 3 missing intent handlers: STAKEHOLDER_INFO, INTERACTION_SUM, ASK_QUERY
- 4 missing command handlers: work_status, stakeholder_info, remind, ask
- Help text update mencakup semua command baru
- Railway deployment + environment variable configuration
