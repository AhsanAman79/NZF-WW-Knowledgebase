# Ablagestruktur PRM Wissensdatenbank

**Zweck**: Kuratierte Ablage durch PRMs, lesbar und verarbeitbar durch KI-Agenten  
**Stand**: 29.04.2026 | **Status**: Entwurf

---

## Struktur

```
{branch}/{stream}/{partner}/{PREFIX}_{beschreibung}[-{datum}].md
```

Vier Ebenen: Branch → Stream → Partner → Datei.

---

## Ordner

### Ebene 1: Branch

| Ordner | Branch |
|--------|--------|
| `infrastructure/` | Infrastructure |
| `transportation/` | Transportation |
| `group/` | Group |
| `_einheit/` | PRM-Einheit intern, branch-übergreifend |

### Ebene 2: Stream (innerhalb eines Branch)

Beispiel für Branch **Group**:

| Ordner | Stream |
|--------|--------|
| `group/get/` | CIO DB Konzern / Konzernleitung |
| `group/hr/` | H-Ressort (Personal) |
| `group/finance/` | F-Ressort (Finanzen, Beschaffung) |

Für Infrastructure und Transportation analog — Streams werden dort von den jeweiligen Branch-Teams definiert.

Jeder Stream hat einen `_stream/`-Ordner für Dokumente, die den gesamten Stream betreffen (One-Pager, Budgetplanung, Betreuungsstruktur).

### Ebene 3: Partner

Ein Ordner pro betreutem Partner. Benennung: **Kurzname in Kleinbuchstaben**, Bindestriche statt Leerzeichen.

Beispiele (Branch Group, Stream GET):
```
group/get/bev/
group/get/db-mc/
group/get/db-museum/
group/get/ee-konzernentwicklung/
```

---

## Dokumentenklassen (Prefix)

| Prefix | Klasse | Wann verwenden |
|--------|--------|----------------|
| `BRF` | Briefing | Vorbereitung für GF-/Vorstandstermin |
| `DBR` | Debriefing | Nachbereitung, Ergebnisse, Follow-ups |
| `SRM` | Service Review | Jahresgespräch, Quartalsgespräch, regelmäßiger Review |
| `PRO` | Protokoll | Meeting-Mitschrift, Board-Protokoll |
| `INS` | Insight | One-Pager, Partner Insight, kompakte Übersicht |
| `ANA` | Analyse | Auswertung, Bewertung, VDS-Analyse |
| `STR` | Strategie | Account-Strategie, Positionspapier, Zielbild |
| `ANG` | Angebot | Angebotspräsentation, Leistungsbeschreibung |
| `PRJ` | Projekt | Projektsteckbrief, Vorstudie, Statusbericht |
| `PRZ` | Prozess | Ablaufbeschreibung, Verfahren, Workflow |
| `GOV` | Governance | Richtlinie, Konzernregelung, Policy |
| `ORG` | Organisation | Stakeholderliste, Betreuungsstruktur, Teamregeln |
| `DAT` | Daten | Tabellenexport, Übersicht, Liste |
| `KOM` | Kommunikation | E-Mail, Anfrage, Abstimmung |
| `KZI` | KZI | Kundenzufriedenheitsindex-Fragebogen |

---

## Dateinamen

```
{PREFIX}_{beschreibung}[-{datum}].{ext}
```

**Regeln:**
- Prefix in Großbuchstaben, dann Unterstrich
- Beschreibung klein, Bindestriche als Worttrenner
- Keine Umlaute (ae, oe, ue, ss)
- Keine Leerzeichen, keine Sonderzeichen
- Datum am Ende wenn zeitbezogen (YYYY-MM oder YYYY-MM-DD)
- Keine Versionsnummern (Git übernimmt das)
- **Endung**: Originalformat beibehalten (`.pptx`, `.docx`, `.xlsx`, `.pdf`, `.md`)

**Markdown-Konvertierung:**  
Ein täglicher Agent konvertiert alle Nicht-Markdown-Dateien automatisch in `.md`. Die Markdown-Version wird neben dem Original abgelegt — gleicher Name, nur mit `.md`-Endung.

```
group/get/bev/
├── BRF_jahresgespraech-2025-11-27.pptx    ← Original (vom PRM abgelegt)
├── BRF_jahresgespraech-2025-11-27.md      ← Automatisch generiert (Agent)
├── SRM_service-review-2025-11.pptx
└── SRM_service-review-2025-11.md
```

Dateien die direkt als `.md` abgelegt werden, bekommen keine zweite Version.

**Beispiele:**
```
BRF_niedbal-2025-11-24.pptx
BRF_niedbal-2025-11-24.md          ← generiert
SRM_jahresgespraech-2025-11.docx
SRM_jahresgespraech-2025-11.md     ← generiert
INS_one-pager-get.md               ← direkt als Markdown abgelegt, keine Konvertierung
DAT_budgetplanung-kl-plr25.xlsx
DAT_budgetplanung-kl-plr25.md     ← generiert
GOV_ril-0057-leistungsaustausch.pdf
GOV_ril-0057-leistungsaustausch.md ← generiert
```

---

## Vollständiges Beispiel

```
knowledge-base/
│
├── group/
│   ├── get/
│   │   ├── _stream/
│   │   │   ├── INS_one-pager-get.md
│   │   │   ├── ORG_betreuungsstruktur-2025-08.md
│   │   │   └── DAT_budgetplanung-kl-plr25.md
│   │   │
│   │   ├── bev/
│   │   │   ├── BRF_jahresgespraech-2025-11-27.md
│   │   │   └── SRM_service-review-2025-11.md
│   │   │
│   │   ├── ee-konzernentwicklung/
│   │   │   ├── BRF_niedbal-2025-11-24.md
│   │   │   └── DBR_niedbal-2025-11.md
│   │   │
│   │   └── db-mc/
│   │       └── PRZ_negativbescheid-2026-01.md
│   │
│   ├── hr/
│   │   ├── _stream/
│   │   │   ├── INS_one-pager-hr.md
│   │   │   └── ORG_accounts-hr-2025-10.md
│   │   │
│   │   └── h-ressort/
│   │       ├── PRO_it-board-2026-02.md
│   │       └── STR_zielbild-h.md
│   │
│   ├── finance/
│   │   ├── _stream/
│   │   │   └── INS_one-pager-finance.md
│   │   │
│   │   └── beschaffung/
│   │       └── PRJ_vorstudie-audit-2025-08.md
│   │
│   └── cto/
│       └── db-systemtechnik/
│           └── STR_mini-account-strategie-2023.md
│
├── infrastructure/
│   └── ...                          # Streams und Partner analog
│
├── transportation/
│   └── ...                          # Streams und Partner analog
│
└── _einheit/
    ├── GOV_ril-0057-leistungsaustausch.md
    ├── GOV_berechtigungspruefung-2025.md
    ├── PRZ_insourcingverzicht-ablauf-2026-02.md
    ├── INS_partner-insights-group-2026.md
    ├── ORG_teamregeln-kommunikation-2025-07.md
    ├── ORG_kompetenzmatrix-2025-02.md
    ├── ORG_partnerzuordnung-2025-08.md
    └── ORG_stakeholderliste-betreuungsstruktur.md
```

---

## Wo lege ich was ab?

| Situation | Ablageort |
|-----------|-----------|
| Briefing für Termin mit Partner X | `{branch}/{stream}/{partner}/BRF_...` |
| One-Pager für den gesamten Stream | `{branch}/{stream}/_stream/INS_...` |
| Richtlinie, die konzernweit gilt | `_einheit/GOV_...` |
| PRM-Teamregeln, Partnerzuordnung | `_einheit/ORG_...` |
| Partner Insights (alle Branches) | `_einheit/INS_...` |
| KZI-Fragebogen | `{branch}/{stream}/{partner}/KZI_...` |
| Budget/Planung eines Streams | `{branch}/{stream}/_stream/DAT_...` |

---