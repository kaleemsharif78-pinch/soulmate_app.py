import streamlit as st
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

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
            partner_age_height TEXT, partner_edu_city TEXT, partner_other TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. PDF Generation Function
def generate_pdf(data):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=colors.HexColor('#7030a0'), alignment=1, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#495057'), alignment=1, spaceAfter=12)
    section_style = ParagraphStyle('Section', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#7030a0'), spaceBefore=8, spaceAfter=4)
    label_style = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#343a40'))
    value_style = ParagraphStyle('Value', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#495057'))

    story.append(Paragraph("SOULMATE SELECT", title_style))
    story.append(Paragraph("Proprietor: Farheena Amjad | MATRIMONIAL BIODATA FORM", subtitle_style))

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

# 3. Streamlit Web GUI Layout
st.set_page_config(page_title="Soulmate Select Database", page_icon="💍", layout="centered")

st.markdown("<h1 style='text-align: center; color: #7030a0;'>SOULMATE SELECT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #495057; font-weight: bold;'>Proprietor: Farheena Amjad | Database System</p>", unsafe_allow_html=True)

# YAHAN ERROR THA - FIXED: hr() ko divider() mein badal diya
st.divider()

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
                siblings, hometown, address, contact, partner_age_height, partner_edu_city, partner_other
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', list(form_data.values()))
        conn.commit()
        conn.close()
        
        st.success("Record Online Database mein mahfuse ho gaya hai!")
        pdf_file = generate_pdf(form_data)
        
        st.download_button(
            label="📥 Download Professional Biodata PDF",
            data=pdf_file,
            file_name=f"Biodata_{name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )
