import streamlit as st
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image as PILImage

# 1. Database Setup (BLOB type added for saving photo data)
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

# 2. Modern PDF Generation Function with Photo Alignment
def generate_pdf(data, photo_bytes):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=colors.HexColor('#7030a0'), alignment=0, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#495057'), alignment=0, spaceAfter=4)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#7030a0'), spaceBefore=10, spaceAfter=4)
    label_style = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#343a40'))
    value_style = ParagraphStyle('Value', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#495057'))

    # Header and Photo Layout Construction
    header_text_block = []
    header_text_block.append(Paragraph("SOULMATE SELECT", title_style))
    header_text_block.append(Paragraph("Proprietor: Farheena Amjad | MATRIMONIAL BIODATA FORM", subtitle_style))
    
    # Handling Profile Image layout inside PDF
    photo_element = "__________________" # Default empty line if photo not available
    if photo_bytes:
        try:
            img_io = io.BytesIO(photo_bytes)
            # Maintaining aspect ratio using PIL
            pil_img = PILImage.open(img_io)
            pil_img.thumbnail((90, 110))
            img_w, img_h = pil_img.size
            
            img_data = io.BytesIO()
            pil_img.save(img_data, format='JPEG')
            img_data.seek(0)
            
            photo_element = Image(img_data, width=img_w, height=img_h)
        except:
            pass

    # Header Grid (Left text, Right photo)
    header_table_data = [[header_text_block, photo_element]]
    header_table = Table(header_table_data, colWidths=[400, 120])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
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
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#ced4da')),
        ]))
        story.append(t)

    add_pdf_section("1. Personal Details", [
        ("Full Name:", data['name']), ("Gender / Date of Birth:", data['gender_dob']),
        ("Age / Height / Weight:", data['age_height_weight']), ("Complexion / Marital Status:", data['complexion_marital']),
        ("Mother Tongue / Blood Group:", data['tongue_blood']), ("Physical Disability:", data['disability'])
    ])
    add_pdf_section("2. Religious & Family Background", [
        ("Religion / Sect (Maslak):", data['religion_sect']), ("Caste / Clan (Zaat):", data['caste_clan'])
    ])
    add_pdf_section("3. Education & Career", [
        ("Highest Qualification / Field:", data['education']), ("Current Occupation / Income:", data['occupation_income'])
    ])
    add_pdf_section("4. Family Details", [
        ("Father's Name & Occupation:", data['father_details']), ("Mother's Name & Occupation:", data['mother_details']),
        ("Total Brothers / Sisters:", data['siblings']), ("Native Place (Hometown):", data['hometown'])
    ])
    add_pdf_section("5. Contact & Location", [
        ("Current City & Address:", data['address']), ("Contact Numbers:", data['contact'])
    ])
    add_pdf_section("6. Partner Expectations", [
        ("Required Age & Height:", data['partner_age_height']), ("Required Qualification & City:", data['partner_edu_city']),
        ("Other Requirements:", data['partner_other'])
    ])

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer

# 3. Streamlit Modern Web Layout
st.set_page_config(page_title="Soulmate Select Database", page_icon="💍", layout="centered")

st.markdown("<h1 style='text-align: center; color: #7030a0;'>SOULMATE SELECT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #495057; font-weight: bold;'>Proprietor: Farheena Amjad | Database System</p>", unsafe_allow_html=True)
st.divider()

st.subheader("📸 Candidate Profile Photo")
# NEW FILE UPLOADER FOR IMAGE
uploaded_photo = st.file_uploader("Upload Profile Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_photo:
    st.image(uploaded_photo, caption="Uploaded Photo Preview", width=120)

st.subheader("1. Personal Details")
name = st.text_input("Full Name")
gender_dob = st.text_input("Gender / Date of Birth")
age_height_weight = st.text_input("Age / Height / Weight")
complexion_marital = st.text_input("Complexion / Marital Status")
tongue_blood = st.text_input("Mother Tongue / Blood Group")
disability = st.text_input("Physical Disability")

st.subheader("2. Religious & Family Background")
religion_sect = st.text_input("Religion / Sect (Maslak)")
caste_clan = st.text_input("Caste / Clan (Zaat)")

st.subheader("3. Education & Career")
education = st.text_input("Highest Qualification / Field")
occupation_income = st.text_input("Current Occupation / Income")

st.subheader("4. Family Details")
father_details = st.text_input("Father's Name & Occupation")
mother_details = st.text_input("Mother's Name & Occupation")
siblings = st.text_input("Total Brothers / Sisters")
hometown = st.text_input("Native Place (Hometown)")

st.subheader("5. Contact & Location")
address = st.text_input("Current City & Address")
contact = st.text_input("Contact Numbers")

st.subheader("6. Partner Expectations")
partner_age_height = st.text_input("Required Age & Height")
partner_edu_city = st.text_input("Required Qualification & City")
partner_other = st.text_input("Other Partner Requirements")

if st.button("Save & Process Data", type="primary"):
    if not name:
        st.error("Bhai, Full Name likhna zaroori hai!")
    else:
        # Read image data to binary format
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
        
        # Insert statement including photo BLOB
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
        
        st.success("Record Photo ke sath Online Database mein save ho gaya hai!")
        
        # PDF creation with image data pass-through
        pdf_file = generate_pdf(form_data, photo_data)
        
        st.download_button(
            label="📥 Download Professional Biodata PDF",
            data=pdf_file,
            file_name=f"Biodata_{name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
