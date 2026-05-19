import streamlit as st
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image as RLImage, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
import io
from PIL import Image as PILImage

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
DB_PATH    = "soulmate_online.db"
BRAND      = "#6B3FA0"          # deep lavender
BRAND_DARK = "#4A2370"
GOLD       = "#C9A84C"
LAVENDER   = "#EDE7F6"
SOFT       = "#F7F3FD"
MUTED      = "#7B6FA0"

SECTIONS = {
    "📋 Personal Details": [
        ("name",               "Full Name *"),
        ("gender_dob",         "Gender / Date of Birth"),
        ("age_height_weight",  "Age / Height / Weight"),
        ("complexion_marital", "Complexion / Marital Status"),
        ("tongue_blood",       "Mother Tongue / Blood Group"),
        ("disability",         "Physical Disability (if any)"),
    ],
    "🕌 Religious Background": [
        ("religion_sect", "Religion / Sect / Maslak"),
        ("caste_clan",    "Caste / Zaat / Clan"),
    ],
    "🎓 Education & Profession": [
        ("education",         "Highest Qualification / Field"),
        ("occupation_income", "Current Occupation / Income"),
    ],
    "👨‍👩‍👧 Family Details": [
        ("father_details", "Father's Name & Occupation"),
        ("mother_details", "Mother's Name & Occupation"),
        ("siblings",       "Total Brothers / Sisters"),
        ("hometown",       "Native Place (Hometown)"),
    ],
    "📍 Contact & Location": [
        ("address", "Current City & Address"),
        ("contact", "Contact Numbers *"),
    ],
    "💍 Partner Expectations": [
        ("partner_age_height", "Required Age & Height"),
        ("partner_edu_city",   "Required Qualification & City"),
        ("partner_other",      "Other Requirements"),
    ],
}

ALL_KEYS = [k for pairs in SECTIONS.values() for k, _ in pairs]
DB_COLS  = ALL_KEYS  # same order used for INSERT

