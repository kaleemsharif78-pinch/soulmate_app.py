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
#  CONFIG & DUAL LANGUAGE MAPPING
# ─────────────────────────────────────────────────────────────
DB_PATH    = "soulmate_online.db"
BRAND      = "#6B3FA0"          # deep lavender
BRAND_DARK = "#4A2370"
GOLD       = "#C9A84C"
LAVENDER   = "#EDE7F6"
SOFT       = "#F7F3FD"
MUTED      = "#7B6FA0"

# Format: (Database Key, English Label, Urdu Label)
SECTIONS = {
    "📋 Personal Details | ذاتی تفصیلات": [
        ("name",               "Full Name *", "پورا نام *"),
        ("gender_dob",         "Gender / Date of Birth", "جنس / تاریخ پیدائش"),
        ("age_height_weight",  "Age / Height / Weight", "عمر / قد / وزن"),
        ("complexion_marital", "Complexion / Marital Status", "رنگت / ازدواجی حیثیت"),
        ("tongue_blood",       "Mother Tongue / Blood Group", "مادری زبان / بلڈ گروپ"),
        ("disability",         "Physical Disability (if any)", "جسمانی معذوری (اگر کوئی ہو)"),
    ],
    "🕌 Religious Background | مذہبی پس منظر": [
        ("religion_sect", "Religion / Sect / Maslak", "مذہب / فرقہ / مسلک"),
        ("caste_clan",    "Caste / Zaat / Clan", "ذات / برادری"),
    ],
    "🎓 Education & Profession | تعلیم اور پیشہ": [
        ("education",         "Highest Qualification / Field", "اعلیٰ تعلیم / شعبہ"),
        ("occupation_income", "Current Occupation / Income", "موجودہ پیشہ / آمدنی"),
    ],
    "👨‍👩‍👧 Family Details | خاندان کی تفصیلات": [
        ("father_details", "Father's Name & Occupation", "والد کا نام اور پیشہ"),
        ("mother_details", "Mother's Name & Occupation", "والدہ کا نام اور پیشہ"),
        ("siblings",       "Total Brothers / Sisters", "کل بھائی / بہنیں"),
        ("hometown",       "Native Place (Hometown)", "آبائی شہر"),
    ],
    "📍 Contact & Location | رابطہ اور پتہ": [
        ("address", "Current City & Address", "موجودہ شہر اور پتہ"),
        ("contact", "Contact Numbers *", "رابطہ نمبر *"),
    ],
    "💍 Partner Expectations | جیون ساتھی سے توقعات": [
        ("partner_age_height", "Required Age & Height", "مطلوبہ عمر اور قد"),
        ("partner_edu_city",   "Required Qualification & City", "مطلوبہ تعلیم اور شہر"),
        ("partner_other",      "Other Requirements", "دیگر ضروریات / شرائط"),
    ],
}

ALL_KEYS = [k for pairs in SECTIONS.values() for k, _, _ in pairs]
DB_COLS  = ALL_KEYS  # Same English keys maintained in database configuration

