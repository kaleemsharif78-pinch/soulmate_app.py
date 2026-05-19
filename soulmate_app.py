import streamlit as st
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage

# 1. Database Setup
def init_db():
    conn = sqlite3.connect('soulmate_online.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, gender_dob TEXT, age_height_weight TEXT, complexion_marital TEXT,
            tongue_blood TEXT, disability TEXT, religion_sect TEXT, caste_clan TEXT,
            education TEXT, occupation_income TEXT, father_details TEXT, mother_details TEXT,
            siblings TEXT, hometown TEXT, address TEXT, contact TEXT,
            partner_age_height TEXT, partner_edu_city TEXT, partner_other TEXT,
            photo BLOB
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. Modern PDF Generation Function
def generate_pdf(data, photo_bytes):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=colors.HexColor('#4A154B'), alignment=0, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#606060'), alignment=0, spaceAfter=4)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#4A154B'), spaceBefore=12, spaceAfter=6)
    label_style = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#333333'))
    value_style = ParagraphStyle('Value', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#555555'))

    # Header section
    header_text_block = []
    header_text_block.append(Paragraph("SOULMATE SELECT", title_style))
    header_text_block.append(Paragraph("Proprietor: Farheena Rana Amjad | MATRIMONIAL BIODATA FORM", subtitle_style))
    
    photo_element = "__________________"
    if photo_bytes:
        try:
            img_io = io.BytesIO(photo_bytes)
            pil_img = PILImage.open(img_io)
            pil_img.thumbnail((100, 120))
            img_w, img_h = pil_img.size
            
            img_data = io.BytesIO()
            pil_img.save(img_data, format='JPEG')
            img_data.seek(0)
            
            photo_element = Image(img_data, width=img_w, height=img_h)
        except:
            pass

    header_table_data = [[header_text_block, photo_element]]
    header_table = Table(header_table_data, colWidths=[400, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(header_table)

    def add_pdf_section(title, pairs):
        story.append(Paragraph(title, section_style))
        table_data = []
        for label, val in pairs:
            table_data.append([Paragraph(label, label_style), Paragraph(val if val else "_____________________________________", value_style)])
        t = Table(table_data, colWidths=[180, 340])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
        ]))
        story.append(t)

    add_pdf_section("1. Personal Details", [
        ("Full Name:", data['name']), ("Gender / Date of Birth:", data['gender_dob']),
        ("Age / Height / Weight:", data['age_height_weight']), ("Complexion / Marital Status:", data['complexion_marital']),
        ("Mother Tongue / Blood Group:", data['tongue_blood']), ("Physical Disability:", data['disability'])
    ])
    add_pdf_section("2. Religious Background", [
        ("Religion / Sect / Maslak:", data['religion_sect']), ("Caste / Zaat / Clan:", data['caste_clan'])
    ])
    add_pdf_section("3. Education & Profession", [
        ("Highest Qualification:", data['education']), ("Current Occupation / Income:", data['occupation_income'])
    ])
    add_pdf_section("4. Family Details", [
        ("Father's Name & Details:", data['father_details']), ("Mother's Name & Details:", data['mother_details']),
        ("Total Siblings (Brothers/Sisters):", data['siblings']), ("Native Place (Hometown):", data['hometown'])
    ])
    add_pdf_section("5. Contact & Location", [
        ("Current Address:", data['address']), ("Phone / Contact Numbers:", data['contact'])
    ])
    add_pdf_section("6. Partner Expectations", [
        ("Required Age & Height:", data['partner_age_height']), ("Required Qualification & City:", data['partner_edu_city']),
        ("Other Requirements:", data['partner_other'])
    ])

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer

# 3. Streamlit Advanced Custom CSS Styling (Premium Modern Design)
st.set_page_config(page_title="Soulmate Select Premium", page_icon="💍", layout="centered")

st.markdown("""
<style>
    /* Main Background and tone */
    .stApp {
        background: linear-gradient(135deg, #f3edf7 0%, #e5daf1 100%);
    }
    
    /* Premium 3D Header Card */
    .premium-header {
        background: linear-gradient(135deg, #4A154B 0%, #2c0b2d 100%);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0px 10px 25px rgba(74, 21, 75, 0.3), inset 0px 1px 3px rgba(255,255,255,0.3);
        margin-bottom: 25px;
        border: 2px solid #dfc3e6;
    }
    .premium-header h1 {
        color: #FFD700 !important;
        font-family: 'Arial Black', Gadget, sans-serif;
        font-size: 38px !important;
        letter-spacing: 2px;
        margin: 0;
        text-shadow: 2px 3px 6px rgba(0,0,0,0.5);
    }
    .premium-header p {
        color: #ffffff !important;
        font-size: 16px;
        font-weight: bold;
        margin-top: 8px;
        opacity: 0.9;
    }
    
    /* Subheaders Styling with Left Highlight */
    .stMarkdown h3 {
        color: #4A154B !important;
        background: #fdf8ff;
        padding: 8px 15px;
        border-left: 5px solid #FFD700;
        border-radius: 4px;
        box-shadow: 0px 3px 6px rgba(0,0,0,0.05);
        font-size: 18px !important;
        margin-top: 25px !important;
    }
    
    /* Input Boxes Modern 3D/Curved Design */
    .stTextInput>div>div>input {
        background-color: #ffffff !important;
        border: 1px solid #ced4da !important;
        border-radius: 10px !important;
        padding: 10px 15px !important;
        box-shadow: inset 0px 2px 4px rgba(0,0,0,0.05), 0px 2px 5px rgba(0,0,0,0.02) !important;
        transition: all 0.3s ease-in-out;
    }
    .stTextInput>div>div>input:focus {
        border-color: #4A154B !important;
        box-shadow: 0px 0px 8px rgba(74, 21, 75, 0.3), inset 0px 1px 2px rgba(0,0,0,0.05) !important;
    }
    
    /* Submit and Download Buttons styling */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #FFD700 0%, #e6be00 100%) !important;
        color: #4A154B !important;
        font-weight: bold !important;
        font-size: 18px !important;
        padding: 12px 30px !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0px 6px 15px rgba(230, 190, 0, 0.4), inset 0px 1px 2px rgba(255,255,255,0.5) !important;
        text-shadow: 0px 1px 1px rgba(255,255,255,0.6);
        width: 100%;
        transition: all 0.2s ease;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0px 8px 20px rgba(230, 190, 0, 0.6) !important;
    }
    div.stButton > button:first-child:active {
        transform: translateY(1px);
    }
</style>
""", unsafe_allow_html=True)

# App UI Layout with Premium HTML Header banner
st.markdown("""
<div class="premium-header">
    <h1>SOULMATE SELECT</h1>
    <p>Proprietor: Farheena Rana Amjad | Premium Matrimonial Database System</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<h3>📸 Candidate Profile Photo</h3>", unsafe_allow_html=True)
uploaded_photo = st.file_uploader("Upload Profile Photo (JPG/PNG)", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

if uploaded_photo:
    st.image(uploaded_photo, caption="Uploaded Photo Preview", width=130)

st.markdown("<h3>1. Personal Details</h3>", unsafe_allow_html=True)
name = st.text_input("Full Name")
gender_dob = st.text_input("Gender / Date of Birth")
age_height_weight = st.text_input("Age / Height / Weight")
complexion_marital = st.text_input("Complexion / Marital Status")
tongue_blood = st.text_input("Mother Tongue / Blood Group")
disability = st.text_input("Physical Disability")

st.markdown("<h3>2. Religious Background</h3>", unsafe_allow_html=True)
religion_sect = st.text_input("Religion / Sect / Maslak")
caste_clan = st.text_input("Caste / Zaat / Clan")

st.markdown("<h3>3. Education & Profession</h3>", unsafe_allow_html=True)
education = st.text_input("Highest Qualification")
occupation_income = st.text_input("Current Occupation / Income")

st.markdown("<h3>4. Family Details</h3>", unsafe_allow_html=True)
father_details = st.text_input("Father's Name & Details")
mother_details = st.text_input("Mother's Name & Details")
siblings = st.text_input("Total Siblings (Brothers/Sisters)")
hometown = st.text_input("Native Place (Hometown)")

st.markdown("<h3>5. Contact & Location</h3>", unsafe_allow_html=True)
address = st.text_input("Current Address")
contact = st.text_input("Phone / Contact Numbers")

st.markdown("<h3>6. Partner Expectations</h3>", unsafe_allow_html=True)
partner_age_height = st.text_input("Required Age & Height")
partner_edu_city = st.text_input("Required Qualification & City")
partner_other = st.text_input("Other Partner Requirements")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Save & Process Data"):
    if not name:
        st.error("Bhai, Full Name likhna zaroori hai!")
    else:
        photo_data = None
        if uploaded_photo is not None:
            photo_data = uploaded_photo.read()

        form_data = {
            'name': name, 'gender_dob': gender_dob, 'age_height_weight': age_height_weight,
            'complexion_marital': complexion_marital, 'tongue_blood': tongue_blood, 'disability': disability,
            'religion_sect': religion_sect, 'caste_clan': caste_clan, 'education': education,
            'occupation_income': occupation_income, 'father_details': father_details, 'mother_details': mother_details,
            'siblings': siblings, 'hometown': hometown, 'address': address, 'contact': contact,
            'partner_age_height': partner_age_height, 'partner_edu_city': partner_edu_city, 'partner_other': partner_other
        }
        
        conn = sqlite3.connect('soulmate_online.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO profiles (
                name, gender_dob, age_height_weight, complexion_marital, tongue_blood, disability,
                religion_sect, caste_clan, education, occupation_income, father_details, mother_details,
                siblings, hometown, address, contact, partner_age_height, partner_edu_city, partner_other, photo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', list(form_data.values()) + [photo_data])
        conn.commit()
        conn.close()
        
        st.success("✨ Record Premium Online Database mein save ho gaya hai!")
        pdf_file = generate_pdf(form_data, photo_data)
        
        st.download_button(
            label="📥 Download Professional Biodata PDF",
            data=pdf_file,
            file_name=f"Biodata_{name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