# ─────────────────────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────────────────────
def _make_biodata_id(row_id: int) -> str:
    """Generate a human-readable unique ID: SS-YYYY-XXXXXX"""
    import datetime
    year = datetime.datetime.now().year
    return f"SS-{year}-{row_id:06d}"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS profiles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                biodata_id  TEXT UNIQUE,
                {", ".join(c + " TEXT" for c in DB_COLS)},
                photo       BLOB,
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                status      TEXT DEFAULT 'Active'
            )
        ''')
        # Migrate existing DBs — add missing columns safely.
        # We use try/except per column because SQLite has no
        # "ALTER TABLE ... ADD COLUMN IF NOT EXISTS" syntax.
        for col, defn in [
            ("photo",      "BLOB"),
            ("biodata_id", "TEXT"),
            ("created_at", "TEXT DEFAULT (datetime('now','localtime'))"),
            ("status",     "TEXT DEFAULT 'Active'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # column already exists — safe to ignore

        # Back-fill biodata_id for old rows that have none
        rows = conn.execute(
            "SELECT id FROM profiles WHERE biodata_id IS NULL OR biodata_id = ''"
        ).fetchall()
        for (rid,) in rows:
            conn.execute(
                "UPDATE profiles SET biodata_id = ? WHERE id = ?",
                (_make_biodata_id(rid), rid)
            )


def get_next_biodata_id() -> str:
    """Preview what the next ID will be (before INSERT)."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='profiles'"
        ).fetchone()
        next_rowid = (row[0] + 1) if row else 1
    return _make_biodata_id(next_rowid)


def save_profile(data: dict, photo_bytes: bytes | None) -> tuple[int, str]:
    cols    = DB_COLS + ["photo"]
    values  = [data.get(c, "") for c in DB_COLS] + [photo_bytes]
    ph      = ", ".join("?" * len(cols))
    col_str = ", ".join(cols)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            f"INSERT INTO profiles ({col_str}) VALUES ({ph})", values
        )
        row_id     = cur.lastrowid
        biodata_id = _make_biodata_id(row_id)
        conn.execute(
            "UPDATE profiles SET biodata_id = ? WHERE id = ?",
            (biodata_id, row_id)
        )
    return row_id, biodata_id


def load_profiles(search: str = ""):
    q, p = "SELECT * FROM profiles", ()
    if search.strip():
        q += " WHERE name LIKE ? OR contact LIKE ? OR biodata_id LIKE ?"
        p  = (f"%{search}%", f"%{search}%", f"%{search}%")
    q += " ORDER BY id DESC"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(q, p).fetchall()


def fetch_profile_by_biodata_id(bid: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            "SELECT * FROM profiles WHERE biodata_id = ?", (bid,)
        ).fetchone()


def update_status(pid: int, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE profiles SET status = ? WHERE id = ?", (status, pid))


def delete_profile(pid: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (pid,))

# ─────────────────────────────────────────────────────────────
#  PDF GENERATION
# ─────────────────────────────────────────────────────────────
def generate_pdf(data: dict, photo_bytes: bytes | None, biodata_id: str = "") -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28
    )

    base = getSampleStyleSheet()
    mk   = lambda n, **kw: ParagraphStyle(n, parent=base["Normal"], **kw)

    title_s   = mk("T",  fontName="Helvetica-Bold", fontSize=22, leading=26,
                   textColor=colors.HexColor(BRAND_DARK), alignment=0, spaceAfter=2)
    sub_s     = mk("S",  fontName="Helvetica", fontSize=9,
                   textColor=colors.HexColor(MUTED), alignment=0, spaceAfter=3)
    id_s      = mk("ID", fontName="Helvetica-Bold", fontSize=10,
                   textColor=colors.HexColor(BRAND), alignment=0, spaceAfter=2)
    section_s = mk("H",  fontName="Helvetica-Bold", fontSize=11, leading=14,
                   textColor=colors.HexColor(BRAND_DARK), spaceBefore=12, spaceAfter=5)
    label_s   = mk("L",  fontName="Helvetica-Bold", fontSize=9,
                   textColor=colors.HexColor("#2d2d2d"))
    value_s   = mk("V",  fontName="Helvetica", fontSize=9,
                   textColor=colors.HexColor("#444444"))
    footer_s  = mk("F",  fontName="Helvetica-Oblique", fontSize=8,
                   textColor=colors.HexColor(MUTED), alignment=1)

    # ── Photo element ──
    photo_el = Paragraph(
        "<font color='#aaaaaa'>[ No Photo ]</font>", value_s
    )
    if photo_bytes:
        try:
            pil = PILImage.open(io.BytesIO(photo_bytes))
            if pil.mode in ("RGBA", "LA", "P"):
                pil = pil.convert("RGB")
            pil.thumbnail((90, 110))
            w, h  = pil.size
            buf2  = io.BytesIO()
            pil.save(buf2, format="JPEG", quality=92)
            buf2.seek(0)
            photo_el = RLImage(buf2, width=w, height=h)
        except Exception:
            pass

    # ── Header table ──
    header_left = [
        Paragraph("SOULMATE SELECT", title_s),
        Paragraph("Proprietor: Farheena Rana Amjad", sub_s),
        Paragraph("Matrimonial Biodata Form  |  All information is strictly confidential", sub_s),
    ]
    if biodata_id:
        header_left.append(Paragraph(f"Biodata ID: {biodata_id}", id_s))
    ht = Table([[header_left, photo_el]], colWidths=[400, 110])
    ht.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1,  0),  "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story = [ht, HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor(BRAND), spaceAfter=6)]

    # ── Sections ──
    for sec_title, pairs in SECTIONS.items():
        # Strip emoji from title for cleaner PDF
        clean_title = sec_title.split(" ", 1)[-1]
        story.append(Paragraph(clean_title, section_s))
        story.append(HRFlowable(width="100%", thickness=0.4,
                                 color=colors.HexColor("#d8cce8"), spaceAfter=2))

        rows = []
        for key, label in pairs:
            val = data.get(key, "").strip()
            rows.append([
                Paragraph(label.rstrip(" *") + ":", label_s),
                Paragraph(val or "─────────────────────", value_s),
            ])

        t = Table(rows, colWidths=[175, 340])
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#e8e0f0")),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1),
             [colors.HexColor("#faf8fd"), colors.white]),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#c5b8e0"), spaceAfter=6))
    footer_text = "Thank you for registering with Soulmate Select.  |  This document is private and confidential."
    if biodata_id:
        footer_text += f"  |  Biodata ID: {biodata_id}"
    story.append(Paragraph(footer_text, footer_s))

    doc.build(story)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG  &  CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Soulmate Select",
    page_icon="💍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@400;500;600&display=swap');

  /* ── Global ── */
  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
  }}
  .stApp {{
    background: linear-gradient(160deg, #f0eafa 0%, #e8dff5 40%, #ddd3f0 100%);
    min-height: 100vh;
  }}

  /* ── Header Banner ── */
  .ss-banner {{
    background: linear-gradient(135deg, {BRAND_DARK} 0%, {BRAND} 60%, #8B5CC4 100%);
    border-radius: 20px;
    padding: 36px 40px 30px;
    text-align: center;
    margin-bottom: 32px;
    box-shadow: 0 12px 40px rgba(74,35,112,0.35), inset 0 1px 0 rgba(255,255,255,0.15);
    position: relative;
    overflow: hidden;
  }}
  .ss-banner::before {{
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
  }}
  .ss-banner::after {{
    content: '';
    position: absolute;
    bottom: -40px; left: -40px;
    width: 140px; height: 140px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
  }}
  .ss-banner h1 {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 48px;
    font-weight: 700;
    color: {GOLD} !important;
    letter-spacing: 4px;
    margin: 0 0 6px;
    text-shadow: 0 2px 12px rgba(0,0,0,0.4);
  }}
  .ss-banner p {{
    color: rgba(255,255,255,0.85) !important;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 1px;
    margin: 0;
  }}
  .ss-banner .gem {{ font-size: 22px; }}

  /* ── Section Headers ── */
  .ss-section {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 20px;
    font-weight: 600;
    color: {BRAND_DARK};
    background: linear-gradient(90deg, rgba(107,63,160,0.08) 0%, transparent 100%);
    border-left: 4px solid {GOLD};
    padding: 10px 16px;
    border-radius: 0 10px 10px 0;
    margin: 28px 0 12px;
    letter-spacing: 0.5px;
  }}

  /* ── Inputs ── */
  .stTextInput > div > div > input,
  .stTextArea > div > div > textarea {{
    background: rgba(255,255,255,0.9) !important;
    border: 1.5px solid #d4c4ee !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    color: #2d1f45 !important;
    box-shadow: 0 2px 8px rgba(107,63,160,0.06), inset 0 1px 3px rgba(0,0,0,0.03) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
  }}
  .stTextInput > div > div > input:focus,
  .stTextArea > div > div > textarea:focus {{
    border-color: {BRAND} !important;
    box-shadow: 0 0 0 3px rgba(107,63,160,0.15) !important;
  }}

  /* ── Labels ── */
  .stTextInput label, .stTextArea label, .stFileUploader label {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: {BRAND_DARK} !important;
    letter-spacing: 0.3px;
  }}

  /* ── Primary Button ── */
  div.stButton > button:first-child {{
    background: linear-gradient(135deg, {BRAND} 0%, {BRAND_DARK} 100%) !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    padding: 14px 32px !important;
    border-radius: 14px !important;
    border: none !important;
    width: 100% !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 6px 20px rgba(74,35,112,0.35) !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
  }}
  div.stButton > button:first-child:hover {{
    box-shadow: 0 10px 28px rgba(74,35,112,0.45) !important;
    transform: translateY(-1px) !important;
  }}

  /* ── Download Button ── */
  div.stDownloadButton > button {{
    background: linear-gradient(135deg, {GOLD} 0%, #a8822a 100%) !important;
    color: #2d1f45 !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 13px 28px !important;
    border-radius: 14px !important;
    border: none !important;
    width: 100% !important;
    box-shadow: 0 6px 18px rgba(180,140,40,0.35) !important;
  }}

  /* ── File uploader ── */
  .stFileUploader > div {{
    background: rgba(255,255,255,0.75) !important;
    border: 2px dashed #b89ed4 !important;
    border-radius: 14px !important;
    padding: 18px !important;
    transition: border-color 0.2s !important;
  }}
  .stFileUploader > div:hover {{
    border-color: {BRAND} !important;
  }}

  /* ── Alerts ── */
  .stSuccess {{
    background: rgba(107,63,160,0.08) !important;
    border: 1px solid #b89ed4 !important;
    border-radius: 12px !important;
  }}
  .stError {{
    border-radius: 12px !important;
  }}

  /* ── Divider ── */
  hr {{
    border-color: rgba(107,63,160,0.15) !important;
    margin: 24px 0 !important;
  }}

  /* ── Records table ── */
  .ss-record-row {{
    background: rgba(255,255,255,0.8);
    border: 1px solid #e0d5f0;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .ss-record-name {{
    font-weight: 600;
    color: {BRAND_DARK};
    font-size: 15px;
  }}
  .ss-record-meta {{
    font-size: 12px;
    color: {MUTED};
    margin-top: 2px;
  }}

  /* ── Tab styling ── */
  .stTabs [data-baseweb="tab-list"] {{
    background: rgba(255,255,255,0.5);
    border-radius: 14px;
    padding: 4px;
    gap: 4px;
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    color: {MUTED} !important;
    padding: 8px 20px !important;
  }}
  .stTabs [aria-selected="true"] {{
    background: {BRAND} !important;
    color: white !important;
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="ss-banner">
  <div class="gem">💍</div>
  <h1>SOULMATE SELECT</h1>
  <p>PROPRIETOR: FARHEENA RANA AMJAD &nbsp;·&nbsp; PREMIUM MATRIMONIAL DATABASE SYSTEM</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  EXTRA CSS for ID Tracker
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  .id-badge {{
    display: inline-block;
    background: linear-gradient(135deg, {BRAND} 0%, {BRAND_DARK} 100%);
    color: white;
    font-family: 'DM Sans', sans-serif;
    font-size: 18px;
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 12px;
    letter-spacing: 2px;
    box-shadow: 0 4px 14px rgba(74,35,112,0.3);
    margin: 6px 0 16px;
  }}
  .id-preview-box {{
    background: rgba(255,255,255,0.7);
    border: 2px dashed {BRAND};
    border-radius: 14px;
    padding: 14px 20px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  .id-preview-label {{
    font-size: 12px;
    font-weight: 600;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .id-preview-value {{
    font-size: 20px;
    font-weight: 700;
    color: {BRAND_DARK};
    letter-spacing: 2px;
  }}
  .status-active   {{ background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-matched  {{ background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-closed   {{ background:#fce4ec; color:#c62828; border:1px solid #ef9a9a; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-on-hold  {{ background:#fff8e1; color:#e65100; border:1px solid #ffcc80; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .tracker-card {{
    background: rgba(255,255,255,0.85);
    border: 1px solid #ddd3f0;
    border-radius: 16px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 2px 10px rgba(107,63,160,0.07);
  }}
  .tracker-id {{
    font-family: monospace;
    font-size: 13px;
    font-weight: 700;
    color: {BRAND};
    background: {LAVENDER};
    padding: 3px 10px;
    border-radius: 8px;
    display: inline-block;
    margin-bottom: 6px;
  }}
  .tracker-name {{
    font-size: 16px;
    font-weight: 700;
    color: {BRAND_DARK};
  }}
  .tracker-meta {{
    font-size: 12px;
    color: {MUTED};
    margin-top: 3px;
  }}
  .tracker-date {{
    font-size: 11px;
    color: #aaa;
    margin-top: 4px;
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────
tab_form, tab_records, tab_tracker = st.tabs([
    "✚  New Biodata",
    "🔍  View Records",
    "🪪  ID Tracker",
])

# ══════════════════════════════════════════════
#  TAB 1 — NEW BIODATA FORM
# ══════════════════════════════════════════════
with tab_form:

    # Preview upcoming Biodata ID
    preview_id = get_next_biodata_id()
    st.markdown(f"""
    <div class="id-preview-box">
      <div>
        <div class="id-preview-label">🪪 Biodata ID that will be assigned</div>
        <div class="id-preview-value">{preview_id}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Photo upload
    st.markdown('<div class="ss-section">📸 Profile Photo</div>', unsafe_allow_html=True)
    uploaded_photo = st.file_uploader(
        "Upload photo (JPG / PNG)", type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )
    if uploaded_photo:
        col_img, col_tip = st.columns([1, 3])
        with col_img:
            st.image(uploaded_photo, width=120)
        with col_tip:
            st.info("✅ Photo uploaded successfully. It will appear on the PDF.")

    # Form fields
    field_values: dict[str, str] = {}

    for section_title, pairs in SECTIONS.items():
        st.markdown(f'<div class="ss-section">{section_title}</div>', unsafe_allow_html=True)

        if len(pairs) >= 4:
            left, right = st.columns(2)
            for i, (key, label) in enumerate(pairs):
                col = left if i % 2 == 0 else right
                with col:
                    field_values[key] = st.text_input(label, key=key)
        else:
            for key, label in pairs:
                field_values[key] = st.text_input(label, key=key)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("💾  Save Record & Generate PDF"):
        errors = []
        if not field_values.get("name", "").strip():
            errors.append("Full Name is required.")
        if not field_values.get("contact", "").strip():
            errors.append("Contact Number is required.")

        if errors:
            for err in errors:
                st.error(f"⚠️ {err}")
        else:
            photo_bytes = uploaded_photo.read() if uploaded_photo else None
            try:
                pid, biodata_id = save_profile(field_values, photo_bytes)
                pdf_buf = generate_pdf(field_values, photo_bytes, biodata_id)

                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#f3e5ff,#ede0fa);
                     border:1px solid #c8a8e8; border-radius:14px; padding:18px 22px; margin:10px 0;">
                  <div style="font-size:13px;color:{MUTED};font-weight:600;margin-bottom:4px;">
                    ✅ Record saved successfully!
                  </div>
                  <div style="font-size:22px;font-weight:800;color:{BRAND_DARK};letter-spacing:2px;">
                    {biodata_id}
                  </div>
                  <div style="font-size:12px;color:{MUTED};margin-top:4px;">
                    Keep this Biodata ID for future reference and tracking.
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.download_button(
                    label="📥  Download Biodata PDF",
                    data=pdf_buf,
                    file_name=f"Biodata_{biodata_id}_{field_values['name'].strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ══════════════════════════════════════════════
#  TAB 2 — VIEW RECORDS
# ══════════════════════════════════════════════
with tab_records:
    st.markdown('<div class="ss-section">🔍 Search Records</div>', unsafe_allow_html=True)

    search_q = st.text_input(
        "Search by name, contact, or Biodata ID",
        placeholder="e.g. Ahmed  /  0300-1234567  /  SS-2025-000001",
        label_visibility="collapsed"
    )
    records = load_profiles(search_q)

    if not records:
        st.info("No records found.")
    else:
        st.markdown(f"**{len(records)} record(s) found**")
        st.markdown("")

        for row in records:
            with st.container():
                col_info, col_pdf, col_del = st.columns([5, 2, 1])

                bid    = row["biodata_id"] or f"#{row['id']}"
                status = row["status"] or "Active"
                s_cls  = f"status-{status.lower().replace(' ','-')}"

                with col_info:
                    st.markdown(f"""
                    <div class="ss-record-row">
                      <div>
                        <span class="tracker-id">{bid}</span>
                        &nbsp;<span class="{s_cls}">{status}</span>
                        <div class="ss-record-name" style="margin-top:4px;">{row['name'] or '—'}</div>
                        <div class="ss-record-meta">
                          {row['gender_dob'] or ''}{' &nbsp;·&nbsp; ' if row['gender_dob'] and row['contact'] else ''}{row['contact'] or ''}
                          {' &nbsp;·&nbsp; ' + row['religion_sect'] if row['religion_sect'] else ''}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_pdf:
                    data_dict = {c: row[c] for c in DB_COLS if c in row.keys()}
                    photo_b   = row["photo"] if "photo" in row.keys() else None
                    pdf_b     = generate_pdf(data_dict, photo_b, bid)
                    st.download_button(
                        "📥 PDF",
                        data=pdf_b,
                        file_name=f"Biodata_{bid}_{(row['name'] or 'record').replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['id']}"
                    )

                with col_del:
                    if st.button("🗑", key=f"del_{row['id']}", help="Delete this record"):
                        delete_profile(row["id"])
                        st.rerun()

# ══════════════════════════════════════════════
#  TAB 3 — ID TRACKER
# ══════════════════════════════════════════════
with tab_tracker:
    st.markdown('<div class="ss-section">🪪 Biodata ID Tracker</div>', unsafe_allow_html=True)

    # ── Quick ID lookup ──
    st.markdown("**🔎 Look up a Biodata ID**")
    lookup_col, btn_col = st.columns([4, 1])
    with lookup_col:
        lookup_id = st.text_input(
            "Enter Biodata ID", placeholder="SS-2025-000001",
            label_visibility="collapsed", key="lookup_id_input"
        )
    with btn_col:
        do_lookup = st.button("Search", key="lookup_btn")

    if do_lookup and lookup_id.strip():
        found = fetch_profile_by_biodata_id(lookup_id.strip().upper())
        if found:
            st.markdown(f"""
            <div class="tracker-card">
              <span class="tracker-id">{found['biodata_id']}</span>
              <span class="status-{(found['status'] or 'active').lower().replace(' ','-')}"
                    style="margin-left:10px;">{found['status'] or 'Active'}</span>
              <div class="tracker-name">{found['name'] or '—'}</div>
              <div class="tracker-meta">
                {found['gender_dob'] or ''}{' · ' if found['gender_dob'] else ''}{found['contact'] or ''}
                {' · ' + found['education'] if found['education'] else ''}
              </div>
              <div class="tracker-date">Registered: {found['created_at'] or 'N/A'}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"No record found for ID: **{lookup_id.strip()}**")

    st.markdown("---")

    # ── Status updater ──
    st.markdown("**✏️ Update Status for a Biodata ID**")
    upd_col1, upd_col2, upd_col3 = st.columns([3, 2, 1])
    with upd_col1:
        upd_id = st.text_input("Biodata ID", placeholder="SS-2025-000001",
                                label_visibility="collapsed", key="upd_id")
    with upd_col2:
        new_status = st.selectbox(
            "Status", ["Active", "Matched", "On Hold", "Closed"],
            label_visibility="collapsed", key="upd_status"
        )
    with upd_col3:
        if st.button("Update", key="upd_btn"):
            target = fetch_profile_by_biodata_id(upd_id.strip().upper())
            if target:
                update_status(target["id"], new_status)
                st.success(f"✅ {upd_id.strip()} → **{new_status}**")
                st.rerun()
            else:
                st.error("ID not found.")

    st.markdown("---")

    # ── Full ID Registry ──
    st.markdown("**📋 Full Biodata ID Registry**")

    STATUS_COLORS = {
        "Active":  ("#2e7d32", "#e8f5e9"),
        "Matched": ("#1565c0", "#e3f2fd"),
        "Closed":  ("#c62828", "#fce4ec"),
        "On Hold": ("#e65100", "#fff8e1"),
    }

    all_records = load_profiles()
    if not all_records:
        st.info("No records registered yet.")
    else:
        # Summary stats
        from collections import Counter
        status_counts = Counter(r["status"] or "Active" for r in all_records)
        c1, c2, c3, c4 = st.columns(4)
        for col, label, icon in [
            (c1, "Active",  "🟢"),
            (c2, "Matched", "🔵"),
            (c3, "On Hold", "🟡"),
            (c4, "Closed",  "🔴"),
        ]:
            count = status_counts.get(label, 0)
            col.metric(f"{icon} {label}", count)

        st.markdown("")

        for row in all_records:
            bid    = row["biodata_id"] or f"#{row['id']}"
            status = row["status"] or "Active"
            fg, bg = STATUS_COLORS.get(status, ("#555", "#eee"))
            created = row["created_at"] or "N/A"

            st.markdown(f"""
            <div class="tracker-card">
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                  <span class="tracker-id">{bid}</span>
                  <div class="tracker-name">{row['name'] or '—'}</div>
                  <div class="tracker-meta">
                    {row['contact'] or 'No contact'}&nbsp;·&nbsp;{row['gender_dob'] or 'N/A'}
                    {' &nbsp;·&nbsp; ' + row['education'] if row['education'] else ''}
                  </div>
                  <div class="tracker-date">📅 Registered: {created}</div>
                </div>
                <div style="text-align:right;">
                  <span style="background:{bg};color:{fg};border:1px solid {fg}33;
                    padding:5px 14px; border-radius:20px; font-size:12px; font-weight:700;">
                    {status}
                  </span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
