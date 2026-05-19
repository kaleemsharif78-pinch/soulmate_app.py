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
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f'''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {", ".join(c + " TEXT" for c in DB_COLS)},
                photo BLOB
            )
        ''')
        # Migrate: add photo column if missing (existing DBs)
        existing = {r[1] for r in conn.execute("PRAGMA table_info(profiles)")}
        if "photo" not in existing:
            conn.execute("ALTER TABLE profiles ADD COLUMN photo BLOB")


def save_profile(data: dict, photo_bytes: bytes | None) -> int:
    cols   = DB_COLS + ["photo"]
    values = [data.get(c, "") for c in DB_COLS] + [photo_bytes]
    ph     = ", ".join("?" * len(cols))
    col_str = ", ".join(cols)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            f"INSERT INTO profiles ({col_str}) VALUES ({ph})", values
        )
        return cur.lastrowid


def load_profiles(search: str = ""):
    q, p = "SELECT * FROM profiles", ()
    if search.strip():
        q += " WHERE name LIKE ? OR contact LIKE ?"
        p  = (f"%{search}%", f"%{search}%")
    q += " ORDER BY id DESC"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(q, p).fetchall()


def delete_profile(pid: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM profiles WHERE id = ?", (pid,))

# ─────────────────────────────────────────────────────────────
#  PDF GENERATION
# ─────────────────────────────────────────────────────────────
def generate_pdf(data: dict, photo_bytes: bytes | None) -> io.BytesIO:
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
    story.append(Paragraph(
        "Thank you for registering with Soulmate Select. "
        "This document is private and confidential.",
        footer_s
    ))

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
#  TABS
# ─────────────────────────────────────────────────────────────
tab_form, tab_records = st.tabs(["✚  New Biodata", "🔍  View Records"])

# ══════════════════════════════════════════════
#  TAB 1 — NEW BIODATA FORM
# ══════════════════════════════════════════════
with tab_form:

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

        # Two-column layout for sections with ≥ 4 fields
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
                pid = save_profile(field_values, photo_bytes)
                pdf_buf = generate_pdf(field_values, photo_bytes)

                st.success(f"✨ Record saved successfully! (ID: {pid})")
                st.download_button(
                    label="📥  Download Biodata PDF",
                    data=pdf_buf,
                    file_name=f"Biodata_{field_values['name'].strip().replace(' ', '_')}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ══════════════════════════════════════════════
#  TAB 2 — VIEW RECORDS
# ══════════════════════════════════════════════
with tab_records:
    st.markdown('<div class="ss-section">🔍 Search Records</div>', unsafe_allow_html=True)

    search_q = st.text_input("Search by name or contact", placeholder="Type to filter…",
                              label_visibility="collapsed")
    records  = load_profiles(search_q)

    if not records:
        st.info("No records found.")
    else:
        st.markdown(f"**{len(records)} record(s) found**")
        st.markdown("")

        for row in records:
            with st.container():
                col_info, col_pdf, col_del = st.columns([5, 2, 1])

                with col_info:
                    st.markdown(f"""
                    <div class="ss-record-row">
                      <div>
                        <div class="ss-record-name">#{row['id']} — {row['name'] or '—'}</div>
                        <div class="ss-record-meta">
                          {row['gender_dob'] or ''}
                          {'&nbsp;·&nbsp;' if row['gender_dob'] and row['contact'] else ''}
                          {row['contact'] or ''}
                          {'&nbsp;·&nbsp;' if row['religion_sect'] else ''}
                          {row['religion_sect'] or ''}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_pdf:
                    data_dict = {c: row[c] for c in DB_COLS if c in row.keys()}
                    photo_b   = row["photo"] if "photo" in row.keys() else None
                    pdf_b     = generate_pdf(data_dict, photo_b)
                    st.download_button(
                        "📥 PDF",
                        data=pdf_b,
                        file_name=f"Biodata_{(row['name'] or 'record').replace(' ','_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['id']}"
                    )

                with col_del:
                    if st.button("🗑", key=f"del_{row['id']}", help="Delete this record"):
                        delete_profile(row["id"])
                        st.rerun()
