import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Database Setup
def init_db():
    conn = sqlite3.connect('soulmate_records.db')
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

# 2. Save Data & Generate Modern PDF
def save_and_export():
    data = {k: entry_vars[k].get() for k in entry_vars}
    if not data['name']:
        messagebox.showerror("Error", "Bhai, Full Name likhna zaroori hai!")
        return

    conn = sqlite3.connect('soulmate_records.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO profiles (
            name, gender_dob, age_height_weight, complexion_marital, tongue_blood, disability,
            religion_sect, caste_clan, education, occupation_income, father_details, mother_details,
            siblings, hometown, address, contact, partner_age_height, partner_edu_city, partner_other
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', list(data.values()))
    conn.commit()
    conn.close()

    # Professional 1-Page PDF Layout
    pdf_filename = f"Biodata_{data['name'].replace(' ', '_')}.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
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
    messagebox.showinfo("Success", f"Record Save ho gaya aur PDF ban gayi hai:\n{pdf_filename}")
    clear_fields()

def clear_fields():
    for var in entry_vars.values():
        var.set("")

# 3. GUI Window Setup
root = tk.Tk()
root.title("Soulmate Select - Premium Database")
root.geometry("620x700")
root.configure(bg="#f8f6fa")

banner = tk.Label(root, text="SOULMATE SELECT DATABASE SYSTEM", font=("Arial", 14, "bold"), fg="#ffffff", bg="#7030a0", pady=8)
banner.pack(fill="x")

canvas = tk.Canvas(root, bg="#f8f6fa", highlightthickness=0)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scroll_frame = tk.Frame(canvas, bg="#f8f6fa")

scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scrollbar.pack(side="right", fill="y")

fields = [
    ('name', 'Full Name'), ('gender_dob', 'Gender / Date of Birth'), 
    ('age_height_weight', 'Age / Height / Weight'), ('complexion_marital', 'Complexion / Marital Status'),
    ('tongue_blood', 'Mother Tongue / Blood Group'), ('disability', 'Physical Disability'),
    ('religion_sect', 'Religion / Sect (Maslak)'), ('caste_clan', 'Caste / Clan (Zaat)'),
    ('education', 'Highest Qualification / Field'), ('occupation_income', 'Current Occupation / Income'),
    ('father_details', "Father's Name & Occupation"), ('mother_details', "Mother's Name & Occupation"),
    ('siblings', 'Total Brothers / Sisters'), ('hometown', 'Native Place (Hometown)'),
    ('address', 'Current City & Address'), ('contact', 'Contact Numbers'),
    ('partner_age_height', 'Required Age & Height'), ('partner_edu_city', 'Required Qualification & City'),
    ('partner_other', 'Other Partner Requirements')
]
entry_vars = {k: tk.StringVar() for k, _ in fields}

for k, label_text in fields:
    row = tk.Frame(scroll_frame, bg="#f8f6fa", pady=4)
    row.pack(fill="x", padx=10)
    lbl = tk.Label(row, text=label_text, font=("Arial", 10, "bold"), anchor="w", width=25, bg="#f8f6fa", fg="#333333")
    lbl.pack(side="left")
    ent = tk.Entry(row, textvariable=entry_vars[k], font=("Arial", 10), bd=1, relief="solid")
    ent.pack(side="right", fill="x", expand=True, ipady=2)

btn_frame = tk.Frame(root, bg="#f8f6fa", pady=10)
btn_frame.pack(fill="x")
submit_btn = tk.Button(btn_frame, text="Save Record & Export PDF", font=("Arial", 11, "bold"), fg="#ffffff", bg="#7030a0", command=save_and_export, padding=5, relief="flat")
submit_btn.pack()

init_db()
root.mainloop()