# ─────────────────────────────────────────────────────────────
#  DATABASE MANAGEMENT
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
        for col, defn in [
            ("photo",      "BLOB"),
            ("biodata_id", "TEXT"),
            ("created_at", "TEXT DEFAULT (datetime('now','localtime'))"),
            ("status",     "TEXT DEFAULT 'Active'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass

        rows = conn.execute(
            "SELECT id FROM profiles WHERE biodata_id IS NULL OR biodata_id = ''"
        ).fetchall()
        for (rid,) in rows:
            conn.execute(
                "UPDATE profiles SET biodata_id = ? WHERE id = ?",
                (_make_biodata_id(rid), rid)
            )


# ✅ FIXED: Correct function name and safe sqlite_sequence handling
def get_next_biodata_id() -> str:
    with sqlite3.connect(DB_PATH) as conn:
        try:
            row = conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name='profiles'"
            ).fetchone()
            next_rowid = (row[0] + 1) if row else 1
        except sqlite3.OperationalError:
            # sqlite_sequence doesn't exist yet on a fresh/empty database
            next_rowid = 1
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


def _safe(row, key: str, default: str = "") -> str:
    try:
        val = row[key]
        return val if val is not None else default
    except (IndexError, KeyError):
        return default


def _get_existing_cols(conn) -> set:
    return {r[1] for r in conn.execute("PRAGMA table_info(profiles)")}


def _build_select(conn) -> str:
    existing = _get_existing_cols(conn)
    desired  = ["id", "biodata_id"] + list(DB_COLS) + ["photo", "created_at", "status"]
    parts    = [c if c in existing else f"NULL AS {c}" for c in desired]
    return ", ".join(parts)


def load_profiles(search: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sel      = _build_select(conn)
        existing = _get_existing_cols(conn)
        if search.strip():
            filters, params = [], []
            for col in ("name", "contact", "biodata_id"):
                if col in existing:
                    filters.append(f"{col} LIKE ?")
                    params.append(f"%{search}%")
            where = (f" WHERE {' OR '.join(filters)}" if filters else "")
            return conn.execute(
                f"SELECT {sel} FROM profiles{where} ORDER BY id DESC", params
            ).fetchall()
        return conn.execute(
            f"SELECT {sel} FROM profiles ORDER BY id DESC"
        ).fetchall()


def fetch_profile_by_biodata_id(bid: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        existing = _get_existing_cols(conn)
        if "biodata_id" not in existing:
            return None
        sel = _build_select(conn)
        return conn.execute(
            f"SELECT {sel} FROM profiles WHERE biodata_id = ?", (bid,)
        ).fetchone()


def update_status(pid: int, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE profiles SET status = ? WHERE id = ?", (status, pid))


def delete_profile(pid: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (pid,))

# ─────────────────────────────────────────────────────────────
#  PDF GENERATION (Shows BOTH English and Urdu labels side-by-side)
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

    photo_el = Paragraph("<font color='#aaaaaa'>[ No Photo ]</font>", value_s)
    if photo_bytes:
        try:
            img_io = io.BytesIO(photo_bytes)
            pil = PILImage.open(img_io)
            if pil.mode in ("RGBA", "LA", "P") or (pil.mode == 'P' and 'transparency' in pil.info):
                pil = pil.convert("RGB")
            pil.thumbnail((95, 115))
            w, h  = pil.size
            buf2  = io.BytesIO()
            pil.save(buf2, format="JPEG", quality=95)
            buf2.seek(0)
            photo_el = RLImage(buf2, width=w, height=h)
        except Exception:
            pass

    header_left = [
        Paragraph("SOULMATE SELECT", title_s),
        Paragraph("Proprietor: Farheena Amjad", sub_s),
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

    story = [ht, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(BRAND), spaceAfter=6)]

    for sec_title, pairs in SECTIONS.items():
        story.append(Paragraph(sec_title, section_s))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#d8cce8"), spaceAfter=2))

        rows = []
        for key, label_en, label_ur in pairs:
            val = str(data.get(key, "")).strip()
            clean_en = label_en.rstrip(" *")
            clean_ur = label_ur.rstrip(" *")
            combined_label = f"{clean_en} / {clean_ur}"
            rows.append([
                Paragraph(combined_label + ":", label_s),
                Paragraph(val or "─────────────────────", value_s),
            ])

        t = Table(rows, colWidths=[210, 305])
        t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.3, colors.HexColor("#e8e0f0")),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#faf8fd"), colors.white]),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c5b8e0"), spaceAfter=6))
    footer_text = "Thank you for registering with Soulmate Select.  |  This document is private and confidential."
    if biodata_id:
        footer_text += f"  |  Biodata ID: {biodata_id}"
    story.append(Paragraph(footer_text, footer_s))

    doc.build(story)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG & CUSTOM CSS WITH URDU DIALECT SUPPORT
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Soulmate Select",
    page_icon="💍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Initialize database on startup
init_db()

css_style = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@400;500;600&family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

  html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
  }}
  .stApp {{
    background: linear-gradient(160deg, #f0eafa 0%, #e8dff5 40%, #ddd3f0 100%);
    min-height: 100vh;
  }}

  /* Header Banner */
  .ss-banner {{
    background: linear-gradient(135deg, {BRAND_DARK} 0%, {BRAND} 60%, #8B5CC4 100%);
    border-radius: 20px;
    padding: 36px 40px 30px;
    text-align: center;
    margin-bottom: 32px;
    box-shadow: 0 12px 40px rgba(74,35,112,0.35);
  }}
  .ss-banner h1 {{
    font-family: 'Cormorant Garamond', serif;
    font-size: 48px;
    font-weight: 700;
    color: {GOLD} !important;
    letter-spacing: 4px;
    margin: 0 0 6px;
  }}
  .ss-banner p {{
    color: rgba(255,255,255,0.85) !important;
    font-size: 14px;
    font-weight: 500;
  }}

  /* Section Headers */
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
  }}

  /* Bilingual Input Helpers styling */
  .label-container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    margin-bottom: 4px;
  }}
  .label-en {{
    font-size: 13px;
    font-weight: 600;
    color: {BRAND_DARK};
  }}
  .label-ur {{
    font-family: 'Noto Nastaliq Urdu', serif;
    font-size: 12px;
    color: {BRAND};
    direction: rtl;
  }}

  .stTextInput > div > div > input {{
    background: rgba(255,255,255,0.9) !important;
    border: 1.5px solid #d4c4ee !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    color: #2d1f45 !important;
  }}

  div.stButton > button:first-child {{
    background: linear-gradient(135deg, {BRAND} 0%, {BRAND_DARK} 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    padding: 14px 32px !important;
    border-radius: 14px !important;
    border: none !important;
    width: 100% !important;
    box-shadow: 0 6px 20px rgba(74,35,112,0.35) !important;
  }}
  div.stDownloadButton > button {{
    background: linear-gradient(135deg, {GOLD} 0%, #a8822a 100%) !important;
    color: #2d1f45 !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 13px 28px !important;
    border-radius: 14px !important;
    border: none !important;
    width: 100% !important;
  }}

  .ss-record-row {{
    background: rgba(255,255,255,0.8);
    border: 1px solid #e0d5f0;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
  }}
  .ss-record-name {{ font-weight: 600; color: {BRAND_DARK}; font-size: 15px; }}
  .ss-record-meta {{ font-size: 12px; color: {MUTED}; margin-top: 2px; }}
  .status-active   {{ background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-matched  {{ background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-closed   {{ background:#fce4ec; color:#c62828; border:1px solid #ef9a9a; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .status-on-hold  {{ background:#fff8e1; color:#e65100; border:1px solid #ffcc80; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }}
  .tracker-card {{ background: rgba(255,255,255,0.85); border: 1px solid #ddd3f0; border-radius: 16px; padding: 16px 20px; margin-bottom: 12px; }}
  .tracker-id {{ font-family: monospace; font-size: 13px; font-weight: 700; color: {BRAND}; background: {LAVENDER}; padding: 3px 10px; border-radius: 8px; display: inline-block; }}
  .tracker-name {{ font-size: 16px; font-weight: 700; color: {BRAND_DARK}; }}
  .tracker-meta {{ font-size: 12px; color: {MUTED}; margin-top: 3px; }}
  .tracker-date {{ font-size: 11px; color: #aaa; margin-top: 4px; }}
</style>
"""
st.markdown(css_style, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  HEADER BANNER RENDER
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="ss-banner">
  <div class="gem">💍</div>
  <h1>SOULMATE SELECT</h1>
  <p>PROPRIETOR: FARHEENA AMJAD &nbsp;·&nbsp; PREMIUM MATRIMONIAL DATABASE SYSTEM</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  TABS VIEW SYSTEM
# ─────────────────────────────────────────────────────────────
tab_form, tab_records, tab_tracker = st.tabs([
    "✚  New Biodata / نیا بائیو ڈیٹا",
    "🔍  View Records / ریکارڈز دیکھیں",
    "🪪  ID Tracker / آئی ڈی ٹریکر",
])

# ==============================================
#  TAB 1 — BILINGUAL BIODATA ENTRY FORM
# ==============================================
with tab_form:
    preview_id = get_next_biodata_id()
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.7); border: 2px dashed {BRAND}; border-radius: 14px; padding: 14px 20px; margin-bottom: 18px;">
        <div class="label-container">
            <span class="label-en">🪪 Biodata ID that will be assigned</span>
            <span class="label-ur">آئی ڈی جو تفویض کی جائے گی</span>
        </div>
        <div style="font-size: 20px; font-weight: 700; color: {BRAND_DARK}; letter-spacing: 2px;">{preview_id}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ss-section">📸 Profile Photo | پروفائل تصویر</div>', unsafe_allow_html=True)
    uploaded_photo = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="uploader_photo")
    if uploaded_photo:
        col_img, col_tip = st.columns([1, 3])
        with col_img:
            st.image(uploaded_photo, width=120)
        with col_tip:
            st.info("✅ Photo uploaded successfully. / تصویر کامیابی سے اپ لوڈ ہو گئی۔")

    field_values = {}
    for section_title, pairs in SECTIONS.items():
        st.markdown(f'<div class="ss-section">{section_title}</div>', unsafe_allow_html=True)

        if len(pairs) >= 4:
            left, right = st.columns(2)
            for i, (key, label_en, label_ur) in enumerate(pairs):
                col = left if i % 2 == 0 else right
                with col:
                    st.markdown(f"""
                    <div class="label-container">
                        <span class="label-en">{label_en}</span>
                        <span class="label-ur">{label_ur}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    field_values[key] = st.text_input("", label_visibility="collapsed", key=f"form_{key}")
        else:
            for key, label_en, label_ur in pairs:
                st.markdown(f"""
                <div class="label-container">
                    <span class="label-en">{label_en}</span>
                    <span class="label-ur">{label_ur}</span>
                </div>
                """, unsafe_allow_html=True)
                field_values[key] = st.text_input("", label_visibility="collapsed", key=f"form_{key}")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("💾  Save Record & Generate PDF / محفوظ کریں", key="main_save_btn"):
        errors = []
        if not field_values.get("name", "").strip():
            errors.append("Full Name is required. / پورا نام درج کرنا لازمی ہے۔")
        if not field_values.get("contact", "").strip():
            errors.append("Contact Number is required. / رابطہ نمبر درج کرنا لازمی ہے۔")

        if errors:
            for err in errors:
                st.error(f"⚠️ {err}")
        else:
            photo_bytes = uploaded_photo.read() if uploaded_photo else None
            try:
                pid, biodata_id = save_profile(field_values, photo_bytes)
                pdf_buf = generate_pdf(field_values, photo_bytes, biodata_id)

                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#f3e5ff,#ede0fa); border:1px solid #c8a8e8; border-radius:14px; padding:18px 22px; margin:10px 0;">
                  <div style="font-size:13px;color:{MUTED};font-weight:600;margin-bottom:4px;">✅ Record saved successfully! / ریکارڈ محفوظ کر لیا گیا ہے!</div>
                  <div style="font-size:22px;font-weight:800;color:{BRAND_DARK};letter-spacing:2px;">{biodata_id}</div>
                </div>
                """, unsafe_allow_html=True)

                st.download_button(
                    label="📥  Download Biodata PDF / پی ڈی ایف ڈاؤن لوڈ کریں",
                    data=pdf_buf,
                    file_name=f"Biodata_{biodata_id}_{field_values['name'].strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="download_fresh_pdf"
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ==============================================
#  TAB 2 — VIEW RECORDS
# ==============================================
with tab_records:
    st.markdown('<div class="ss-section">🔍 Search Records | ریکارڈز تلاش کریں</div>', unsafe_allow_html=True)

    search_q = st.text_input(
        "Search Placeholder",
        placeholder="e.g. Ahmed  /  0300-1234567  /  SS-2026-000001",
        label_visibility="collapsed",
        key="global_search_input"
    )
    records = load_profiles(search_q)

    if not records:
        st.info("No records found. / کوئی ریکارڈ نہیں ملا۔")
    else:
        st.markdown(f"**{len(records)} record(s) found / ریکارڈز ملے**")
        for row in records:
            with st.container():
                col_info, col_pdf, col_del = st.columns([5, 2, 1])

                bid    = _safe(row, "biodata_id") or f"#{row['id']}"
                status = _safe(row, "status", "Active")
                s_cls  = f"status-{status.lower().replace(' ','-')}"
                name   = _safe(row, "name", "—")
                gdob   = _safe(row, "gender_dob")
                cont   = _safe(row, "contact")
                rel    = _safe(row, "religion_sect")

                with col_info:
                    st.markdown(f"""
                    <div class="ss-record-row">
                      <div>
                        <span class="tracker-id">{bid}</span>
                        &nbsp;<span class="{s_cls}">{status}</span>
                        <div class="ss-record-name" style="margin-top:4px;">{name}</div>
                        <div class="ss-record-meta">
                          {gdob}{' &nbsp;·&nbsp; ' if gdob and cont else ''}{cont}{' &nbsp;·&nbsp; ' + rel if rel else ''}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_pdf:
                    data_dict = {c: _safe(row, c) for c in DB_COLS}
                    photo_b   = _safe(row, "photo") or None
                    pdf_b     = generate_pdf(data_dict, photo_b, bid)
                    st.download_button(
                        "📥 PDF",
                        data=pdf_b,
                        file_name=f"Biodata_{bid}_{name.replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['id']}"
                    )

                with col_del:
                    if st.button("🗑", key=f"del_{row['id']}", help="Delete this record"):
                        delete_profile(row["id"])
                        st.rerun()

# ==============================================
#  TAB 3 — ID TRACKER
# ==============================================
with tab_tracker:
    st.markdown('<div class="ss-section">🪪 Biodata ID Tracker | ٹریکر اور حیثیت</div>', unsafe_allow_html=True)

    st.markdown("**🔎 Look up a Biodata ID / تلاش کریں**")
    lookup_col, btn_col = st.columns([4, 1])
    with lookup_col:
        lookup_id = st.text_input("Enter ID", placeholder="SS-2026-000001", label_visibility="collapsed", key="tracker_lookup_id")
    with btn_col:
        do_lookup = st.button("Search", key="tracker_lookup_btn")

    if do_lookup and lookup_id.strip():
        found = fetch_profile_by_biodata_id(lookup_id.strip().upper())
        if found:
            f_bid     = _safe(found, "biodata_id", lookup_id.strip())
            f_status  = _safe(found, "status", "Active")
            f_name    = _safe(found, "name", "—")
            f_gdob    = _safe(found, "gender_dob")
            f_contact = _safe(found, "contact")
            f_edu     = _safe(found, "education")
            f_created = _safe(found, "created_at", "N/A")
            f_scls    = f_status.lower().replace(' ', '-')
            st.markdown(f"""
            <div class="tracker-card">
              <span class="tracker-id">{f_bid}</span>
              <span class="status-{f_scls}" style="margin-left:10px;">{f_status}</span>
              <div class="tracker-name">{f_name}</div>
              <div class="tracker-meta">{f_gdob}{' · ' if f_gdob else ''}{f_contact}{' · ' + f_edu if f_edu else ''}</div>
              <div class="tracker-date">Registered: {f_created}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"No record found for ID / کوئی ریکارڈ نہیں ملا: **{lookup_id.strip()}**")

    st.markdown("---")

    st.markdown("**✏️ Update Status for a Biodata ID / حیثیت تبدیل کریں**")
    upd_col1, upd_col2, upd_col3 = st.columns([3, 2, 1])
    with upd_col1:
        upd_id = st.text_input("Biodata ID Drop", placeholder="SS-2026-000001", label_visibility="collapsed", key="tracker_upd_id")
    with upd_col2:
        new_status = st.selectbox("Status Drop", ["Active", "Matched", "On Hold", "Closed"], label_visibility="collapsed", key="tracker_upd_status")
    with upd_col3:
        if st.button("Update", key="tracker_upd_btn"):
            target = fetch_profile_by_biodata_id(upd_id.strip().upper())
            if target:
                update_status(target["id"], new_status)
                st.success(f"✅ {upd_id.strip()} → **{new_status}**")
                st.rerun()
            else:
                st.error("ID not found. / آئی ڈی نہیں ملی۔")

    st.markdown("---")

    st.markdown("**📋 Full Biodata ID Registry | مکمل ریکارڈز رجسٹری**")
    STATUS_COLORS = {
        "Active":  ("#2e7d32", "#e8f5e9"),
        "Matched": ("#1565c0", "#e3f2fd"),
        "Closed":  ("#c62828", "#fce4ec"),
        "On Hold": ("#e65100", "#fff8e1"),
    }

    all_records = load_profiles()
    if not all_records:
        st.info("No records registered yet. / ابھی تک کوئی ریکارڈ موجود نہیں ہے۔")
    else:
        from collections import Counter
        status_counts = Counter(_safe(r, "status", "Active") for r in all_records)
        c1, c2, c3, c4 = st.columns(4)
        for col, label, icon in [(c1, "Active", "🟢"), (c2, "Matched", "🔵"), (c3, "On Hold", "🟡"), (c4, "Closed", "🔴")]:
            col.metric(f"{icon} {label}", status_counts.get(label, 0))

        st.markdown("")

        for row in all_records:
            bid     = _safe(row, "biodata_id") or f"#{row['id']}"
            status  = _safe(row, "status", "Active")
            fg, bg  = STATUS_COLORS.get(status, ("#555", "#eee"))
            created = _safe(row, "created_at", "N/A")
            name    = _safe(row, "name", "—")
            contact = _safe(row, "contact", "No contact")
            gdob    = _safe(row, "gender_dob", "N/A")
            edu     = _safe(row, "education")

            st.markdown(f"""
            <div class="tracker-card">
              <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                  <span class="tracker-id">{bid}</span>
                  <div class="tracker-name">{name}</div>
                  <div class="tracker-meta">
                    {contact}&nbsp;·&nbsp;{gdob}{' &nbsp;·&nbsp; ' + edu if edu else ''}
                  </div>
                  <div class="tracker-date">📅 Registered: {created}</div>
                </div>
                <div style="text-align:right;">
                  <span style="background:{bg}; color:{fg}; border:1px solid {fg}33; padding:5px 14px; border-radius:20px; font-size:11px; font-weight:700;">
                    {status}
                  </span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="
    margin-top: 48px;
    padding: 20px 0 10px;
    text-align: center;
    border-top: 1px solid rgba(107,63,160,0.2);
">
    <span style="
        font-family: 'Cormorant Garamond', serif;
        font-size: 13px;
        font-weight: 600;
        color: {MUTED};
        letter-spacing: 1.5px;
        text-transform: uppercase;
    ">NABA TECH BY KALEEM ULLAH SHARIF &nbsp;·&nbsp; 2026</span>
</div>
""", unsafe_allow_html=True)
