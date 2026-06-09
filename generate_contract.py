#!/usr/bin/env python3
"""
MPS Contract Generator — Web Form Version
Reads JSON from stdin, generates filled PDFs, outputs ZIP path to stdout.
Usage: echo '{"contractType":"employment",...}' | python3 generate_contract.py
"""
import json, sys, io, os, zipfile, tempfile, urllib.request
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── BRAND COLORS ──────────────────────────────────────────────
NAVY      = colors.HexColor('#1C2340')
NAVY_DK   = colors.HexColor('#0F1520')
GOLD      = colors.HexColor('#9B7E52')
CREAM     = colors.HexColor('#F5F0E8')
BLACK     = colors.HexColor('#1A1A1A')
GREY      = colors.HexColor('#555555')
GREY_LT   = colors.HexColor('#E8E8E8')
WHITE     = colors.white

PAGE_W, PAGE_H = A4
ML = 2.2 * cm
MR = 2.2 * cm
MT = 3.5 * cm
MB = 2.5 * cm
CW = PAGE_W - ML - MR  # content width

FONT_DIR  = Path('/tmp/mps_fonts')
LOGO_PATH = str(Path(__file__).parent / 'client' / 'public' / 'logo.jpg')

PLAYFAIR_REG  = 'https://fonts.gstatic.com/s/playfairdisplay/v40/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKdFvUDQ.ttf'
PLAYFAIR_BOLD = 'https://fonts.gstatic.com/s/playfairdisplay/v40/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKeiukDQ.ttf'

# ─── FONT SETUP ────────────────────────────────────────────────
_fonts_ready = False
def ensure_fonts():
    global _fonts_ready
    if _fonts_ready: return
    FONT_DIR.mkdir(exist_ok=True)

    def dl(name, url):
        p = FONT_DIR / f"{name}.ttf"
        if not p.exists():
            try: urllib.request.urlretrieve(url, p)
            except Exception as e: print(f"Warning: {name}: {e}", file=sys.stderr); return
        try: pdfmetrics.registerFont(TTFont(name, str(p)))
        except Exception: pass

    dl('Playfair',      PLAYFAIR_REG)
    dl('Playfair-Bold', PLAYFAIR_BOLD)
    for name, fpath in [
        (str(Path(__file__).parent / 'fonts' / 'NotoSansThai-Regular.ttf')),
        ('NotoThai-Bold',str(Path(__file__).parent / 'fonts' / 'NotoSansThai-Bold.ttf')),
        ('NotoMM',       str(Path(__file__).parent / 'fonts' / 'Zawgyi-One.ttf')),
        ('NotoMM-Bold',  str(Path(__file__).parent / 'fonts' / 'Zawgyi-One.ttf')),
    ]:
        try: pdfmetrics.registerFont(TTFont(name, fpath))
        except Exception: pass
    _fonts_ready = True

# ─── FONT MAPS ─────────────────────────────────────────────────
FONTS = {
    'en': {'title':'Playfair-Bold', 'head':'Helvetica-Bold', 'body':'Helvetica',     'italic':'Helvetica-Oblique'},
    'th': {'title':'NotoThai-Bold', 'head':'NotoThai-Bold',  'body':'NotoThai',      'italic':'NotoThai'},
    'my': {'title':'NotoMM-Bold',   'head':'NotoMM-Bold',    'body':'NotoMM',        'italic':'NotoMM'},
}

def make_styles(lang='en'):
    f = FONTS[lang]
    lead_body = 17 if lang != 'en' else 16
    lead_title= 30 if lang != 'en' else 26
    def S(name, **kw): return ParagraphStyle(name, **kw)
    return {
        'doc_title':  S('doc_title',  fontName=f['title'], fontSize=20, textColor=NAVY,  spaceAfter=4,  leading=lead_title, alignment=TA_LEFT),
        'doc_sub':    S('doc_sub',    fontName=f['body'],  fontSize=11, textColor=GOLD,  spaceAfter=14, leading=18,         alignment=TA_LEFT),
        'sec_head':   S('sec_head',   fontName=f['head'],  fontSize=11, textColor=NAVY,  spaceBefore=16,spaceAfter=6,       leading=18,     alignment=TA_LEFT),
        'sub_head':   S('sub_head',   fontName=f['head'],  fontSize=10, textColor=BLACK, spaceBefore=10,spaceAfter=4,       leading=16,     alignment=TA_LEFT),
        'body':       S('body',       fontName=f['body'],  fontSize=10, textColor=BLACK, spaceAfter=5,  leading=lead_body,  alignment=TA_JUSTIFY),
        'body_b':     S('body_b',     fontName=f['head'],  fontSize=10, textColor=BLACK, spaceAfter=4,  leading=lead_body,  alignment=TA_LEFT),
        'bullet':     S('bullet',     fontName=f['body'],  fontSize=10, textColor=BLACK, spaceAfter=4,  leading=lead_body,  leftIndent=20,  bulletIndent=8, alignment=TA_JUSTIFY),
        'sub_bul':    S('sub_bul',    fontName=f['body'],  fontSize=10, textColor=BLACK, spaceAfter=3,  leading=15,         leftIndent=38,  bulletIndent=26, alignment=TA_JUSTIFY),
        'note':       S('note',       fontName=f['italic'],fontSize=9,  textColor=GREY,  spaceAfter=4,  leading=14),
        'sig_lbl':    S('sig_lbl',    fontName=f['head'],  fontSize=10, textColor=BLACK, spaceAfter=2,  leading=15),
        'sig_ln':     S('sig_ln',     fontName=f['body'],  fontSize=10, textColor=BLACK, spaceAfter=12, leading=15),
        'tbl_hdr':    S('tbl_hdr',    fontName=f['head'],  fontSize=9,  textColor=WHITE, alignment=TA_CENTER, leading=14),
        'tbl_cell':   S('tbl_cell',   fontName=f['body'],  fontSize=9,  textColor=BLACK, alignment=TA_LEFT,   leading=14),
        'centered':   S('centered',   fontName=f['body'],  fontSize=10, textColor=BLACK, spaceAfter=5,  leading=16, alignment=TA_CENTER),
        'alert':      S('alert',      fontName=f['head'],  fontSize=9.5,textColor=NAVY_DK, spaceAfter=4, leading=15),
        'field_val':  S('field_val',  fontName=f['head'],  fontSize=10.5,textColor=NAVY_DK, spaceAfter=4, leading=16),
    }

# ─── PAGE DECORATOR ────────────────────────────────────────────
def page_decorator(doc_title_str):
    def decorator(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 1.8*cm, PAGE_W, 1.8*cm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, PAGE_H - 1.8*cm - 0.18*cm, PAGE_W, 0.18*cm, fill=1, stroke=0)
        canvas.setFillColor(WHITE); canvas.setFont('Helvetica-Bold', 11)
        canvas.drawString(ML, PAGE_H - 1.15*cm, "MR PROPERTY SIAM CO., LTD.")
        canvas.setFillColor(GOLD)
        canvas.circle(ML + 185, PAGE_H - 1.1*cm, 1.5, fill=1, stroke=0)
        canvas.setFont('Helvetica', 7)
        canvas.drawString(ML + 195, PAGE_H - 1.15*cm, "LUXURY COLLECTION")
        canvas.setFillColor(WHITE); canvas.setFont('Helvetica', 9)
        canvas.drawRightString(PAGE_W - MR, PAGE_H - 1.15*cm, doc_title_str.upper())
        canvas.setStrokeColor(GOLD); canvas.setLineWidth(1.0)
        canvas.line(ML, 1.8*cm, PAGE_W - MR, 1.8*cm)
        canvas.setFont('Helvetica', 7.5); canvas.setFillColor(GREY)
        canvas.drawString(ML, 1.2*cm,
            "Confidential — Mister Property Siam Co.,LTD  |  115/26 Moo 6, Bo Phut, Koh Samui, Surat Thani 84320, Thailand")
        canvas.drawRightString(PAGE_W - MR, 1.2*cm, f"Page {doc.page}")
        canvas.restoreState()
    return decorator

# ─── HELPERS ───────────────────────────────────────────────────
def hr(): return HRFlowable(width="100%", thickness=0.8, color=GOLD, spaceAfter=8, spaceBefore=4)
def sdiv(): return HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceAfter=10, spaceBefore=14)

def cream_box(text, s):
    t = Table([[Paragraph(text, s['alert'])]], colWidths=[CW - 0.4*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),CREAM),('BOX',(0,0),(-1,-1),1.5,NAVY),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    return t

def navy_box(text, s):
    t = Table([[Paragraph(text, s['alert'])]], colWidths=[CW - 0.4*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),CREAM),('BOX',(0,0),(-1,-1),2,NAVY),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    return t

def cover_logo():
    img = Image(LOGO_PATH); img.drawWidth = img.drawHeight = 5.5*cm; img.hAlign = 'LEFT'
    return img

def info_table(rows, s):
    data = [[Paragraph(k, s['body_b']), Paragraph(str(v) if v else '—', s['field_val'])] for k,v in rows]
    t = Table(data, colWidths=[4.8*cm, CW - 5.3*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F0EDE6')),
        ('LINEBELOW',(0,0),(-1,-2),0.5,GREY_LT),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('BOX',(0,0),(-1,-1),1.2,NAVY)]))
    return t

def sig_block(s, lang='en'):
    labels = {
        'en': ("On Behalf of Employer","Employee","Authorised Signatory — Mister Property Siam Co.,LTD",
               "Employee Name:","ID / Passport:","Position:","Date:","Witness (if required):"),
        'th': ("ในนามของนายจ้าง","ลูกจ้าง","ผู้มีอำนาจลงนาม — Mister Property Siam Co.,LTD",
               "ชื่อลูกจ้าง:","เลขที่บัตร / หนังสือเดินทาง:","ตำแหน่ง:","วันที่:","พยาน (หากจำเป็น):"),
        'my': ("အလုပ်ရှင်ကိုယ်စား","ဝန်ထမ်း","လုပ်ပိုင်ခွင့်ရှိသောလက်မှတ် — Mister Property Siam Co.,LTD",
               "ဝန်ထမ်းအမည် :","မှတ်ပုံတင်/ပတ်စ်ပို့ :","ရာထူး :","ရက်စွဲ :","သက်သေ (လိုအပ်ပါက) :"),
    }
    L = labels[lang]
    story = [Spacer(1, 1.2*cm), sdiv(), Paragraph(L[0] if lang == 'en' else L[0], s['sec_head']), Spacer(1, 0.5*cm)]
    sig_data = [
        [Paragraph(L[0], s['body_b']), Paragraph(L[1], s['body_b'])],
        [Spacer(1, 1.8*cm), Spacer(1, 1.8*cm)],
        [HRFlowable(width="100%", thickness=0.5, color=BLACK),
         HRFlowable(width="100%", thickness=0.5, color=BLACK)],
        [Paragraph(L[2], s['note']), Paragraph(f"{L[3]} ___________________________", s['note'])],
        [Spacer(1, 0.3*cm), Spacer(1, 0.3*cm)],
        [Paragraph(f"Name: _______________________________", s['sig_ln']),
         Paragraph(f"{L[4]} ______________________", s['sig_ln'])],
        [Paragraph(f"Position: ____________________________", s['sig_ln']),
         Paragraph(f"{L[6]} ______________________________", s['sig_ln'])],
        [Paragraph(f"{L[6]} _______________________________", s['sig_ln']), Paragraph("", s['sig_ln'])],
    ]
    t = Table(sig_data, colWidths=[(CW - 0.5*cm)/2]*2, hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),
        ('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"{L[7]} __________________________ {L[6]} ______________", s['body']))
    return story

def make_pdf(header_title, story_fn, lang):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB)
    s = make_styles(lang)
    story = story_fn(s)
    doc.build(story, onFirstPage=page_decorator(header_title), onLaterPages=page_decorator(header_title))
    return buf.getvalue()

# ─── UTILITIES ─────────────────────────────────────────────────
def fmt_date(d):
    if not d: return "__________"
    try:
        dt = datetime.strptime(d[:10], '%Y-%m-%d')
        return dt.strftime('%d %B %Y')
    except: return d

def fmt_salary(sal):
    """Safely format salary as comma-separated integer string."""
    if sal in ('', '__________', None, 0): return '__________'
    try: return f"{int(float(sal)):,}"
    except (TypeError, ValueError): return str(sal)

def dept_name(dept, lang):
    names = {
        'en': {'housekeeping':'Housekeeping','office':'Office / Management','pool_garden_handyman':'Pool, Garden & Handyman'},
        'th': {'housekeeping':'แผนกแม่บ้าน','office':'สำนักงาน / ฝ่ายจัดการ','pool_garden_handyman':'สระว่ายน้ำ สวน และช่าง'},
        'my': {'housekeeping':'အိမ်ရှင်မဌာန','office':'ရုံး / စီမံခန့်ခွဲမှုဌာန','pool_garden_handyman':'ရေကူးကန်၊ ဥယျာဉ် နှင့် ဆောက်လုပ်ရေးဌာန'},
    }
    return names.get(lang, names['en']).get(dept, dept)

# ─── DUTY LABELS ───────────────────────────────────────────────
DUTY_LABELS = {
    # Housekeeping
    'welcome_setup':         {'en':'Welcome setup & villa preparation','th':'การเตรียมวิลล่าต้อนรับแขก','my':'ဧည့်သည်ကြိုဆိုရေး ပြင်ဆင်မှု'},
    'villa_inspection':      {'en':'Villa inspection & quality checks','th':'การตรวจสอบวิลล่าและควบคุมคุณภาพ','my':'ဗိလာ စစ်ဆေးမှုနှင့် အရည်အသွေး'},
    'guest_laundry':         {'en':'Guest laundry service','th':'บริการซักรีดสำหรับแขก','my':'ဧည့်သည် အဝတ်လျော်ဝန်ဆောင်မှု'},
    'ironing':               {'en':'Ironing & garment care','th':'รีดเสื้อผ้าและดูแลเครื่องแต่งกาย','my':'အဝတ်ချောင်းဖွာနှင့် အဝတ်အစားပြုစု'},
    'inventory_mgmt':        {'en':'Inventory management & restocking','th':'การจัดการสต็อกสินค้าและเติม','my':'ပစ္စည်းစာရင်းနှင့် အဖြည့်'},
    'train_staff':           {'en':'Training new housekeeping staff','th':'ฝึกอบรมพนักงานแม่บ้านใหม่','my':'မြိုတ်သစ်ဝန်ထမ်းများ သင်ကြားပေးမှု'},
    'multi_property_hk':     {'en':'Multi-property rotation (housekeeping)','th':'หมุนเวียนหลายทรัพย์สิน','my':'မြေပိုင်အများ ကွင်းဆင်းမှု'},
    'night_checkout_clean':  {'en':'Night/late check-out cleaning','th':'ทำความสะอาดหลัง check-out ดึก','my':'ည/နောက်ကျ check-out ဆဲဆေးမှု'},
    # Office / Management
    'airport_transfer':      {'en':'Airport transfer coordination','th':'ประสานรับส่งสนามบิน','my':'လေဆိပ်သယ်ပို့ ညှိနှိုင်းမှု'},
    'concierge_booking':     {'en':'Concierge & booking management','th':'บริการ concierge และจัดการการจอง','my':'Concierge နှင့် ကြိုတင်မှာကြားမှု'},
    'checkin_checkout':      {'en':'Check-in / check-out management','th':'จัดการ check-in / check-out','my':'Check-in / check-out စီမံမှု'},
    'maintenance_sched':     {'en':'Maintenance scheduling','th':'กำหนดตารางซ่อมบำรุง','my':'ပြုပြင်ထိန်းသိမ်းမှု ဇယားဆွဲ'},
    'vendor_mgmt':           {'en':'Vendor management','th':'จัดการผู้จัดจำหน่าย','my':'ကုန်ပစ္စည်းပေးသွင်းသူ စီမံ'},
    'social_media':          {'en':'Social media monitoring','th':'ติดตามสื่อสังคมออนไลน์','my':'လူမှုကွန်ရက် ကြည့်ရှုခြင်း'},
    'platform_mgmt':         {'en':'Platform management (Airbnb / Booking.com)','th':'จัดการแพลตฟอร์ม (Airbnb/Booking.com)','my':'Platform စီမံမှု (Airbnb/Booking.com)'},
    'revenue_mgmt':          {'en':'Revenue management & dynamic pricing','th':'บริหารรายได้และกำหนดราคาไดนามิก','my':'ဝင်ငွေစီမံမှုနှင့် ဈေးနှုန်းညှိ'},
    'staff_scheduling':      {'en':'Staff scheduling & rotas','th':'จัดตารางพนักงานและเวร','my':'ဝန်ထမ်းဇယားနှင့် တာဝန်ကြိမ်'},
    'petty_cash_mgmt':       {'en':'Petty cash management','th':'จัดการเงินสดย่อย','my':'ငွေသေးစိတ် စီမံမှု'},
    # Pool / Garden / Handyman
    'chemical_testing':      {'en':'Chemical testing & water balance','th':'ทดสอบสารเคมีและปรับสมดุลน้ำ','my':'ဓာတုပစ္စည်း စစ်ဆေးမှုနှင့် ရေချိန်ညှိ'},
    'equipment_maint':       {'en':'Equipment maintenance (pumps, filters)','th':'ซ่อมบำรุงอุปกรณ์ (ปั๊ม, ตัวกรอง)','my':'ကိရိယာပြုပြင် (ပန့်၊ စစ်စစ်)'},
    'jacuzzi_spa':           {'en':'Jacuzzi / spa maintenance','th':'ดูแลแจ็คคูซี่และสปา','my':'Jacuzzi / spa ထိန်းသိမ်း'},
    'lawn_landscaping':      {'en':'Lawn mowing & landscaping','th':'ตัดหญ้าและจัดภูมิทัศน์','my':'မြက်ခုတ်နှင့် ဥယျာဉ်ဒီဇိုင်း'},
    'pest_control':          {'en':'Pest control & prevention','th':'กำจัดและป้องกันแมลง','my':'ကောင်ပိုးပြောင်းဆေး'},
    'minor_plumbing':        {'en':'Minor plumbing repairs','th':'ซ่อมแซมระบบประปาเล็กน้อย','my':'ရေပိုက်ပြုပြင်'},
    'minor_electrical':      {'en':'Minor electrical work','th':'งานไฟฟ้าเล็กน้อย','my':'လျှပ်စစ်လုပ်ငန်းငယ်'},
    'ac_filter':             {'en':'AC filter cleaning & maintenance','th':'ทำความสะอาดและดูแล filter แอร์','my':'အဲယားကွန်း filter သန့်ရှင်း'},
    'painting':              {'en':'Painting & touch-ups','th':'ทาสีและแก้ไขผิวงาน','my':'ဆေးသုတ်မှုနှင့် ပြင်ဆင်'},
    'vehicle_cleaning':      {'en':'Vehicle cleaning & upkeep','th':'ทำความสะอาดและดูแลยานพาหนะ','my':'ယာဉ် သန့်ရှင်းနှင့် ထိန်းသိမ်း'},
    'multi_property_pg':     {'en':'Multi-property rotation','th':'หมุนเวียนหลายทรัพย์สิน','my':'မြေပိုင်အများ ကွင်းဆင်းမှု'},
    'emergency_oncall_pg':   {'en':'Emergency on-call duty','th':'เวรฉุกเฉิน (on-call)','my':'အရေးပေါ် on-call တာဝန်'},
    'supervise_train_pg':    {'en':'Supervise & train team members','th':'ดูแลและฝึกอบรมสมาชิกทีม','my':'အဖွဲ့ဝင်များ ကြီးကြပ်/သင်ကြားပေး'},
    # Complicated functions
    'night_shift_rotation':  {'en':'Night shift rotation (adds night-work clause)','th':'กะกลางคืนหมุนเวียน (เพิ่มข้อการทำงานกลางคืน)','my':'ညဆိုင်းကြိမ်ကူး (ညအလုပ်ဘောင် ထည့်)'},
    'on_call_avail':         {'en':'On-call availability (outside normal hours)','th':'พร้อมรับเวร (นอกเวลางานปกติ)','my':'On-call ရနိုင်မှု (ပုံမှန်အချိန်ပြင်ပ)'},
    'multi_property_cover':  {'en':'Multi-property coverage','th':'ดูแลหลายทรัพย์สิน','my':'မြေပိုင်အများ ကာကွယ်မှု'},
    'training_resp':         {'en':'Training responsibility for other staff','th':'รับผิดชอบฝึกอบรมพนักงานอื่น','my':'အခြားဝန်ထမ်းများ သင်ကြားပေးရသော တာဝန်'},
    'petty_cash_handling':   {'en':'Petty cash handling','th':'จัดการเงินสดย่อย','my':'ငွေသေးစိတ် ကိုင်တွယ်မှု'},
}

# ─── ENGLISH EMPLOYMENT AGREEMENT ─────────────────────────────
def build_ea_en(data):
    emp = data.get('employee', {})
    dept_raw = data.get('department', 'housekeeping')
    dept = dept_name(dept_raw, 'en')
    pos = emp.get('position', '__________')
    sal = emp.get('salary', '__________')
    sd  = fmt_date(emp.get('startDate', ''))
    fname  = emp.get('fullName', '__________')
    nick   = emp.get('nickname', '')
    nat    = emp.get('nationality', '__________')
    idno   = emp.get('idPassport', '__________')
    addr   = emp.get('address', '__________')
    phone  = emp.get('phone', '__________')
    mgd    = emp.get('managedProperties', [])  # [{propertyName, commissionRate}]
    nick_str = f' (known as \"<b>{nick}</b>\")' if nick else ''

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("Employment Agreement", s['doc_title']))
        story.append(Paragraph("Mister Property Siam Co.,LTD  |  Tax ID: 0845566025288", s['doc_sub']))
        story.append(hr()); story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            "This Employment Agreement (<b>\"Agreement\"</b>) is entered into on the last date signed below, between:", s['body']))
        story.append(Spacer(1, 0.4*cm))

        party = [
            [Paragraph("Employer:", s['body_b']),
             Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>Tax ID: 0845566025288<br/>"
                       "Registered address: 115/26 Moo 6, Bo Phut, Koh Samui, Surat Thani 84320, Thailand<br/>"
                       "Email: finance@mrpropertysiam.com", s['body'])],
            [Paragraph("Employee:", s['body_b']),
             Paragraph(f"<b>Full Name:</b> {fname}{nick_str}<br/><b>Nationality:</b> {nat}<br/>"
                       f"<b>ID / Passport No.:</b> {idno}<br/><b>Address:</b> {addr}<br/>"
                       f"<b>Phone:</b> {phone}<br/><b>Department:</b> {dept}", s['body'])],
        ]
        pt = Table(party, colWidths=[3*cm, CW - 3.5*cm])
        pt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(pt)
        story.append(Paragraph("The parties agree as follows:", s['body']))

        # 1 Position
        story.append(sdiv()); story.append(Paragraph("1.  Position and Duties", s['sec_head']))
        for t in [
            f"1.1  The Employee is engaged as <b>{pos}</b> in the <b>{dept}</b> Department."
                + ((" <br/><b>Additional Scope of Work:</b> " + " &nbsp;·&nbsp; ".join(f"<b>{r}</b>" for r in (emp.get('additionalRoles') or []))) if emp.get('additionalRoles') else ""),
            "1.2  The Employee shall perform the duties set out in <b>Annex A</b> and any other reasonable duties assigned by the Employer.",
            "1.3  The Employee shall devote full working time to the Employer and shall not engage in any other employment or business without prior written consent.",
            "1.4  The Employee shall perform all duties diligently, honestly and in accordance with the Employer's policies and lawful instructions.",
            "1.5  All owner relationships, guest relationships, booking channels, supplier relationships and business contacts developed during employment are the sole property of the Employer.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 2 Start Date
        story.append(sdiv()); story.append(Paragraph("2.  Commencement Date", s['sec_head']))
        story.append(Paragraph(f"2.1  Employment commences on: <b>{sd}</b>", s['body']))
        story.append(Paragraph("2.2  This contract is: ☐ Indefinite term   ☐ Fixed term, ending: __________", s['body']))

        # 3 Probation
        story.append(sdiv()); story.append(Paragraph("3.  Probation Period", s['sec_head']))
        story.append(navy_box(
            "IMPORTANT (accountant-reviewed): Probation is 120 days. Note per Section 118 LPA: severance applies once employee completes 120 consecutive days — confirm or terminate before end of probation period if not extending. "
            "Day 120 triggers mandatory severance obligations under Section 17(3) of the Labour Protection Act B.E. 2541.", s))
        story.append(Spacer(1, 0.3*cm))
        for t in [
            "3.1  The Employee shall serve a probation period of <b>one hundred and twenty (120) days</b> from the Commencement Date (Labour Protection Act B.E. 2541, Section 17).",
            "3.2  During probation, either party may terminate by giving advance written notice of not less than one (1) pay cycle, or by payment in lieu, per Section 17(3) LPA. Severance under Section 118 applies only if the employee has completed 120 consecutive days of service.",
            "3.3  The Employer will evaluate performance before probation ends and will confirm employment, extend by written agreement, or terminate.",
            "3.4  Passing probation does not guarantee continued employment beyond the terms of this Agreement.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 4 Compensation
        story.append(sdiv()); story.append(Paragraph("4.  Compensation and Benefits", s['sec_head']))
        story.append(Paragraph(f"4.1  Base Monthly Salary: <b>THB {fmt_salary(sal)}</b>, paid by the last working day of each month by bank transfer.", s['body']))
        # Managed properties / commission (managers and revenue roles)
        if mgd:
            story.append(Paragraph("4.1.1  Property Management Responsibilities &amp; Commission."
                " The Employee shall manage and be responsible for the following properties. "
                "A dedicated management pack percentage (separate from and in addition to base salary) shall be paid as specified:", s['body']))
            tbl_data = [[Paragraph('<b>Property / Villa</b>', s['body_b']),
                         Paragraph('<b>Mgmt Pack %</b>', s['body_b']),
                         Paragraph('<b>Cut of Pack %</b>', s['body_b']),
                         Paragraph('<b>Effective %</b>', s['body_b'])]]
            for p in mgd:
                pack = p.get('managementPackRate', '') or ''
                cut  = p.get('commissionRate', '') or ''
                try:
                    eff = f"{round(float(pack)*float(cut)/100,1)}&nbsp;%" if pack != '' and cut != '' else '—'
                except Exception:
                    eff = '—'
                tbl_data.append([
                    Paragraph(p.get('propertyName',''), s['body']),
                    Paragraph(f"{pack}&nbsp;%" if pack != '' else '—', s['body']),
                    Paragraph(f"{cut}&nbsp;%" if cut != '' else '—', s['body']),
                    Paragraph(eff, s['body']),
                ])
            mt = Table(tbl_data, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
            mt.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
                ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
                ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            story.append(mt); story.append(Spacer(1,0.3*cm))
        story.append(Paragraph(
            "4.2  Overtime. Overtime requires prior written authorisation (including via LINE or WhatsApp) and shall be compensated as follows:", s['body']))
        for item in [
            "(a) Overtime on regular workdays: not less than 1.5× the hourly rate;",
            "(b) Work on rest days (normal hours): not less than 1× the daily wage (daily-rate employees) or additional to the monthly salary (monthly-rate employees);",
            "(c) Overtime on rest days and public holidays: not less than 3× the hourly rate.",
        ]:
            story.append(Paragraph(item, s['bullet']))
        story.append(Paragraph(
            "4.3  Commission, bonuses, or additional incentives (if any) are set out in <b>Annex B</b>. "
            "These amounts are separate from base salary and are not included in statutory benefit calculations except as required by Thai law.", s['body']))
        story.append(Paragraph(
            "4.4  The Employer will deduct personal income tax, social security contributions (Social Security Act B.E. 2533), "
            "and other statutory deductions. The Employee will be registered with the Social Security Office within thirty (30) days of the Commencement Date.", s['body']))

        story.append(Paragraph("4.5  Company Purchases & Petty Cash.", s['sub_head']))
        for item in [
            "(a) The Employee must use the Employer's designated membership cards (e.g. Makro, HomePro, Lotus's) for all company purchases to obtain proper tax invoices under the Employer's Tax ID;",
            "(b) All purchases must be supported by a valid tax invoice in the Employer's company name and Tax ID. Receipts without the Employer's Tax ID will not be reimbursed;",
            "(c) Receipts must be submitted to accounting within three (3) business days;",
            "(d) Company cards and petty cash must not be used for personal expenses — personal use is a disciplinary offence;",
            "(e) Petty cash advances must be reconciled at least monthly;",
            "(f) All property-related expenses must be recorded in the Employer's approved management system (currently Hostaway) and submitted to accounting promptly.",
        ]:
            story.append(Paragraph(item, s['bullet']))

        story.append(Paragraph("4.6  Company Uniforms.", s['sub_head']))
        story.append(cream_box(
            "The Employer provides three (3) sets of company uniforms upon signing. Lost or negligently damaged items within the same year are the Employee's responsibility as detailed below.", s))
        story.append(Spacer(1, 0.3*cm))
        for item in [
            "4.6.1  The Employer provides three (3) complete sets of company uniform items (polo shirt, trousers, cap, and role-specific items) before the Employee commences duties. Items issued are recorded on a signed receipt.",
            "4.6.2  The Employer will renew uniform items once per year, on or before the employment anniversary date, while the Employee remains in active service.",
            "4.6.3  All issued items remain the Employer's property and must be returned in good condition on termination. Fair wear and tear from daily use during employment is not the Employee's liability.",
            "4.6.4  Items lost, stolen (without a police report), intentionally damaged, or rendered unusable due to the Employee's negligence before the annual renewal shall be replaced at the Employer's then-current cost price. The Employer will notify the Employee in writing of the specific items and replacement amounts before any deduction.",
            "4.6.5  Salary deductions for uniform replacement cost shall require the Employee's prior written consent pursuant to <b>Section 76 of the Labour Protection Act B.E. 2541</b>. The Employee may alternatively purchase replacement items independently. Deductions shall not exceed the documented actual cost.",
            "4.6.6  The Employee must wear issued items at all times during working hours and when representing the Employer.",
        ]:
            story.append(Paragraph(item, s['body']))

        story.append(Paragraph("4.7  Night Work.", s['sub_head']))
        for item in [
            "4.7.1  When assigned to work between 22:00 and 06:00 (\"night hours\"), such work must be scheduled in advance by the Employer and recorded in the approved overtime/night-shift log.",
            "4.7.2  The Employee shall receive a night-work premium of <b>THB ______</b> per hour (or per scheduled night shift as agreed in writing) for actual night hours worked, in addition to the applicable hourly or daily base rate.",
            "4.7.3  All night shift work requires prior written authorisation (including via LINE, WhatsApp, or email) and the Employee must log start time, end time, and tasks performed.",
            "4.7.4  Night work must not cause daily working hours to exceed the limits set by the Labour Protection Act without appropriate overtime pay under clause 4.2.",
        ]:
            story.append(Paragraph(item, s['body']))

        # 5 Working Hours
        story.append(sdiv()); story.append(Paragraph("5.  Working Hours", s['sec_head']))
        for t in [
            "5.1  Normal working hours are <b>09:00 to 18:00, Monday to Saturday</b> (inclusive of a one-hour meal break), not exceeding eight (8) hours of actual work per day and forty-eight (48) hours per week, in accordance with the Labour Protection Act B.E. 2541.",
            "5.2  The Employee is entitled to at least one (1) day off per week (LPA Section 28).",
            "5.3  After five (5) consecutive working hours, the Employee shall receive a rest break of not less than one (1) hour (LPA Section 27).",
            "5.4  The Employer may adjust schedules with reasonable notice, provided total hours comply with law.",
        ]:
            story.append(Paragraph(t, s['body']))
        story.append(Paragraph(
            "5.5  Emergency Availability. Given the nature of villa management, the Employee acknowledges that guest emergencies, property incidents, and urgent maintenance issues may arise outside normal hours. The Employee agrees to:", s['body']))
        for item in ["(a) Be reachable by phone and message during rostered on-call periods;",
                     "(b) Respond to emergency calls or messages within thirty (30) minutes during on-call periods;",
                     "(c) Attend the property or take immediate action when a guest emergency, security issue, or property damage requires physical attendance."]:
            story.append(Paragraph(item, s['bullet']))
        story.append(Paragraph(
            "Actual hours worked during emergency response shall be recorded and compensated as overtime per clause 4.2. "
            "Stand-by duty alone (without actual work performed) is not overtime. The Employer will roster on-call fairly.", s['body']))

        # 6 Leave
        story.append(sdiv()); story.append(Paragraph("6.  Leave and Public Holidays", s['sec_head']))
        for t in [
            "6.1  <b>Weekly rest day:</b> Not less than one (1) day per week in accordance with Thai labour law.",
            "6.2  <b>Public holidays:</b> Not less than thirteen (13) days per year as announced by the Employer.",
            "6.3  <b>Annual leave:</b> Not less than six (6) working days per year after one (1) year of service. Unused leave may be carried over or paid out per Employer policy.",
            "6.4  <b>Sick leave:</b> Up to thirty (30) working days per year with pay (LPA Section 32). A medical certificate may be required for three (3) or more consecutive sick days.",
            "6.4a <b>Business leave:</b> At least three (3) working days per year with full pay for necessary personal business matters (LPA Section 34).",
            "6.5  <b>Maternity leave:</b> Up to ninety-eight (98) days per pregnancy including holidays (LPA Section 41 as amended). The Employer pays wages for not more than forty-five (45) days; remaining days may be covered by the Social Security Fund.",
            "6.6  <b>Paternity leave:</b> Up to fifteen (15) working days with pay, within thirty (30) days of the child's birth — LPA Section 41/2 (as amended).",
            "6.7  <b>Other statutory leave:</b> As required by Thai labour law, including military service leave, sterilisation leave, and training leave.",
        ]:
            story.append(Paragraph(t, s['body']))

        # ── Holiday-in-lieu arrangement (EN) ─────────────────────────────────────
        story.append(Paragraph(
            "6.5a  <b>Public / Traditional Holidays (13 days) — Compensatory Leave Arrangement.</b>  "
            "The Employee is entitled to at least 13 traditional holidays per year (LPA Section 29). "
            "In the villa hospitality industry, the Employee may be required to work on these days. In such cases: "
            "(a) Normal-hours work on a public holiday is compensated at not less than double (2×) the daily rate (LPA Section 56); "
            "(b) Overtime on a public holiday is compensated at not less than three (3×) the hourly rate; "
            "(c) Each public holiday worked accumulates as one (1) day of compensatory leave, to be taken within the same calendar year at a time agreed by both parties; "
            "(d) Compensatory leave (up to 13 days) + annual leave (6 days) = flexible leave pool of up to <b>19 days per year</b>; "
            "(e) Leave schedule requires at least 7 days advance notice, subject to operational needs.",
            s['body']))

        # 7 Confidentiality
        story.append(sdiv()); story.append(Paragraph("7.  Confidentiality and Data Protection", s['sec_head']))
        story.append(Paragraph(
            "7.1  <b>Definition.</b> \"Confidential Information\" means all non-public information relating to the Employer's business, including: "
            "(a) property owner identities, contact details, contract terms and fee structures; (b) guest data, booking details and preferences; "
            "(c) pricing strategies, revenue data and financial information; (d) operational systems, processes, software and passwords; "
            "(e) supplier and partner agreements; (f) commission structures, salary data and personnel information; (g) marketing strategies and business plans.", s['body']))
        story.append(Paragraph(
            "7.2  <b>Obligations.</b> The Employee shall keep all Confidential Information strictly confidential; not disclose it to third parties without the Employer's prior written consent; "
            "not use it beyond the scope of employment; take reasonable measures to prevent unauthorised access; and not copy or remove Confidential Information except as authorised.", s['body']))
        story.append(Paragraph(
            "7.3  <b>Survival.</b> The obligations in clause 7 survive the termination of this Agreement indefinitely.", s['body']))
        story.append(Paragraph(
            "7.4  <b>PDPA compliance.</b> The Employee must comply with the Personal Data Protection Act B.E. 2562 (PDPA) and the Employer's policies regarding personal data of guests, owners, employees and third parties.", s['body']))

        # 8 Non-compete
        story.append(sdiv()); story.append(Paragraph("8.  Non-Solicitation and Non-Compete", s['sec_head']))
        story.append(Paragraph(
            "8.1  During employment and for twelve (12) months after the termination date (<b>\"Restricted Period\"</b>), "
            "the Employee shall not directly or indirectly:", s['body']))
        for item in [
            "(a) Solicit, approach or contact any property owner managed by the Employer during the last 12 months of employment to offer competing property management services;",
            "(b) Divert or attempt to divert any guest, booking or business opportunity away from the Employer;",
            "(c) Solicit, induce or encourage any employee, contractor or agent of the Employer to leave their engagement;",
            "(d) Interfere with or damage the Employer's relationships with any property owner, guest, supplier or booking channel.",
        ]:
            story.append(Paragraph(item, s['bullet']))
        story.append(Paragraph(
            "8.2  <b>Non-Compete.</b> During employment and for twelve (12) months after termination, the Employee shall not establish, operate, manage or be employed by any business providing property management, "
            "villa rental management, or similar competing services in <b>Koh Samui, Koh Phangan, and the surrounding islands of Surat Thani Province</b>.", s['body']))
        story.append(Paragraph(
            "8.3  <b>Liquidated damages.</b> Breach of clause 8 shall render the Employee liable to pay <b>THB __________ </b> "
            "(recommended: 3–6 months' salary) to the Employer, without prejudice to the Employer's right to claim further damages or injunctive relief.", s['body']))

        # 9 IP
        story.append(sdiv()); story.append(Paragraph("9.  Intellectual Property and Company Assets", s['sec_head']))
        for t in [
            "9.1  All documents, keys, access cards, equipment, systems, records, data, materials, work product and intellectual property provided to or created by the Employee during employment are the sole property of the Employer.",
            "9.2  Any work, creation, system, process or intellectual property developed during employment or using the Employer's resources belongs exclusively to the Employer.",
            "9.3  Upon termination, the Employee must immediately return all company property including keys, access cards, equipment, documents, uniforms and copies of company data, and provide written confirmation.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 10 Conduct
        story.append(sdiv()); story.append(Paragraph("10.  Compliance and Conduct", s['sec_head']))
        for t in [
            "10.1  The Employee agrees to comply with all company policies, work regulations, lawful instructions and professional standards.",
            "10.2  The Employee shall not accept money, commission, gifts or personal benefits from any property owner, guest, supplier or third party in connection with the Employer's business without explicit written authorisation.",
            "10.3  Serious misconduct may result in immediate termination without severance pay per Section 119 of the Thai Labour Protection Act. The Employer may suspend with pay pending investigation.",
            "10.4  Social Media: The Employee shall not post content that discloses Confidential Information, disparages the Employer or its clients, or uses the Employer's trademarks or property images without prior written consent.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 11 Termination
        story.append(sdiv()); story.append(Paragraph("11.  Termination", s['sec_head']))
        for t in [
            "11.1  Either party may terminate with written notice of not less than thirty (30) days, or the equivalent of at least one (1) full pay cycle, whichever is longer.",
            "11.2  The Employer may elect to pay wages in lieu of notice. During garden leave, the Employee remains bound by all obligations under this Agreement.",
            "11.3  Termination by the Employer must be in writing and state the grounds in accordance with Section 17 of the Labour Protection Act.",
            "11.4  Upon termination, the Employer shall pay within three (3) days: (a) accrued wages to the termination date; (b) unused accrued annual leave; (c) statutory severance if applicable; (d) any other amounts required by law.",
            "11.5  No severance is payable where there is serious misconduct under Section 119 of the Labour Protection Act, including: dishonesty, wilful damage, gross negligence causing damage, abandonment of duty for three or more consecutive working days without justification, or a criminal conviction.",
            "11.6  Clauses 7 (Confidentiality), 8 (Non-Solicitation / Non-Compete) and 9 (Intellectual Property) survive termination.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 12 Disciplinary
        story.append(sdiv()); story.append(Paragraph("12.  Disciplinary Process", s['sec_head']))
        for t in [
            "12.1  For non-serious misconduct, the Employer will follow a progressive disciplinary process: (a) First offence: verbal warning (recorded); (b) Second offence: written warning; (c) Third offence within one year of a written warning: final written warning or dismissal.",
            "12.2  For serious misconduct under Section 119 of the Labour Protection Act, the Employer may dismiss immediately without following progressive steps.",
            "12.3  All warnings must be in writing and signed by the Employee. Written warnings expire one (1) year from the date of the offence.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 13 Governing Law
        story.append(sdiv()); story.append(Paragraph("13.  Governing Law and Dispute Resolution", s['sec_head']))
        for t in [
            "13.1  This Agreement is governed by and construed in accordance with the laws of the Kingdom of Thailand.",
            "13.2  Any dispute arising from or in connection with this Agreement is subject to the exclusive jurisdiction of the Thai Labour Court.",
            "13.3  The parties agree to attempt to resolve disputes through good-faith negotiation before commencing formal proceedings.",
        ]:
            story.append(Paragraph(t, s['body']))

        # 14 General
        story.append(sdiv()); story.append(Paragraph("14.  General Provisions", s['sec_head']))
        for t in [
            "<b>14.1 Entire Agreement.</b> This Agreement, together with Annexes A and B, constitutes the entire agreement between the parties and supersedes all prior agreements and understandings relating to this subject matter.",
            "<b>14.2 Severability.</b> If any provision is found invalid or unenforceable, the remaining provisions continue in full force.",
            "<b>14.3 Amendments.</b> This Agreement may only be amended by a written instrument signed by both parties.",
            "<b>14.4 Waiver.</b> Waiver of any breach does not constitute waiver of any subsequent breach. Waivers must be in writing.",
            "<b>14.5 Assignment.</b> The Employee may not assign any rights or obligations under this Agreement without the Employer's prior written consent.",
            "<b>14.6 Notices.</b> All notices must be in writing and delivered by hand, registered post, or email to the addresses stated in this Agreement.",
            "<b>14.7 Property Inspection.</b> The Employee must conduct thorough property inspections before and after each guest stay using the Employer's approved checklists. Damage, maintenance issues or inventory discrepancies must be photographed and reported within twenty-four (24) hours.",
            "<b>14.8 Property Management System.</b> All tasks, bookings, guest communications and property records must be logged in the Employer's approved management system (currently Hostaway) per Employer procedures.",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv())
        story.append(Paragraph("Acknowledgement", s['sec_head']))
        story.append(Paragraph(
            "The Employee acknowledges having read, understood, and agreed to be bound by the terms and conditions of this Employment Agreement, "
            "including all Annexes, and having had the opportunity to seek independent legal advice before signing.", s['body']))
        story.append(Paragraph("This Agreement is executed in two (2) originals, one for each party.", s['body']))
        story += sig_block(s, 'en')
        return story

    return content

# ─── THAI EMPLOYMENT AGREEMENT ────────────────────────────────
def build_ea_th(data):
    emp = data.get('employee', {})
    dept_raw = data.get('department', 'housekeeping')
    dept = dept_name(dept_raw, 'th')
    pos = emp.get('position', '__________')
    sal = emp.get('salary', '__________')
    sd  = fmt_date(emp.get('startDate', ''))
    fname  = emp.get('fullName', '__________')
    nick   = emp.get('nickname', '')
    dob    = emp.get('dateOfBirth', '')
    nat    = emp.get('nationality', '__________')
    idno   = emp.get('idPassport', '__________')
    addr   = emp.get('address', '__________')
    phone  = emp.get('phone', '__________')
    mgd    = emp.get('managedProperties', [])
    nick_str_th = f' (ชื่อเล่น: \"<b>{nick}</b>\")' if nick else ''

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("สัญญาจ้างงาน", s['doc_title']))
        story.append(Paragraph("Mister Property Siam Co.,LTD — เอกสารแปลภาษาไทย (คู่ฉบับประกอบสัญญาภาษาอังกฤษ)", s['doc_sub']))
        story.append(hr()); story.append(Spacer(1, 0.2*cm))
        story.append(cream_box(
            "เอกสารนี้เป็นคำแปลภาษาไทยที่จัดทำขึ้นเพื่อประกอบสัญญาจ้างงานฉบับภาษาอังกฤษ "
            "ในกรณีที่มีความขัดแย้งใดๆ ระหว่างฉบับภาษาไทยและฉบับภาษาอังกฤษ ให้ฉบับภาษาอังกฤษมีผลบังคับใช้", s))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("สัญญาจ้างงานฉบับนี้ (<b>\"สัญญา\"</b>) ทำขึ้น ณ วันที่ลงนามล่าสุดด้านล่าง ระหว่าง:", s['body']))
        story.append(Spacer(1, 0.4*cm))

        party = [
            [Paragraph("นายจ้าง:", s['body_b']),
             Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>เลขที่ประจำตัวผู้เสียภาษี: 0845566025288<br/>"
                       "ที่อยู่จดทะเบียน: 115/26 หมู่ 6 ตำบลบ่อผุด เกาะสมุย จังหวัดสุราษฎร์ธานี 84320 ประเทศไทย<br/>"
                       "อีเมล: info@mrpropertysiam.com", s['body'])],
            [Paragraph("ลูกจ้าง:", s['body_b']),
             Paragraph(f"<b>ชื่อ-นามสกุล:</b> {fname}{nick_str_th}<br/><b>สัญชาติ:</b> {nat}<br/>"
                       f"<b>เลขที่บัตร / หนังสือเดินทาง:</b> {idno}<br/><b>ที่อยู่:</b> {addr}<br/>"
                       f"<b>โทรศัพท์:</b> {phone}<br/><b>แผนก:</b> {dept}", s['body'])],
        ]
        pt = Table(party, colWidths=[3*cm, CW - 3.5*cm])
        pt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(pt)
        story.append(Paragraph("คู่สัญญาตกลงกัน ดังนี้:", s['body']))

        story.append(sdiv()); story.append(Paragraph("1.  ตำแหน่งและหน้าที่", s['sec_head']))
        for t in [
            f"1.1  ลูกจ้างได้รับการจ้างงานในตำแหน่ง: <b>{pos}</b> ในแผนก <b>{dept}</b>"
                + ((" <br/><b>ขอบเขตงานเพิ่มเติม:</b> " + " &nbsp;·&nbsp; ".join(f"<b>{r}</b>" for r in (emp.get('additionalRoles') or []))) if emp.get('additionalRoles') else ""),
            "1.2  ลูกจ้างตกลงปฏิบัติหน้าที่ตามที่ระบุไว้ใน <b>ภาคผนวก ก</b> รวมถึงหน้าที่อื่นใดที่สมเหตุสมผลที่นายจ้างมอบหมาย",
            "1.3  ลูกจ้างต้องอุทิศเวลาทำงานทั้งหมดให้แก่นายจ้าง และไม่ประกอบอาชีพอื่นโดยไม่ได้รับความยินยอมเป็นลายลักษณ์อักษรล่วงหน้า",
            "1.4  ลูกจ้างต้องปฏิบัติหน้าที่ทั้งหมดด้วยความซื่อสัตย์และเป็นไปตามนโยบายและมาตรฐานของนายจ้าง",
            "1.5  ความสัมพันธ์กับเจ้าของทรัพย์สิน แขก ช่องทางการจอง ผู้จัดหา และการติดต่อทางธุรกิจทั้งหมดที่พัฒนาในระหว่างการจ้างงาน ถือเป็นทรัพย์สินของนายจ้างแต่เพียงผู้เดียว",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("2.  วันเริ่มต้นการจ้างงาน", s['sec_head']))
        story.append(Paragraph(f"2.1  การจ้างงานเริ่มต้นวันที่: <b>{sd}</b>", s['body']))
        story.append(Paragraph("2.2  สัญญานี้เป็น:  ☐  ไม่กำหนดระยะเวลา   ☐  กำหนดระยะเวลา สิ้นสุดวันที่: __________", s['body']))

        story.append(sdiv()); story.append(Paragraph("3.  ระยะเวลาทดลองงาน", s['sec_head']))
        story.append(navy_box("อ้างอิงกฎหมาย (ผ่านการตรวจสอบโดยนักบัญชี): ระยะทดลองงาน <b>120 วัน</b> ตามมาตรา 17(3) LPA — สิทธิ์ค่าชดเชยตามมาตรา 118 เกิดขึ้นเมื่อทำงานครบ 120 วันติดต่อกัน", s))
        story.append(Spacer(1, 0.3*cm))
        for t in [
            "3.1  ลูกจ้างอยู่ในระยะทดลองงานเป็นเวลา <b>หนึ่งร้อยยี่สิบ (120) วัน</b> นับจากวันที่เริ่มงาน ตามมาตรา 17 แห่ง พ.ร.บ. คุ้มครองแรงงาน พ.ศ. 2541",
            "3.2  ในระหว่างทดลองงาน คู่สัญญาฝ่ายใดฝ่ายหนึ่งสามารถบอกเลิกสัญญาได้ตามมาตรา 17(3) โดยแจ้งล่วงหน้าไม่น้อยกว่าหนึ่งรอบการจ่ายค่าจ้าง หรือชำระค่าจ้างแทนการบอกกล่าว ลูกจ้างมีสิทธิ์ค่าชดเชยตามมาตรา 118 เมื่อทำงานครบ 120 วันติดต่อกัน",
            "3.3  นายจ้างจะประเมินผลก่อนสิ้นสุดระยะทดลองงาน และจะยืนยัน ขยาย หรือสิ้นสุดการจ้างงาน",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("4.  ค่าจ้างและสวัสดิการ", s['sec_head']))
        story.append(Paragraph(f"4.1  ค่าจ้างพื้นฐาน: <b>THB {fmt_salary(sal)} ต่อเดือน</b> จ่ายภายในวันทำการสุดท้ายของเดือนโดยโอนเข้าบัญชีธนาคาร", s['body']))
        # Managed properties / commission (managers and revenue roles)
        if mgd:
            story.append(Paragraph("4.1.1  ความรับผิดชอบการบริหารทรัพย์สิน &amp; ค่าคอมมิชชั่น."
                " ลูกจ้างต้องดูแลรับผิดชอบทรัพย์สินดังต่อไปนี้ "
                "โดยจะได้รับค่าคอมมิชชั่นการบริหารจัดการ (แยกจากเงินเดือนพื้นฐาน) ตามที่ระบุ:", s['body']))
            tbl_data = [[Paragraph('<b>ทรัพย์สิน / วิลล่า</b>', s['body_b']),
                         Paragraph('<b>แพ็กเกจบริหาร %</b>', s['body_b']),
                         Paragraph('<b>ส่วนแบ่ง %</b>', s['body_b']),
                         Paragraph('<b>รายได้จริง %</b>', s['body_b'])]]
            for p in mgd:
                pack = p.get('managementPackRate', '') or ''
                cut  = p.get('commissionRate', '') or ''
                try:
                    eff = f"{round(float(pack)*float(cut)/100,1)}&nbsp;%" if pack != '' and cut != '' else '—'
                except Exception:
                    eff = '—'
                tbl_data.append([
                    Paragraph(p.get('propertyName',''), s['body']),
                    Paragraph(f"{pack}&nbsp;%" if pack != '' else '—', s['body']),
                    Paragraph(f"{cut}&nbsp;%" if cut != '' else '—', s['body']),
                    Paragraph(eff, s['body']),
                ])
            mt = Table(tbl_data, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
            mt.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
                ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
                ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            story.append(mt); story.append(Spacer(1,0.3*cm))
        story.append(Paragraph("4.2  ค่าล่วงเวลา (ต้องได้รับอนุมัติเป็นลายลักษณ์อักษรล่วงหน้า):", s['body']))
        for item in ["(ก) ล่วงเวลาในวันทำงานปกติ: ไม่น้อยกว่า 1.5 เท่า;",
                     "(ข) ทำงานในวันหยุดชั่วโมงปกติ: ไม่น้อยกว่า 1 เท่าของค่าจ้างรายวัน;",
                     "(ค) ล่วงเวลาในวันหยุด: ไม่น้อยกว่า 3 เท่า"]:
            story.append(Paragraph(item, s['bullet']))
        story.append(Paragraph("4.3  โบนัสและค่าตอบแทนเพิ่มเติม (หากมี) กำหนดไว้ใน <b>ภาคผนวก ข</b>", s['body']))
        story.append(Paragraph("4.4  นายจ้างจะหักภาษีเงินได้และเงินสมทบประกันสังคมตามที่กฎหมายกำหนด", s['body']))

        story.append(Paragraph("4.5  ชุดทำงานของบริษัท", s['sub_head']))
        story.append(cream_box("นายจ้างจัดชุดทำงาน 3 ชุดเมื่อลงนามสัญญา การเปลี่ยนทดแทนชุดที่สูญหายหรือเสียหายโดยเจตนาภายในปีเดียวกันเป็นความรับผิดชอบของลูกจ้าง", s))
        story.append(Spacer(1, 0.3*cm))
        for t in [
            "4.5.1  นายจ้างจัดชุดทำงานมาตรฐาน 3 ชุด (เสื้อโปโล กางเกง หมวก และรายการเฉพาะตามบทบาท) ก่อนเริ่มปฏิบัติหน้าที่",
            "4.5.2  นายจ้างจะต่อสิทธิ์ชุดทำงานปีละหนึ่งครั้งในวันครบรอบการเริ่มงาน",
            "4.5.3  หากรายการสูญหาย ถูกขโมย เสียหายโดยเจตนา หรือเสียหายเนื่องจากความประมาทก่อนรอบการเปลี่ยนรายปี ลูกจ้างต้องรับผิดชอบค่าใช้จ่ายในการเปลี่ยน",
            "4.5.4  การหักเงินค่าชุดทำงานต้องได้รับความยินยอมเป็นลายลักษณ์อักษรล่วงหน้าจากลูกจ้าง ตามมาตรา 76 แห่งพระราชบัญญัติคุ้มครองแรงงาน",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("5.  ชั่วโมงทำงาน", s['sec_head']))
        for t in [
            "5.1  ชั่วโมงทำงานปกติ: วันจันทร์ถึงวันเสาร์ เวลา 09:00–18:00 น. (รวมเวลาพัก 1 ชั่วโมง) ไม่เกิน 8 ชั่วโมงต่อวัน และไม่เกิน 48 ชั่วโมงต่อสัปดาห์ ตาม พ.ร.บ. คุ้มครองแรงงาน พ.ศ. 2541",
            "5.2  ลูกจ้างมีสิทธิหยุดพักประจำสัปดาห์ไม่น้อยกว่าสัปดาห์ละ 1 วัน (มาตรา 28 LPA)",
            "5.3  หลังจากทำงานต่อเนื่อง 5 ชั่วโมง ลูกจ้างมีสิทธิพักไม่น้อยกว่า 1 ชั่วโมง (มาตรา 27 LPA)",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("6.  วันหยุดและวันลา", s['sec_head']))
        for t in [
            "6.1  <b>วันหยุดประจำสัปดาห์:</b> ไม่น้อยกว่าหนึ่ง (1) วันต่อสัปดาห์",
            "6.2  <b>วันหยุดตามประเพณี:</b> ไม่น้อยกว่าสิบสาม (13) วันต่อปีตามที่นายจ้างประกาศ",
            "6.3  <b>วันลาพักร้อน:</b> ไม่น้อยกว่าหก (6) วันทำการต่อปี หลังครบหนึ่ง (1) ปีการทำงาน",
            "6.4  <b>วันลาป่วย:</b> สูงสุดสามสิบ (30) วันทำการต่อปีโดยได้รับค่าจ้าง (มาตรา 32 LPA) — ขาดงาน 3 วันขึ้นไปติดต่อกัน อาจต้องแสดงใบรับรองแพทย์",
            "6.4ก <b>วันลากิจ:</b> ไม่น้อยกว่า 3 วันทำการต่อปีโดยได้รับค่าจ้างเต็ม สำหรับกิจธุระจำเป็น (มาตรา 34 LPA)",
            "6.5  <b>วันลาคลอด:</b> สูงสุด 98 วัน ต่อการตั้งครรภ์ รวมวันหยุด (มาตรา 41 LPA) นายจ้างจ่ายค่าจ้างไม่เกิน 45 วัน ส่วนที่เหลืออาจได้รับจากกองทุนประกันสังคม",
            "6.6  <b>วันลาของบิดา:</b> สูงสุด 15 วันทำการโดยได้รับค่าจ้าง (มาตรา 41/2 LPA แก้ไขเพิ่มเติม)",
        ]:
            story.append(Paragraph(t, s['body']))

        # ── Holiday-in-lieu arrangement (TH) ─────────────────────────────────────
        story.append(Paragraph(
            "6.5ก  <b>วันหยุดตามประเพณี (13 วัน) — การสะสมวันลาทดแทน.</b>  "
            "ลูกจ้างมีสิทธิ์วันหยุดตามประเพณีไม่น้อยกว่า 13 วันต่อปี (มาตรา 29 LPA) "
            "เนื่องจากลักษณะงานบริการวิลล่า ลูกจ้างอาจต้องทำงานในวันดังกล่าว: "
            "(ก) ชั่วโมงปกติในวันหยุดตามประเพณี — ได้รับไม่น้อยกว่าสองเท่า (2×) (มาตรา 56 LPA); "
            "(ข) ล่วงเวลาในวันหยุด — ได้รับไม่น้อยกว่าสามเท่า (3×); "
            "(ค) วันหยุดที่ทำงานสะสมเป็นวันลาชดเชย 1 วัน ต้องใช้ภายในปีเดียวกัน; "
            "(ง) วันลาชดเชย + วันลาพักร้อน 6 วัน = วันลาสะสมสูงสุด <b>19 วันต่อปี</b>; "
            "(จ) แจ้งล่วงหน้าไม่น้อยกว่า 7 วัน",
            s['body']))

        story.append(sdiv()); story.append(Paragraph("7.  การรักษาความลับและการคุ้มครองข้อมูล", s['sec_head']))
        story.append(Paragraph("7.1  <b>นิยาม.</b>  \"ข้อมูลความลับ\" หมายถึงข้อมูลที่ไม่เปิดเผยทั้งหมดของนายจ้าง รวมถึงข้อมูลเจ้าของทรัพย์สิน ข้อมูลแขก กลยุทธ์ราคา ระบบปฏิบัติการ และโครงสร้างค่านายหน้า", s['body']))
        story.append(Paragraph("7.2  <b>พันธะหน้าที่.</b>  ลูกจ้างต้องเก็บรักษาข้อมูลความลับ ไม่เปิดเผยต่อบุคคลภายนอก และไม่นำไปใช้นอกเหนือจากการปฏิบัติหน้าที่", s['body']))
        story.append(Paragraph("7.3  <b>ผลบังคับภายหลัง.</b>  พันธะหน้าที่นี้ยังคงมีผลบังคับใช้หลังสิ้นสุดสัญญาจ้างงาน", s['body']))
        story.append(Paragraph("7.4  <b>PDPA.</b>  ลูกจ้างต้องปฏิบัติตามพระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 อย่างเคร่งครัด ห้ามเก็บรวบรวม ใช้ หรือเปิดเผยข้อมูลส่วนบุคคลของแขก เจ้าของทรัพย์สิน หรือบุคคลที่สาม เว้นแต่ในขอบเขตหน้าที่ การฝ่าฝืนถือเป็นความผิดทางวินัยร้ายแรง", s['body']))

        story.append(sdiv()); story.append(Paragraph("8.  ข้อห้ามการชักชวนและการแข่งขัน", s['sec_head']))
        story.append(Paragraph(
            "8.1  ในระหว่างการจ้างงานและเป็นเวลา 12 เดือนหลังวันที่สิ้นสุดสัญญา ลูกจ้างต้องไม่ชักชวนเจ้าของทรัพย์สิน "
            "เบี่ยงเบนแขก ชักชวนพนักงาน หรือแทรกแซงความสัมพันธ์ทางธุรกิจของนายจ้าง", s['body']))
        story.append(Paragraph(
            "8.2  <b>สัญญาไม่แข่งขัน.</b>  ลูกจ้างต้องไม่ประกอบธุรกิจบริหารอสังหาริมทรัพย์ที่แข่งขันใน "
            "<b>เกาะสมุย เกาะพะงัน และเกาะบริเวณใกล้เคียงในจังหวัดสุราษฎร์ธานี</b> เป็นเวลา 12 เดือนหลังสิ้นสุดสัญญา", s['body']))
        story.append(Paragraph("8.3  <b>ค่าเสียหาย.</b>  การละเมิดข้อนี้มีโทษปรับ <b>THB __________</b>", s['body']))

        story.append(sdiv()); story.append(Paragraph("9.  ทรัพย์สินบริษัทและทรัพย์สินทางปัญญา", s['sec_head']))
        for t in [
            "9.1  ทรัพย์สินและงานสร้างสรรค์ทั้งหมดที่สร้างขึ้นในระหว่างการจ้างงานเป็นของนายจ้างแต่เพียงผู้เดียว",
            "9.2  เมื่อสิ้นสุดสัญญา ลูกจ้างต้องคืนทรัพย์สินบริษัททั้งหมด",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("10.  การปฏิบัติตามกฎระเบียบและพฤติกรรม", s['sec_head']))
        for t in [
            "10.1  ลูกจ้างตกลงปฏิบัติตามนโยบายบริษัท ระเบียบการทำงาน และมาตรฐานวิชาชีพทั้งหมด",
            "10.2  ลูกจ้างต้องไม่รับเงิน ค่านายหน้า หรือผลประโยชน์จากบุคคลที่สาม เว้นแต่ได้รับอนุญาตเป็นลายลักษณ์อักษร",
            "10.3  การกระทำผิดร้ายแรงอาจส่งผลให้ถูกเลิกจ้างทันทีโดยไม่ได้รับค่าชดเชย",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("11.  การสิ้นสุดสัญญา", s['sec_head']))
        for t in [
            "11.1  คู่สัญญาฝ่ายใดฝ่ายหนึ่งสามารถบอกเลิกสัญญาได้โดยแจ้งล่วงหน้าเป็นลายลักษณ์อักษรไม่น้อยกว่า 30 วัน หรือไม่น้อยกว่าหนึ่งรอบการจ่ายค่าจ้าง แล้วแต่กรณีใดจะนานกว่า นายจ้างอาจชำระค่าจ้างแทนการบอกกล่าว",
            "11.2  เมื่อสิ้นสุดสัญญา นายจ้างต้องชำระภายใน 3 วัน ได้แก่: (ก) ค่าจ้างคงค้างถึงวันสุดท้าย; (ข) วันลาพักร้อนสะสมที่ยังไม่ได้ใช้; (ค) ค่าชดเชยตามมาตรา 118 หากมีสิทธิ์; (ง) เงินอื่นที่กฎหมายกำหนด",
            "11.3  ข้อ 7, 8 และ 9 ยังคงมีผลบังคับใช้หลังสิ้นสุดสัญญา",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("12.  กระบวนการทางวินัย", s['sec_head']))
        story.append(Paragraph("นายจ้างจะดำเนินกระบวนการทางวินัยตามขั้นตอนดังต่อไปนี้:", s['body']))
        for _t in [
            "12.1  <b>ขั้นที่ 1 ตักเตือนด้วยวาจา:</b> กระทำผิดครั้งแรก นายจ้างตักเตือนด้วยวาจาและบันทึกไว้",
            "12.2  <b>ขั้นที่ 2 ตักเตือนเป็นลายลักษณ์อักษร:</b> กระทำผิดซ้ำ นายจ้างออกหนังสือเตือนอย่างเป็นทางการ มีผล 12 เดือน",
            "12.3  <b>ขั้นที่ 3 เลิกจ้าง:</b> กระทำผิดซ้ำภายในระยะเวลาที่กำหนด นายจ้างอาจเลิกจ้างตามกฎหมาย",
            "12.4  <b>การกระทำผิดร้ายแรง:</b> ทุจริต ละทิ้งหน้าที่ ความรุนแรง หรือฝ่าฝืนกฎระเบียบอย่างจงใจ — นายจ้างเลิกจ้างทันทีโดยไม่จ่ายค่าชดเชยตามมาตรา 119 LPA",
        ]:
            story.append(Paragraph(_t, s['body']))

        story.append(sdiv()); story.append(Paragraph("13.  กฎหมายที่ใช้บังคับและการระงับข้อพิพาท", s['sec_head']))
        story.append(Paragraph("สัญญานี้อยู่ภายใต้กฎหมายแห่งราชอาณาจักรไทย ข้อพิพาทอยู่ภายใต้เขตอำนาจของศาลแรงงานไทย ในกรณีที่ฉบับภาษาไทยและภาษาอังกฤษขัดแย้งกัน ให้ใช้ฉบับภาษาไทยเป็นหลักในการตีความตามกฎหมายแรงงานไทย", s['body']))

        story.append(sdiv()); story.append(Paragraph("14.  บทบัญญัติทั่วไป", s['sec_head']))
        story.append(Paragraph(
            "สัญญานี้รวมกับภาคผนวกทั้งหมด ถือเป็นข้อตกลงทั้งหมด แก้ไขได้โดยการทำเป็นลายลักษณ์อักษรเท่านั้น "
            "และยังคงบังคับตามภาคผนวกทั้งหมดที่แนบมา", s['body']))

        story.append(sdiv()); story.append(Paragraph("การรับทราบ", s['sec_head']))
        story.append(Paragraph(
            "ลูกจ้างรับทราบว่าได้อ่าน เข้าใจ และตกลงที่จะผูกพันตามข้อกำหนดของสัญญาจ้างงานฉบับนี้ "
            "และมีโอกาสขอคำแนะนำอิสระก่อนลงนาม สัญญานี้จัดทำขึ้นสองฉบับต้นฉบับ", s['body']))
        story += sig_block(s, 'th')
        return story

    return content

# ─── BURMESE EMPLOYMENT AGREEMENT ─────────────────────────────
def build_ea_my(data):
    emp = data.get('employee', {})
    dept_raw = data.get('department', 'housekeeping')
    dept = dept_name(dept_raw, 'my')
    pos = emp.get('position', '__________')
    sal = emp.get('salary', '__________')
    sd  = fmt_date(emp.get('startDate', ''))
    fname = emp.get('fullName', '__________')
    nat   = emp.get('nationality', '__________')
    idno  = emp.get('idPassport', '__________')
    addr  = emp.get('address', '__________')
    phone = emp.get('phone', '__________')
    nick  = emp.get('nickname', '')
    dob    = emp.get('dateOfBirth', '')
    mgd   = emp.get('managedProperties', [])
    nick_str_my = f' (အမည်ချပ် : "<b>{nick}</b>")' if nick else ''
    dob_str_my = f'<br/><b>မွေးသက်ကရာဇတ် :</b> {dob}' if dob else ''

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph("အလုပ်ခန့်ထားမှု သဘောတူစာချုပ်", s['doc_title']))
        story.append(Paragraph("Mister Property Siam Co.,LTD — ဘားမားဘာသာ သဘောတူစာချုပ် (အင်္ဂလိပ်ဘာသာ ပူးတွဲပါ)", s['doc_sub']))
        story.append(hr()); story.append(Spacer(1, 0.2*cm))
        story.append(cream_box(
            "ဤဘားမားဘာသာ ဗားရှင်းသည် အင်္ဂလိပ်ဘာသာ အလုပ်ခန့်ထားမှု သဘောတူစာချုပ်နှင့် ပူးတွဲပါသော ဘာသာပြန်ဆိုချက် ဖြစ်သည်။ "
            "ဘားမားနှင့် အင်္ဂလိပ်ဗားရှင်းကြား ကွာဟချက်ရှိပါက ထိုင်းဘာသာ/အင်္ဂလိပ်ဘာသာ ဗားရှင်း ကျင့်သုံးမည်။", s))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph("ဤ အလုပ်ခန့်ထားမှု သဘောတူစာချုပ် ကို အောက်တွင် နောက်ဆုံးလက်မှတ်ရေးထိုးသောရက်တွင် ချုပ်ဆိုသည် :", s['body']))
        story.append(Spacer(1, 0.4*cm))

        party = [
            [Paragraph("အလုပ်ရှင် :", s['body_b']),
             Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>ကုမ္ပဏီ Tax ID : 0845566025288<br/>"
                       "မှတ်ပုံတင်လိပ်စာ : 115/26 Moo 6, Bo Phut, Koh Samui, Surat Thani 84320, Thailand<br/>"
                       "အီးမေးလ် : info@mrpropertysiam.com", s['body'])],
            [Paragraph("ဝန်ထမ်း :", s['body_b']),
             Paragraph(f"<b>အမည် (အပြည့်အစုံ) :</b> {fname}{nick_str_my}<br/><b>နိုင်ငံသား :</b> {nat}<br/>"
                       f"<b>မှတ်ပုံတင် / ပတ်စ်ပို့ :</b> {idno}{dob_str_my}<br/><b>လိပ်စာ :</b> {addr}<br/>"
                       f"<b>ဖုန်း :</b> {phone}<br/><b>ဌာန :</b> {dept}", s['body'])],
        ]
        pt = Table(party, colWidths=[3.2*cm, CW - 3.7*cm])
        pt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(pt)
        story.append(Paragraph("အဖွဲ့နှစ်ဖွဲ့သည် အောက်ပါအတိုင်း သဘောတူညီသည် :", s['body']))

        story.append(sdiv()); story.append(Paragraph("၁.  ရာထူးနှင့် တာဝန်ဝတ္တရားများ", s['sec_head']))
        for t in [
            f"၁.၁  ဝန်ထမ်းကို <b>{dept}</b> ဌာနတွင် <b>{pos}</b> ရာထူးဖြင့် ခန့်ထားသည်။"
                + ((" <br/><b>နောက်ထပ်တာဝန် :</b> " + " &nbsp;·&nbsp; ".join(f"<b>{r}</b>" for r in (emp.get('additionalRoles') or []))) if emp.get('additionalRoles') else ""),
            "၁.၂  ဝန်ထမ်းသည် <b>နောက်ဆက်တွဲ က</b> တွင် ဖော်ပြသော တာဝန်ဝတ္တရားများနှင့် အလုပ်ရှင်မှ ညွှန်ကြားသောအခြားတာဝန်များ ထမ်းဆောင်ရမည်။",
            "၁.၃  ဝန်ထမ်းသည် အလုပ်ချိန်ပြည့် အလုပ်ရှင်၏ လုပ်ငန်းကိုသာ အာရုံစိုက်ရမည်ဖြစ်ပြီး ကြိုတင်ရေးဖြင့် ခွင့်မပြုဘဲ အခြားအလုပ် မပါဝင်ရ။",
            "၁.၄  ဝန်ထမ်းသည် တာဝန်ဝတ္တရားအားလုံးကို ရိုးသားစွာ ကြိုးစားအားထုတ်မှုဖြင့် ထမ်းဆောင်ရမည်။",
            "၁.၅  အလုပ်ကာလအတွင်း ဖန်တီးသော မြေပိုင်ပိုင်ရှင်/ဧည့်သည်/ကြော်ငြာ/ကုန်ပစ္စည်းပေးသွင်းသူ ဆက်ဆံမှုများ အားလုံးသည် အလုပ်ရှင်၏ ပိုင်ဆိုင်မှုဖြစ်သည်။",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၂.  အလုပ်စတင်သောနေ့", s['sec_head']))
        story.append(Paragraph(f"၂.၁  အလုပ်ကို ဤရက်မှ စတင်ရမည် : <b>{sd}</b>", s['body']))
        story.append(Paragraph("၂.၂  ☐ မသတ်မှတ်ထားသောသက်တမ်း   ☐ သတ်မှတ်သက်တမ်း — ရက်ကုန် : __________", s['body']))

        story.append(sdiv()); story.append(Paragraph("၃.  စမ်းသပ်ကာလ", s['sec_head']))
        story.append(navy_box("အရေးကြီး — စမ်းသပ်ကာလသည် <b>၁၁၉ ရက်</b> (တစ်ရာတစ်ဆယ့်ကိုး ရက်) ဖြစ်သည် — ၁၂၀ ရက်မဟုတ်ပေ။", s))
        story.append(Spacer(1, 0.3*cm))
        for t in [
            "၃.၁  ဝန်ထမ်းသည် အလုပ်စတင်မှ <b>၁၁၉ ရက်</b> (တစ်ရာတစ်ဆယ့်ကိုး ရက်) စီစမ်းသပ်ကာလသို့ ပါဝင်ရမည်။",
            "၃.၂  စမ်းသပ်ကာလအတွင်း ဘယ်တစ်ဖက်မဆို လစာပေးချေမှုတစ်ကြိမ် ကြိုတင်အကြောင်းကြားချက်ဖြင့် ဖြုတ်ချနိုင်သည်။ ဝန်ထမ်းသည် ၁၂၀ ရက် မပြည့်ခင် ဖြုတ်ချပါက နစ်နာကြေး မပေးရ။",
            "၃.၃  စမ်းသပ်ကာလ ကုန်ဆုံးမတိုင်ခင် အလုပ်ရှင်သည် — အတည်ပြုခန့်အပ်ခြင်း၊ ပြန်တစ်ကြိမ်စစ်ဆေးခြင်း (ရေးဖြင့်) သို့မဟုတ် ဖြုတ်ချမှုပြုလုပ်ရမည်။",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၄.  လစာနှင့် အကျိုးခံစားခွင့်များ", s['sec_head']))
        story.append(Paragraph(f"၄.၁  လတစ်လ အခြေခံလစာ : <b>THB {fmt_salary(sal)}</b> — လ၏ နောက်ဆုံးအလုပ်ရက်တွင် ဘဏ်ငွေလွှဲဖြင့် ပေးချေမည်။", s['body']))
        # Managed properties / commission (managers and revenue roles)
        if mgd:
            story.append(Paragraph("၄.၁.၁  အိမ်ခြံမြေ စီမံခန့်ခွဲမှုတာဝန်နှင့် ကော်မရှင်။"
                " ဝန်ထမ်းသည် အောက်ပါ အိမ်ခြံမြေများကို ဂရုစိုက်တာဝန်ယူရမည်။ "
                "စီမံခန့်ခွဲမှု ကော်မရှင် (အခြေခံလစာနှင့် သီးခြားသော) ကို သတ်မှတ်ချက်အတိုင်း ပေးမည် :", s['body']))
            tbl_data = [[Paragraph('<b>အိမ်ခြံမြေ / Villa</b>', s['body_b']),
                         Paragraph('<b>စီမံ Pack %</b>', s['body_b']),
                         Paragraph('<b>ရငွေ %</b>', s['body_b']),
                         Paragraph('<b>ထိရောက် %</b>', s['body_b'])]]
            for p in mgd:
                pack = p.get('managementPackRate', '') or ''
                cut  = p.get('commissionRate', '') or ''
                try:
                    eff = f"{round(float(pack)*float(cut)/100,1)}&nbsp;%" if pack != '' and cut != '' else '—'
                except Exception:
                    eff = '—'
                tbl_data.append([
                    Paragraph(p.get('propertyName',''), s['body']),
                    Paragraph(f"{pack}&nbsp;%" if pack != '' else '—', s['body']),
                    Paragraph(f"{cut}&nbsp;%" if cut != '' else '—', s['body']),
                    Paragraph(eff, s['body']),
                ])
            mt = Table(tbl_data, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
            mt.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
                ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
                ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            story.append(mt); story.append(Spacer(1,0.3*cm))
        story.append(Paragraph("၄.၂  အချိန်ပိုခ (ကြိုတင်ရေးဖြင့် ခွင့်ပြုချက်ရမှသာ) :", s['body']))
        for item in ["(က) ပုံမှန်အလုပ်ရက် အချိန်ပို : နာရီလစာ၏ ၁.၅ ဆ;",
                     "(ခ) ကောင်ဘားအလုပ်ရက် ပုံမှန်အချိန် : နေ့ရောက်လစာ;",
                     "(ဂ) ကောင်ဘားအလုပ်ရက် အချိန်ပို : နာရီလစာ၏ ၃ ဆ။"]:
            story.append(Paragraph(item, s['bullet']))
        story.append(Paragraph("၄.၃  ဆုနှင့် ထပ်ဆောင်းငွေများ (ရှိပါက) ကို <b>နောက်ဆက်တွဲ ခ</b> တွင် ဖော်ပြသည်။", s['body']))

        story.append(Paragraph("၄.၄  အလုပ်ဝတ်စုံ (Company Workwear)။", s['sub_head']))
        story.append(cream_box("အလုပ်ရှင်သည် စာချုပ်လက်မှတ်ထိုးချိန်တွင် ကုမ္ပဏီ အလုပ်ဝတ်စုံ (၃) စုံ ပေးသည်။ တစ်နှစ်အတွင်း ပျောက်ဆုံးသော သို့မဟုတ် ဝန်ထမ်း၏ ဂရုမစိုက်မှုကြောင့် ပျက်စီးသောပစ္စည်းများကို ဝန်ထမ်းကိုယ်တိုင် မိမိကုန်ကျစရိတ်ဖြင့် အစားထိုးရမည်။", s))
        story.append(Spacer(1, 0.3*cm))
        for t in [
            "၄.၄.၁  ဤစာချုပ် လက်မှတ်ထိုးပြီး တာဝန်ဝင်မတိုင်ခင် ကုမ္ပဏီ polo shirt၊ ဘောင်းဘီ၊ ဦးထုပ်နှင့် တာဝန်ပေါ်မူတည်၍ ပစ္စည်းများ (၃) စုံ ပေးအပ်မည်။",
            "၄.၄.၂  နှစ်တိုင်း တစ်ကြိမ် (ခန့်ထားသောနေ့ မှတ်နှစ်ပတ်ကြာ) ဝတ်စုံ သစ်မွမ်းပေးမည်။",
            "၄.၄.၃  ပျောက်ဆုံးမှု/ဂရုမစိုက်မှုကြောင့် ပျက်စီးမှုအတွက် ဝန်ထမ်းသည် ကုန်ကျစရိတ် ကျသင့်မည်။ လစာနုတ်ရန် <b>ပုဒ်မ ၇၆</b> နှင့်အညီ ဝန်ထမ်း၏ ကြိုတင်ရေးဖြင့် သဘောတူချက် ရယူရမည်။",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၅.  အလုပ်ချိန်", s['sec_head']))
        for t in [
            "၅.၁  ပုံမှန်အလုပ်ချိန် — တစ်နေ့ ၈ နာရီ မကျော်၊ တစ်ပတ် ၄၈ နာရီ မကျော်",
            "၅.၂  အပတ်ရစ်နားသောနေ့ : __________________",
            "၅.၃  ဆက်တိုက် ၅ နာရီ ပြီးနောက် အနည်းဆုံး ၁ နာရီ နားချိန် ရပိုင်ခွင့်ရှိသည်",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၆.  ခွင့်နှင့် အများပြည်သူ ရုံးပိတ်ရက်", s['sec_head']))
        for t in [
            "၆.၁  <b>အပတ်ရစ်နားသောနေ့ :</b> တစ်ပတ် အနည်းဆုံး ၁ ရက်",
            "၆.၂  <b>ရိုးရာပွဲတော်ရက် :</b> နှစ်တိုင်း ၁၃ ရက် (အလုပ်ရှင်မှ ကြေညာ)",
            "၆.၃  <b>နှစ်ချုပ်ရပ်ခွင့် :</b> ၁ နှစ်ပြည့်ပြီးနောက် နှစ်တိုင်း ၆ ရက်",
            "၆.၄  <b>နာမကျန်းခွင့် :</b> နှစ်တိုင်း လစာဖြင့် ၃၀ ရက်",
            "၆.၅  <b>မိခင်ခွင့် :</b> ကိုယ်ဝန်တစ်ခုအတွက် ၉၈ ရက် (LPA ပုဒ်မ 41) — အလုပ်ရှင် ၄၅ ရက် လစာပေးရ၊ ကျန်ရက်မျာ ပြည်သူ့ကျန်းမာရေးရန်ပုံငွေမှ ရနိုင်",
            "၆.၆  <b>ဖခင်ခွင့် :</b> ကလေးမွေးသောနေ့မှ ၃၀ ရက်အတွင်း ၁၅ ရက် (LPA ပုဒ်မ ၄၁/၂)",
        ]:
            story.append(Paragraph(t, s['body']))

        # ── Holiday-in-lieu (MY) ─────────────────────────────────────────────────
        story.append(Paragraph(
            "၆.၅က  <b>ရိုးရာနေ့ကောင်း (၁၃ ရက်) — ခွင့်ရက် အစားထိုး သဘောတူ.</b>  "
            "ဝန်ထမ်းသည် တစ်နှစ်တွင် ရိုးရာနေ့ကောင်း ၁၃ ရက် ရပိုင်ခွင့်ရှိ (LPA ပုဒ်မ 29)။ "
            "Villa ဝန်ဆောင်မှုအတွက် ဧည့်သည်ရှိချိန် အလုပ်ဆင်းရနိုင်သည် — "
            "(က) ပုံမှန်နာရီ ဆင်းပါက နှစ်ဆ (2×) (LPA ပုဒ်မ 56); "
            "(ခ) အချိန်ပိုဆင်းပါက သုံးဆ (3×); "
            "(ဂ) ဆင်းသောနေ့တိုင်း ခွင့် ၁ ရက် စုဆောင်းနိုင် — ထိုနှစ်အတွင်းသာ ယူနိုင်; "
            "(ဃ) ရိုးရာနေ့ ၁၃ ရက် + နှစ်စဉ်ခွင့် ၆ ရက် = <b>နှစ်စဉ် ၁၉ ရက်</b> ပြောင်းလွယ်ခွင့်ထုပ်",
            s['body']))

        story.append(sdiv()); story.append(Paragraph("၇.  ဝန်ထမ်း၏ တာဝန်ဝတ္တရားများ / စည်းကမ်း", s['sec_head']))
        for t in [
            "၇.၁  ဝန်ထမ်းသည် ကုမ္ပဏီ၏ မူဝါဒများ၊ အလုပ်စည်းမျဉ်းများ နှင့် ပညာရှင်စံနှုန်းများကို လိုက်နာရမည်။",
            "၇.၂  မည်သည့် ပိုင်ရှင်/ဧည့်သည်/ကုန်ပစ္စည်းပေးသွင်းသူမဆို ငွေ/ကော်မရှင်/လက်ဆောင် မခံရ — ခွင့်ပြုချက်ရမှသာ ခံရ",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၈.  လျှို့ဝှက်ချက်ထိန်းသိမ်းခြင်း", s['sec_head']))
        story.append(Paragraph("\"လျှို့ဝှက်သတင်းအချက်အလက်\" ဆိုသည်မှာ မြေပိုင်ပိုင်ရှင်/ဧည့်သည်/ဈေးနှုန်း/ငွေကြေးဒေတာ/ဝန်ထမ်းဒေတာ/စစ်ဆင်ရေးစနစ် အပါအဝင် ကုမ္ပဏီ၏ ဖော်ပြမထားသောသတင်းအချက်အလက် အားလုံး ဖြစ်သည်။ ဤတာဝန်ဝတ္တရားသည် ဤစာချုပ်ဆုံးစဲပြီးနောက်ကာလပါ ဆက်လက်ရှိနေသည်။", s['body']))

        story.append(sdiv()); story.append(Paragraph("၉.  ယှဉ်ပြိုင်မည်မဟုတ်ကြောင်း ကတိနှင့် ဖောက်သည်မဆွဲဆောင်ကြောင်း", s['sec_head']))
        story.append(Paragraph(
            "အလုပ်ကာလနှင့် ဖြုတ်ချပြီး ၁၂ လ (တစ်ဆယ့်နှစ်လ) အတွင်း ဝန်ထမ်းသည် — "
            "မြေပိုင်ပိုင်ရှင် ဆွဲဆောင်ခြင်း၊ ဧည့်သည် လမ်းကြောင်းပြောင်းခြင်း၊ ဝန်ထမ်း ဆွဲဆောင်ခြင်း — မပြုရ။ "
            "<b>ကိုဆမွေ၊ ကိုပါင်ဂန်း နှင့် ဆူရတ်ထာနီပြည်နယ်</b> တွင် ၁၂ လ ယှဉ်ပြိုင်မည်မဟုတ်ကြောင်း ကတိ — ချိုးဖောက်ပါက <b>THB __________</b>", s['body']))

        story.append(sdiv()); story.append(Paragraph("၁၀.  ဥပစ္စမ်နှင့် ကုမ္ပဏီပစ္စည်း", s['sec_head']))
        for t in [
            "၁၀.၁  အလုပ်ကာလအတွင်း ပေးအပ်သော/ဖန်တီးသော မည်သည့် ဥပစ္စမ်မဆို အလုပ်ရှင်၏ ပိုင်ဆိုင်မှုဖြစ်သည်။",
            "၁၀.၂  ဖြုတ်ချပါက ကုမ္ပဏီပစ္စည်းအားလုံး (သော့၊ ကတ်၊ ကိရိယာ၊ ဝတ်စုံ) ချက်ချင်းပြန်အပ်ရမည်။",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၁၁.  စာချုပ်ရပ်ဆိုင်းခြင်း", s['sec_head']))
        for t in [
            "၁၁.၁  ဘယ်တစ်ဖက်မဆို ရက် ၃၀ ကြိုတင်ရေးဖြင့် အကြောင်းကြားချက်ဖြင့် ဖြုတ်ချနိုင်သည်",
            "၁၁.၂  ဖြုတ်ချပါက ၃ ရက်အတွင်း — ကျန်ရှိသောလစာ၊ မသုံးထားသောခွင့်၊ ဥပဒေနှင့်ညီသောနစ်နာကြေး — ပေးရမည်",
            "၁၁.၃  ပုဒ်မ ၁၁၉ ပါ ရာဇဝတ်မှုများတွင် နစ်နာကြေး မပေးရ",
            "၁၁.၄  ပုဒ်မ ၈ (လျှို့ဝှက်ချက်)၊ ၉ (ယှဉ်ပြိုင်မည်မဟုတ်) နှင့် ၁၀ (ဥပစ္စမ်) သည် ဖြုတ်ချပြီးနောက်ကာလတွင်လည်း ဆက်လက်ကျင့်သုံးသည်",
        ]:
            story.append(Paragraph(t, s['body']))

        story.append(sdiv()); story.append(Paragraph("၁၂.  စည်းကမ်းလုပ်ထုံးလုပ်နည်း", s['sec_head']))
        story.append(Paragraph("ပြင်းမသောကျင့်ဝတ်ချိုးဖောက်မှု — နှုတ်သတိပေး → ရေးသတိပေး → နောက်ဆုံးသတိပေး/ဖြုတ်ချ။ ရာဇဝတ်မှုတွင် ချက်ချင်း ဖြုတ်ချနိုင်သည်။", s['body']))

        story.append(sdiv()); story.append(Paragraph("၁၃.  ကျင့်သုံးမည့်ဥပဒေနှင့် အငြင်းပွားမှုဖြေရှင်းခြင်း", s['sec_head']))
        story.append(Paragraph("ဤစာချုပ်ကို ထိုင်းနိုင်ငံ ဥပဒေနှင့်အညီ ကျင့်သုံးမည်ဖြစ်ပြီး ထိုင်းနိုင်ငံ အလုပ်သမားတရားရုံး တစ်ဦးတည်း စီရင်ပိုင်ခွင့်ရှိသည်။ ကွာဟချက်ရှိပါက ထိုင်းဘာသာ/အင်္ဂလိပ်ဗားရှင်း ကျင့်သုံးမည်။", s['body']))

        story.append(sdiv()); story.append(Paragraph("၁၄.  ယေဘုယျ ဘောင်များ", s['sec_head']))
        story.append(Paragraph("ဤစာချုပ်သည် နောက်ဆက်တွဲများနှင့်တစ်ပါတည်း ကြိုတင်သဘောတူမှုများ အားလုံးကို ဖယ်ရှားသည်။ ရေးဖြင့်သာ ပြင်ဆင်နိုင်သည်။", s['body']))

        story.append(sdiv()); story.append(Paragraph("သက်သေပြုချက် (ACKNOWLEDGEMENT)", s['sec_head']))
        story.append(Paragraph(
            "ဝန်ထမ်းသည် ဤ အလုပ်ခန့်ထားမှု သဘောတူစာချုပ်ပါ သတ်မှတ်ချက်နှင့် အခြေအနေများကို (နောက်ဆက်တွဲများ အပါအဝင်) "
            "ဖတ်ရှုနားလည်ပြီး လိုက်နာကြောင်း သဘောတူသည်ကိုလည်း ရေးထိုးခြင်းမပြုမတိုင်ခင် မိမိကိုယ်တိုင် ဥပဒေဆိုင်ရာ အကြံဉာဏ်ရှာဖွေနိုင်ခဲ့ကြောင်း အသိအမှတ်ပြုသည်။ "
            "ဤစာချုပ်ကို မူလနှစ်စောင် (နှစ်ဖက် တစ်စောင်စီ) ချုပ်ဆိုသည်။", s['body']))
        story += sig_block(s, 'my')
        return story

    return content

# ─── ANNEX A BUILDERS ─────────────────────────────────────────
DEPT_CORE_DUTIES = {
    'housekeeping': {
        'en': ["Daily cleaning and preparation of all villa areas (bedrooms, bathrooms, kitchen, living areas, outdoor spaces)",
               "Linen and towel management: changing, washing, folding, and restocking to brand standard",
               "Reporting of damages, maintenance needs, or safety hazards within 24 hours",
               "Pre-arrival setup and post-departure deep clean to MPS presentation standard",
               "Guest amenities setup: toiletries, welcome gifts, minibar, and villa essentials",
               "Waste management and recycling in accordance with property procedures",
               "Maintaining cleanliness logs and checklists in the Employer's management system"],
        'th':  ["ทำความสะอาดและเตรียมพื้นที่วิลล่าทุกส่วนประจำวัน (ห้องนอน ห้องน้ำ ครัว พื้นที่นั่งเล่น พื้นที่กลางแจ้ง)",
               "จัดการผ้าปูที่นอนและผ้าขนหนู: เปลี่ยน ซัก พับ และเติมตามมาตรฐานแบรนด์",
               "รายงานความเสียหาย ความต้องการซ่อมบำรุง หรืออันตรายด้านความปลอดภัยภายใน 24 ชั่วโมง",
               "เตรียมวิลล่าก่อนรับแขกและทำความสะอาดอย่างละเอียดหลังจากแขกออกตามมาตรฐาน MPS",
               "จัดชุดต้อนรับแขก: สิ่งอำนวยความสะดวก ของขวัญต้อนรับ และสิ่งจำเป็นในวิลล่า"],
        'my':  ["ဗိလာ နေရာများ (အိပ်ခန်း၊ ရေချိုးခန်း၊ မီးဖိုချောင်၊ ဧည့်ခန်း၊ ပြင်ပ) ကို နေ့တိုင်း သန့်ရှင်းပြင်ဆင်ခြင်း",
               "အိပ်ရာခင်းနှင့် ပဝါ စီမံမှု — ပြောင်း၊ လျော်၊ ခေါက်၊ ဖြည့်တင်း",
               "ပျက်စီးမှု၊ ပြုပြင်ရမည့်ကိစ္စ သို့မဟုတ် အန္တရာယ်ကို ၂၄ နာရီအတွင်း သတင်းပို့ခြင်း",
               "ဧည့်သည်ရောက်မတိုင်မှီ ပြင်ဆင်မှုနှင့် ထွက်ပြီးနောက် အနက်ဆဲဆေးမှု — MPS စံနှုန်းအတိုင်း",
               "ဧည့်သည်အဆင်ပြေမှု ဖြည့်ဆည်းခြင်း — တာဝေး၊ ကြိုဆိုလက်ဆောင်၊ ဗိလာ လိုအပ်ချက်များ"],
    },
    'office': {
        'en': ["Handle all guest communication: pre-arrival, during-stay, and post-departure via approved channels",
               "Manage all booking platforms (Airbnb, Booking.com, direct website) with daily calendar reconciliation",
               "Coordinate property maintenance schedules, vendor visits, and repair works",
               "Prepare and distribute arrival packs, welcome letters, and villa information materials",
               "Maintain accurate financial records, expense reports, and petty cash in management system",
               "Liaise with property owners: regular updates, monthly financial reports, issue resolution",
               "Monitor and respond to online reviews across all platforms within 24 hours"],
        'th':  ["จัดการการสื่อสารกับแขกทั้งหมด: ก่อนรับ ระหว่างพัก และหลังออก ผ่านช่องทางที่ได้รับอนุมัติ",
               "จัดการแพลตฟอร์มการจองทั้งหมด (Airbnb, Booking.com, เว็บไซต์โดยตรง) กระทบยอดปฏิทินรายวัน",
               "ประสานตารางซ่อมบำรุงทรัพย์สิน การเยี่ยมชมผู้จัดหา และงานซ่อมแซม",
               "จัดทำและแจกจ่าย arrival pack จดหมายต้อนรับ และสื่อข้อมูลวิลล่า",
               "ดูแลและตอบรีวิวออนไลน์ในทุกแพลตฟอร์มภายใน 24 ชั่วโมง"],
        'my':  ["ဧည့်သည် ဆက်သွယ်ရေး အားလုံး စီမံမှု — ရောက်မတိုင်မှီ၊ နေဆဲ၊ ထွက်ပြီးနောက် — ခွင့်ပြုထားသောလမ်းကြောင်းမှ",
               "ကြိုတင်မှာကြားမှု ပလက်ဖောင်းများ (Airbnb, Booking.com, တိုက်ရိုက်ဝဘ်ဆိုက်) စီမံမှု — နေ့တိုင်း ပြေစာ ညှိချက်",
               "မြေပိုင်ပြုပြင်မှုဇယားများ၊ ကုန်ပစ္စည်းပေးသွင်းသူ လာရောက်မှုများ ညှိနှိုင်းခြင်း",
               "ဝင်ငွေ မှတ်တမ်းများ၊ ကုန်ကျစရိတ် အစီရင်ခံစာများ ထိန်းသိမ်းခြင်း",
               "အွန်လိုင်းဝေဖန်ချက်များကို ပလက်ဖောင်းအားလုံးမှ ၂၄ နာရီအတွင်း ကြည့်ရှုတုံ့ပြန်ခြင်း"],
    },
    'pool_garden_handyman': {
        'en': ["Daily pool water testing (pH, chlorine, alkalinity) and chemical balancing",
               "Weekly brushing, vacuuming, and backwashing of pool filters",
               "Pool surrounds, decking, and outdoor furniture cleaning and maintenance",
               "Garden maintenance: mowing, trimming, watering, fertilising, weeding",
               "Irrigation system inspection and adjustment",
               "Minor repairs and maintenance to plumbing, electrical, fixtures, and fittings",
               "Equipment log maintenance and regular safety inspections",
               "Reporting and photographing any maintenance issues within 24 hours"],
        'th':  ["ทดสอบน้ำในสระรายวัน (pH, คลอรีน, ความเป็นด่าง) และปรับสมดุลสารเคมี",
               "แปรง ดูด และล้างตัวกรองสระรายสัปดาห์",
               "ทำความสะอาดและดูแลบริเวณสระ ดาดฟ้า และเฟอร์นิเจอร์กลางแจ้ง",
               "ดูแลสวน: ตัดหญ้า ตัดแต่ง รดน้ำ ใส่ปุ๋ย ถอนหญ้า",
               "ซ่อมแซมเล็กน้อย: ระบบประปา ไฟฟ้า อุปกรณ์ติดตั้ง"],
        'my':  ["ရေကူးကန် ရေ နေ့တိုင်း စစ်ဆေးမှု (pH, chlorine, alkalinity) နှင့် ဓာတုချိန်ညှိ",
               "ရေကူးကန် ဘရပ်ဖြန်း၊ ပတ်ဝန်းကျင် သန့်ရှင်းမှု — အပတ်တိုင်း",
               "ဥယျာဉ် ထိန်းသိမ်းမှု — မြက်ခုတ်၊ ဖြတ်ထွင်း၊ ရေသွင်း၊ မြေဩဇာပေး",
               "ရေပိုက်၊ လျှပ်စစ်၊ ကိရိယာ ငယ်တောင့်ပြုပြင်မှု",
               "ပြုပြင်ရမည့်ကိစ္စများကို ဓာတ်ပုံ ရိုက်ပြီး ၂၄ နာရီအတွင်း သတင်းပို့ခြင်း"],
    },
}

ANNEX_A_TITLES = {
    'en': {'housekeeping':'Annex A-1 — Housekeeping','office':'Annex A-2 — Office & Management','pool_garden_handyman':'Annex A-3 — Pool, Garden & Handyman'},
    'th': {'housekeeping':'ภาคผนวก ก-1 — แผนกแม่บ้าน','office':'ภาคผนวก ก-2 — สำนักงาน / ฝ่ายจัดการ','pool_garden_handyman':'ภาคผนวก ก-3 — สระว่ายน้ำ สวน และช่าง'},
    'my': {'housekeeping':'နောက်ဆက်တွဲ က-၁ — အိမ်ရှင်မဌာန','office':'နောက်ဆက်တွဲ က-၂ — ရုံး/စီမံမှုဌာန','pool_garden_handyman':'နောက်ဆက်တွဲ က-၃ — ရေကူးကန်၊ ဥယျာဉ် နှင့် ပြုပြင်ဌာန'},
}

def build_annex_a(data, lang):
    emp  = data.get('employee', {})
    dept_raw = data.get('department', 'housekeeping')
    dept_ln  = dept_name(dept_raw, lang)
    fname    = emp.get('fullName', '__________')
    pos      = emp.get('position', '__________')
    addons   = data.get('addons', {})
    sel_duties = addons.get('duties', [])
    sel_comp   = addons.get('complicatedFunctions', [])
    title      = ANNEX_A_TITLES.get(lang, ANNEX_A_TITLES['en']).get(dept_raw, 'Annex A')

    header_names = {
        'en': ("Job Description","Department:","Employee:","Position:","Section A — Core Duties",
               "Section B — Additional Selected Duties","Section C — Specialised Functions",
               "Employee's Acknowledgement","I acknowledge receipt of this job description and confirm I understand my duties."),
        'th': ("คำบรรยายลักษณะงาน","แผนก:","ลูกจ้าง:","ตำแหน่ง:","ส่วน ก — หน้าที่หลัก",
               "ส่วน ข — หน้าที่เพิ่มเติมที่เลือก","ส่วน ค — งานพิเศษ",
               "การรับทราบของลูกจ้าง","ข้าพเจ้ารับทราบและเข้าใจหน้าที่ตามคำบรรยายลักษณะงานนี้"),
        'my': ("အလုပ်ဖော်ပြချက်","ဌာန :","ဝန်ထမ်း :","ရာထူး :","အပိုင်း က — အဓိကတာဝန်ဝတ္တရားများ",
               "အပိုင်း ခ — ရွေးချယ်ထားသောထပ်ဆောင်းတာဝန်များ","အပိုင်း ဂ — အထူးကျွမ်းကျင်မှုလုပ်ငန်းများ",
               "ဝန်ထမ်း၏ အသိအမှတ်ပြုချက်","ဤ အလုပ်ဖော်ပြချက်ကို လက်ခံပြီး တာဝန်ဝတ္တရားများ နားလည်ကြောင်း အတည်ပြုသည်"),
    }
    H = header_names.get(lang, header_names['en'])

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(title, s['doc_title']))
        story.append(Paragraph(H[0] + " — Mister Property Siam Co.,LTD", s['doc_sub']))
        story.append(hr())

        rows = [(H[1], dept_ln), (H[2], fname), (H[3], pos)]
        story.append(info_table(rows, s))
        story.append(Spacer(1, 0.4*cm))

        # Section A — core duties
        story.append(sdiv()); story.append(Paragraph(H[4], s['sec_head']))
        for d in DEPT_CORE_DUTIES.get(dept_raw, {}).get(lang, DEPT_CORE_DUTIES.get(dept_raw, {}).get('en', [])):
            story.append(Paragraph(f"• {d}", s['bullet']))

        # Section B — selected add-on duties
        story.append(sdiv()); story.append(Paragraph(H[5], s['sec_head']))
        if sel_duties:
            for duty_key in sel_duties:
                label = DUTY_LABELS.get(duty_key, {}).get(lang, DUTY_LABELS.get(duty_key, {}).get('en', duty_key))
                story.append(Paragraph(f"• {label}", s['bullet']))
        else:
            na = {"en":"No additional duties selected.","th":"ไม่มีหน้าที่เพิ่มเติมที่เลือก","my":"ထပ်ဆောင်းတာဝန် မရွေးချယ်ထား"}
            story.append(Paragraph(na.get(lang, na['en']), s['note']))

        # Section C — complicated functions
        story.append(sdiv()); story.append(Paragraph(H[6], s['sec_head']))
        if sel_comp:
            for comp_key in sel_comp:
                label = DUTY_LABELS.get(comp_key, {}).get(lang, DUTY_LABELS.get(comp_key, {}).get('en', comp_key))
                story.append(Paragraph(f"• {label}", s['bullet']))
        else:
            na = {"en":"No specialised functions selected.","th":"ไม่มีงานพิเศษที่เลือก","my":"အထူးကျွမ်းကျင်မှု မရွေးချယ်ထား"}
            story.append(Paragraph(na.get(lang, na['en']), s['note']))

        # Acknowledgement
        story.append(sdiv()); story.append(Paragraph(H[7], s['sec_head']))
        story.append(Paragraph(H[8], s['body']))
        story += sig_block(s, lang)
        return story

    return content

# ─── ANNEX B — PERFORMANCE BONUS ──────────────────────────────
def build_annex_b(data, lang):
    emp         = data.get('employee', {})
    fname       = emp.get('fullName', '__________')
    dept_raw    = data.get('department', 'housekeeping')
    bonus_pool  = emp.get('bonusPoolAmount', '')
    penalty_cap = emp.get('penaltyCapAmount', '')
    eom_reward  = emp.get('eomRewardAmount', '')

    def fmt_thb(v, fallback='THB __________'):
        return f'THB {int(v):,}' if v else fallback
    def fmt_pen(v, fallback='THB ______'):
        return f'THB {int(v):,}' if v else fallback

    titles = {
        'en': 'Annex B — Performance Bonus & Incentive Schedule',
        'th': 'ภาคผนวก ข — ตารางโบนัสและสิ่งจูงใจ',
        'my': 'နောက်ဆက်တွဲ ခ — ကျွမ်းကျင်မှုဆု & မောင်းနှင်မှုဇယား',
    }

    NAVY  = (0.11, 0.14, 0.25)
    WHITE = (1, 1, 1)

    def score_tbl(rows, s):
        t = Table(rows, colWidths=[CW*0.22, CW*0.52, CW*0.22])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),NAVY), ('TEXTCOLOR',(0,0),(-1,0),WHITE),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F5F0E8')]),
            ('BOX',(0,0),(-1,-1),1,colors.HexColor('#1C2340')),
            ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4CCBC')),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        return t

    def pen_tbl(rows, s):
        t = Table(rows, colWidths=[CW*0.62, CW*0.34])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),NAVY), ('TEXTCOLOR',(0,0),(-1,0),WHITE),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F5F0E8')]),
            ('BOX',(0,0),(-1,-1),1,colors.HexColor('#1C2340')),
            ('INNERGRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4CCBC')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        return t

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(titles[lang], s['doc_title']))
        story.append(Paragraph("Mister Property Siam Co.,LTD  |  Tax ID: 0845566025288", s['doc_sub']))
        story.append(hr())
        story.append(info_table([
            ("Employee / ชื่อ / အမည်", fname),
            ("Department", {"housekeeping":"Housekeeping","office":"Office / Management","pool":"Pool, Garden & Handyman"}.get(dept_raw, dept_raw.title())),
        ], s)); story.append(Spacer(1, 0.4*cm))

        if lang == 'en':
            story.append(Paragraph("1.  Structure & Eligibility", s['sec_head']))
            story.append(cream_box("Bonuses and penalties are assessed every six (6) months. Penalties are deducted from the bonus pool ONLY — never from base salary (LPA Section 76 B.E. 2541).", s))
            for t in [
                "1.1  Assessment periods: January–June (paid July) and July–December (paid January of the following year).",
                "1.2  Eligibility: probation must be completed; employee must have served at least 3 full months of the period.",
                f"1.3  Maximum bonus pool: <b>{fmt_thb(bonus_pool)}</b> per period — confirmed in writing at period start.",
                "1.4  Bonuses are pro-rated for periods of less than six (6) months.",
            ]:
                story.append(Paragraph(t, s['body']))

            if dept_raw == 'housekeeping':
                story.append(Paragraph("2.  Housekeeping — Performance Score Tiers", s['sec_head']))
                story.append(Paragraph("Average guest cleanliness score across all assigned villas, weighted by number of stays.", s['body']))
                story.append(Spacer(1, 0.15*cm))
                story.append(score_tbl([
                    [Paragraph("<b>Band</b>", s['tbl_hdr']), Paragraph("<b>Avg. Cleanliness Score</b>", s['tbl_hdr']), Paragraph("<b>Bonus %</b>", s['tbl_hdr'])],
                    [Paragraph("Excellent",      s['tbl_cell']), Paragraph("4.8 – 5.0 stars",  s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("Good",           s['tbl_cell']), Paragraph("4.5 – 4.79 stars", s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("Satisfactory",   s['tbl_cell']), Paragraph("4.0 – 4.49 stars", s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("Below Standard", s['tbl_cell']), Paragraph("Below 4.0 stars",  s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("2.1  Adjustments: punctuality (zero late arrivals +0.1), full attendance +0.1, documented linen complaints −0.1 each.", s['body']))
                story.append(Paragraph("3.  Penalty Provisions — Housekeeping", s['sec_head']))
                story.append(navy_box("Deducted from bonus pool only. Base salary is protected (LPA Section 76).", s))
                story.append(Spacer(1, 0.1*cm))
                story.append(pen_tbl([
                    [Paragraph("<b>Event</b>", s['tbl_hdr']), Paragraph("<b>Deduction</b>", s['tbl_hdr'])],
                    [Paragraph("Negative guest review from cleaning negligence", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Villa property damage due to negligence", s['tbl_cell']), Paragraph("Documented repair / replacement cost", s['tbl_cell'])],
                    [Paragraph("Repeated standard failures (3+ documented/period)", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Unauthorised absence during confirmed guest stay", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Guest item missing and attributed to housekeeping", s['tbl_cell']), Paragraph("Documented value (with investigation)", s['tbl_cell'])],
                ], s))

            elif dept_raw == 'pool':
                story.append(Paragraph("2.  Pool, Garden & Handyman — Performance Score Tiers", s['sec_head']))
                story.append(Paragraph("Score: maintenance round completion rate (60%) + guest outdoor satisfaction (30%) + zero critical failures (10%).", s['body']))
                story.append(Spacer(1, 0.15*cm))
                story.append(score_tbl([
                    [Paragraph("<b>Band</b>", s['tbl_hdr']), Paragraph("<b>Criteria</b>", s['tbl_hdr']), Paragraph("<b>Bonus %</b>", s['tbl_hdr'])],
                    [Paragraph("Excellent",      s['tbl_cell']), Paragraph("≥95% rounds + outdoor score ≥4.8 + zero critical failures", s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("Good",           s['tbl_cell']), Paragraph("≥85% rounds + outdoor score ≥4.5",                         s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("Satisfactory",   s['tbl_cell']), Paragraph("≥75% rounds + outdoor score ≥4.0",                         s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("Below Standard", s['tbl_cell']), Paragraph("Below 75% rounds OR score below 4.0 OR critical failure",  s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.15*cm))
                story.append(Paragraph("2.1  Critical failure = unchecked pool chemical imbalance during guest stay, or safety hazard not reported within 2 hours.", s['body']))
                story.append(Paragraph("3.  Penalty Provisions — Pool, Garden & Handyman", s['sec_head']))
                story.append(navy_box("Deducted from bonus pool only. Base salary is protected.", s))
                story.append(Spacer(1, 0.1*cm))
                story.append(pen_tbl([
                    [Paragraph("<b>Event</b>", s['tbl_hdr']), Paragraph("<b>Deduction</b>", s['tbl_hdr'])],
                    [Paragraph("Pool chemical failure during guest stay", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Missed scheduled maintenance round (per incident)", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Safety hazard unreported within 2 hours", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Property damage due to maintenance negligence", s['tbl_cell']), Paragraph("Documented cost", s['tbl_cell'])],
                    [Paragraph("Urgent repair not responded within 4 hours (during guest stay)", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                ], s))

            else:  # office
                is_manager = bool(emp.get('managedProperties'))
                story.append(Paragraph("2.  Office / Management — Performance Score Tiers", s['sec_head']))
                story.append(Paragraph("Score: portfolio occupancy rate (40%) + owner satisfaction (30%) + on-time reporting (20%) + guest review (10%).", s['body']))
                story.append(Spacer(1, 0.15*cm))
                story.append(score_tbl([
                    [Paragraph("<b>Band</b>", s['tbl_hdr']), Paragraph("<b>Criteria</b>", s['tbl_hdr']), Paragraph("<b>Bonus %</b>", s['tbl_hdr'])],
                    [Paragraph("Excellent",      s['tbl_cell']), Paragraph("Occupancy ≥80% + owner score ≥4.8 + all reports on time",              s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("Good",           s['tbl_cell']), Paragraph("Occupancy ≥70% + owner score ≥4.5 + ≥90% reports on time",            s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("Satisfactory",   s['tbl_cell']), Paragraph("Occupancy ≥60% + owner score ≥4.0",                                    s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("Below Standard", s['tbl_cell']), Paragraph("Occupancy below 60% OR owner score below 4.0 OR 3+ late reports",      s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.15*cm))
                if is_manager:
                    story.append(Paragraph("2.1  Portfolio Manager — Additional Incentive: management commission per property is paid monthly (separate from bonus pool). Revenue growth ≥10% YoY: discretionary bonus of up to 50% of pool at Employer's discretion.", s['body']))
                story.append(Paragraph("3.  Penalty Provisions — Office / Management", s['sec_head']))
                story.append(navy_box("Deducted from bonus pool only. Base salary is protected.", s))
                story.append(Spacer(1, 0.1*cm))
                story.append(pen_tbl([
                    [Paragraph("<b>Event</b>", s['tbl_hdr']), Paragraph("<b>Deduction</b>", s['tbl_hdr'])],
                    [Paragraph("Monthly property report late or incomplete (per report)", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Documented owner complaint from management failure", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Guest complaint from booking error or access issue", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("OTA listing error causing lost or double-booking", s['tbl_cell']), Paragraph(f"Up to {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("Breach of owner or guest confidentiality", s['tbl_cell']), Paragraph("Up to full pool forfeiture", s['tbl_cell'])],
                ], s))

            # Employee of the Month (all depts)
            story.append(Paragraph("4.  Employee of the Month", s['sec_head']))
            for t in [
                "4.1  Nominations based on: (a) written commendations in villa review books; (b) personal mentions in online reviews (Airbnb, Google, TripAdvisor); or (c) Employer nomination.",
                f"4.2  Reward: <b>{fmt_thb(eom_reward)}</b> cash bonus plus a printed certificate.",
                "4.3  Multiple nominations in one period carry additional weight.",
                "4.4  Employees subject to an active written warning are not eligible.",
            ]:
                story.append(Paragraph(t, s['body']))
            story.append(Spacer(1, 0.4*cm))
            story += sig_block(s, lang)

        elif lang == 'th':
            story.append(Paragraph("1.  โครงสร้างโบนัสและคุณสมบัติ", s['sec_head']))
            story.append(cream_box("โบนัสและบทลงโทษประเมินทุก 6 เดือน บทลงโทษหักจากกองทุนโบนัสเท่านั้น ห้ามหักจากค่าจ้างพื้นฐาน (มาตรา 76 LPA)", s))
            for t in [
                "1.1  รอบโบนัส: มกราคม–มิถุนายน (จ่ายกรกฎาคม) และกรกฎาคม–ธันวาคม (จ่ายมกราคมปีถัดไป)",
                "1.2  คุณสมบัติ: ผ่านการทดลองงานและทำงานครบ 3 เดือนเต็มในรอบนั้น",
                f"1.3  กองทุนโบนัสสูงสุด: <b>{fmt_thb(bonus_pool)}</b> ต่อรอบ",
            ]:
                story.append(Paragraph(t, s['body']))

            if dept_raw == 'housekeeping':
                story.append(Paragraph("2.  แม่บ้าน — ระดับคะแนนการทำความสะอาด", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>ระดับ</b>", s['tbl_hdr']), Paragraph("<b>คะแนนรีวิวแขก (เฉลี่ย)</b>", s['tbl_hdr']), Paragraph("<b>โบนัส %</b>", s['tbl_hdr'])],
                    [Paragraph("ดีเยี่ยม",        s['tbl_cell']), Paragraph("4.8–5.0 ดาว",    s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ดี",              s['tbl_cell']), Paragraph("4.5–4.79 ดาว",   s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("พอใช้",           s['tbl_cell']), Paragraph("4.0–4.49 ดาว",   s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("ต่ำกว่ามาตรฐาน", s['tbl_cell']), Paragraph("ต่ำกว่า 4.0 ดาว", s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("3.  บทลงโทษ — แม่บ้าน", s['sec_head']))
                story.append(navy_box("หักจากกองทุนโบนัสเท่านั้น ค่าจ้างพื้นฐานได้รับการคุ้มครอง", s))
                story.append(pen_tbl([
                    [Paragraph("<b>เหตุการณ์</b>", s['tbl_hdr']), Paragraph("<b>จำนวนหัก</b>", s['tbl_hdr'])],
                    [Paragraph("รีวิวเชิงลบจากความประมาทของแม่บ้าน", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ความเสียหายต่อทรัพย์สินวิลล่า", s['tbl_cell']), Paragraph("ค่าซ่อมแซม/ทดแทน", s['tbl_cell'])],
                    [Paragraph("ล้มเหลวในมาตรฐาน 3 ครั้งขึ้นไปในรอบเดียว", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ขาดงานระหว่างแขกเข้าพักโดยไม่ได้รับอนุญาต", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                ], s))
            elif dept_raw == 'pool':
                story.append(Paragraph("2.  สระน้ำ สวน ช่าง — ระดับการบำรุงรักษา", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>ระดับ</b>", s['tbl_hdr']), Paragraph("<b>เกณฑ์</b>", s['tbl_hdr']), Paragraph("<b>โบนัส %</b>", s['tbl_hdr'])],
                    [Paragraph("ดีเยี่ยม",        s['tbl_cell']), Paragraph("รอบ ≥95% + คะแนนกลางแจ้ง ≥4.8 + ไม่มีความล้มเหลวร้ายแรง", s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ดี",              s['tbl_cell']), Paragraph("รอบ ≥85% + คะแนนกลางแจ้ง ≥4.5", s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("พอใช้",           s['tbl_cell']), Paragraph("รอบ ≥75% + คะแนนกลางแจ้ง ≥4.0", s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("ต่ำกว่ามาตรฐาน", s['tbl_cell']), Paragraph("รอบ <75% หรือ คะแนน <4.0 หรือ ความล้มเหลวร้ายแรง", s['tbl_cell']), Paragraph("0%", s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("3.  บทลงโทษ — สระน้ำ สวน ช่าง", s['sec_head']))
                story.append(navy_box("หักจากกองทุนโบนัสเท่านั้น ค่าจ้างพื้นฐานได้รับการคุ้มครอง", s))
                story.append(pen_tbl([
                    [Paragraph("<b>เหตุการณ์</b>", s['tbl_hdr']), Paragraph("<b>จำนวนหัก</b>", s['tbl_hdr'])],
                    [Paragraph("ปัญหาสารเคมีสระขณะแขกพัก", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ข้ามรอบการบำรุงรักษาที่กำหนด (ต่อครั้ง)", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("อันตรายที่ไม่รายงานภายใน 2 ชั่วโมง", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ความเสียหายจากความประมาท", s['tbl_cell']), Paragraph("ค่าซ่อมแซม", s['tbl_cell'])],
                ], s))
            else:
                story.append(Paragraph("2.  สำนักงาน / บริหาร — ระดับผลการปฏิบัติงาน", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>ระดับ</b>", s['tbl_hdr']), Paragraph("<b>เกณฑ์</b>", s['tbl_hdr']), Paragraph("<b>โบนัส %</b>", s['tbl_hdr'])],
                    [Paragraph("ดีเยี่ยม",        s['tbl_cell']), Paragraph("เข้าพัก ≥80% + เจ้าของ ≥4.8 + รายงานตรงเวลาทั้งหมด", s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ดี",              s['tbl_cell']), Paragraph("เข้าพัก ≥70% + เจ้าของ ≥4.5 + ≥90% ตรงเวลา",         s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("พอใช้",           s['tbl_cell']), Paragraph("เข้าพัก ≥60% + เจ้าของ ≥4.0",                         s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("ต่ำกว่ามาตรฐาน", s['tbl_cell']), Paragraph("เข้าพัก <60% หรือ เจ้าของ <4.0",                     s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("3.  บทลงโทษ — สำนักงาน / บริหาร", s['sec_head']))
                story.append(navy_box("หักจากกองทุนโบนัสเท่านั้น ค่าจ้างพื้นฐานได้รับการคุ้มครอง", s))
                story.append(pen_tbl([
                    [Paragraph("<b>เหตุการณ์</b>", s['tbl_hdr']), Paragraph("<b>จำนวนหัก</b>", s['tbl_hdr'])],
                    [Paragraph("รายงานทรัพย์สินล่าช้า/ไม่ครบ (ต่อฉบับ)", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ข้อร้องเรียนจากเจ้าของที่มีสาเหตุจากการบริหาร", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("ข้อผิดพลาดในการจองที่ทำให้สูญเสียรายได้", s['tbl_cell']), Paragraph(f"สูงสุด {fmt_pen(penalty_cap)}", s['tbl_cell'])],
                    [Paragraph("การละเมิดความลับของเจ้าของหรือแขก", s['tbl_cell']), Paragraph("หักได้ถึงเต็มกองทุนโบนัส", s['tbl_cell'])],
                ], s))

            story.append(Paragraph("4.  พนักงานดีเด่นประจำเดือน", s['sec_head']))
            story.append(Paragraph(
                f"พนักงานที่ได้รับคำชมจากแขกในสมุดรีวิวหรือรีวิวออนไลน์ (Airbnb, Google) จะได้รับรางวัลพนักงานดีเด่น "
                f"รางวัล: <b>{fmt_thb(eom_reward)}</b> + ใบประกาศเกียรติคุณ พนักงานที่มีใบเตือนที่ยังมีผลบังคับไม่มีสิทธิ์รับรางวัล",
                s['body']))
            story.append(Spacer(1, 0.4*cm))
            story += sig_block(s, lang)

        else:  # my
            story.append(Paragraph("၁.  ဆုစနစ် အကျဉ်းချုပ်", s['sec_head']))
            story.append(cream_box("ဆုနှင့် ဒဏ်ကြေးကို ၆ လ တစ်ကြိမ် စစ်ဆေးသည်။ ဒဏ်ကြေးကို ဆုငွေထုပ်မှသာ နုတ်ရမည် — အခြေခံလစာမှ မနုတ်ရ (LPA ပုဒ်မ 76)", s))
            for t in [
                "၁.၁  ဆုကာလ: ဇန်နဝါရီ–ဇွန် (ဇူလိုင်တွင် ပေး) နှင့် ဇူလိုင်–ဒီဇင်ဘာ (နောက်နှစ် ဇန်နဝါရီတွင် ပေး)",
                f"၁.၂  ဆုငွေ အများဆုံး: <b>{fmt_thb(bonus_pool)}</b> — ကာလ ဦးပိုင်းတွင် ရေးဖြင့် သဘောတူရမည်",
            ]:
                story.append(Paragraph(t, s['body']))

            if dept_raw == 'housekeeping':
                story.append(Paragraph("၂.  Housekeeping — သန့်ရှင်းရေး ကျွမ်းကျင်မှုဇယား", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>အဆင့်</b>", s['tbl_hdr']), Paragraph("<b>ဧည့်သည် ရမှတ် (ပျမ်းမျှ)</b>", s['tbl_hdr']), Paragraph("<b>ဆု %</b>", s['tbl_hdr'])],
                    [Paragraph("အထူးကောင်း", s['tbl_cell']), Paragraph("4.8–5.0 ကြယ်",    s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ကောင်း",      s['tbl_cell']), Paragraph("4.5–4.79 ကြယ်",  s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("လုံလောက်",    s['tbl_cell']), Paragraph("4.0–4.49 ကြယ်",  s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("စံနှုန်းအောက်", s['tbl_cell']), Paragraph("4.0 ကြယ်အောက်", s['tbl_cell']), Paragraph("0%",  s['tbl_cell'])],
                ], s)); story.append(Spacer(1, 0.2*cm))
                story.append(Paragraph("၃.  ဒဏ်ကြေး — Housekeeping", s['sec_head']))
                story.append(navy_box("ဆုငွေထုပ်မှသာ နုတ်ရမည် — အခြေခံလစာ ကာကွယ်ထားသည်", s))
                story.append(pen_tbl([
                    [Paragraph("<b>အကြောင်း</b>", s['tbl_hdr']), Paragraph("<b>နုတ်ငွေ</b>", s['tbl_hdr'])],
                    [Paragraph("ဂရုမစိုက်မှုကြောင့် ဧည့်သည် ဆိုးဝါးသောဝေဖန်ချက်", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                    [Paragraph("ဗိလာပစ္စည်းပျက်စီးမှု (ဂရုမစိုက်ခြင်းကြောင့်)", s['tbl_cell']), Paragraph("ပြုပြင်/အစားထိုးကုန်ကျ", s['tbl_cell'])],
                    [Paragraph("ဧည့်သည်ရှိချိန် ခွင်မပြုဘဲ ခွင်ပျက်", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                ], s))
            elif dept_raw == 'pool':
                story.append(Paragraph("၂.  ကန်၊ ဥယျာဉ်၊ ဆင်ခြေ — ထိန်းသိမ်းမှုဇယား", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>အဆင့်</b>", s['tbl_hdr']), Paragraph("<b>သတ်မှတ်ချက်</b>", s['tbl_hdr']), Paragraph("<b>ဆု %</b>", s['tbl_hdr'])],
                    [Paragraph("အထူးကောင်း", s['tbl_cell']), Paragraph("≥95% + ပြင်ပ ≥4.8 + ချွတ်ယွင်းမှုမရှိ", s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ကောင်း",      s['tbl_cell']), Paragraph("≥85% + ပြင်ပ ≥4.5", s['tbl_cell']), Paragraph("70%", s['tbl_cell'])],
                    [Paragraph("လုံလောက်",    s['tbl_cell']), Paragraph("≥75% + ပြင်ပ ≥4.0", s['tbl_cell']), Paragraph("40%", s['tbl_cell'])],
                    [Paragraph("စံနှုန်းအောက်", s['tbl_cell']), Paragraph("<75% သို့မဟုတ် ချွတ်ယွင်းမှုကြီး", s['tbl_cell']), Paragraph("0%", s['tbl_cell'])],
                ], s))
                story.append(Paragraph("၃.  ဒဏ်ကြေး — ကန်၊ ဥယျာဉ်၊ ဆင်ခြေ", s['sec_head']))
                story.append(navy_box("ဆုငွေထုပ်မှသာ နုတ်ရမည်", s))
                story.append(pen_tbl([
                    [Paragraph("<b>အကြောင်း</b>", s['tbl_hdr']), Paragraph("<b>နုတ်ငွေ</b>", s['tbl_hdr'])],
                    [Paragraph("ဧည့်သည်ရှိချိန် ရေကန်ဓာတုပြဿနာ", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                    [Paragraph("သတ်မှတ်ထိန်းသိမ်းမှုကာလ ကျော်လွန်", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                    [Paragraph("ဂရုမစိုက်မှုကြောင့် ပစ္စည်းပျက်စီး", s['tbl_cell']), Paragraph("ပြုပြင်ကုန်ကျ", s['tbl_cell'])],
                ], s))
            else:
                story.append(Paragraph("၂.  ရုံးစီမံ / Villa Manager — ကျွမ်းကျင်မှုဇယား", s['sec_head']))
                story.append(score_tbl([
                    [Paragraph("<b>အဆင့်</b>", s['tbl_hdr']), Paragraph("<b>သတ်မှတ်ချက်</b>", s['tbl_hdr']), Paragraph("<b>ဆု %</b>", s['tbl_hdr'])],
                    [Paragraph("အထူးကောင်း", s['tbl_cell']), Paragraph("Occupancy ≥80% + ပိုင်ရှင် ≥4.8 + report အချိန်မီ", s['tbl_cell']), Paragraph("100%", s['tbl_cell'])],
                    [Paragraph("ကောင်း",      s['tbl_cell']), Paragraph("Occupancy ≥70% + ပိုင်ရှင် ≥4.5 + ≥90% မီ",       s['tbl_cell']), Paragraph("70%",  s['tbl_cell'])],
                    [Paragraph("လုံလောက်",    s['tbl_cell']), Paragraph("Occupancy ≥60% + ပိုင်ရှင် ≥4.0",                s['tbl_cell']), Paragraph("40%",  s['tbl_cell'])],
                    [Paragraph("စံနှုန်းအောက်", s['tbl_cell']), Paragraph("Occupancy <60% သို့မဟုတ် ပိုင်ရှင် <4.0",      s['tbl_cell']), Paragraph("0%",   s['tbl_cell'])],
                ], s))
                story.append(Paragraph("၃.  ဒဏ်ကြေး — ရုံးစီမံ", s['sec_head']))
                story.append(navy_box("ဆုငွေထုပ်မှသာ နုတ်ရမည်", s))
                story.append(pen_tbl([
                    [Paragraph("<b>အကြောင်း</b>", s['tbl_hdr']), Paragraph("<b>နုတ်ငွေ</b>", s['tbl_hdr'])],
                    [Paragraph("Property report နောက်ကျ/မပြည့်စုံ", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                    [Paragraph("ပိုင်ရှင်တိုင်ကြားချက် (မှတ်တမ်းပါ)", s['tbl_cell']), Paragraph(f"{fmt_pen(penalty_cap)} အထိ", s['tbl_cell'])],
                    [Paragraph("ပိုင်ရှင်/ဧည့်သည် လျှို့ဝှက်ချက် ချိုးဖောက်", s['tbl_cell']), Paragraph("ဆုထုပ် အပြည့် နုတ်နိုင်", s['tbl_cell'])],
                ], s))

            story.append(Paragraph("၄.  လ အကောင်းဆုံးဝန်ထမ်း", s['sec_head']))
            story.append(Paragraph(
                f"ဗိလာ review book သို့မဟုတ် online review (Airbnb, Google) တွင် ဧည့်သည်ချီးကျူးချက်ရသောဝန်ထမ်း ဆုနိုင်ပိုင်ခွင့်ရှိ — "
                f"ဆု: <b>{fmt_thb(eom_reward)}</b> + ဂုဏ်ထူးဆောင်လက်မှတ်", s['body']))
            story.append(Spacer(1, 0.4*cm))
            story += sig_block(s, lang)

        return story
    return content

def build_b2b(data, lang):
    col = data.get('collaborator', {})
    fname      = col.get('fullName', '__________')
    nick       = col.get('nickname', '')
    dob_col    = col.get('dateOfBirth', '')
    idno       = col.get('idPassport', '__________')
    phone      = col.get('phone', '__________')
    email      = col.get('email', '__________')
    svcs       = col.get('services', '__________')
    rate       = col.get('commissionRate', '__')
    terms      = col.get('paymentTerms', '__________')
    roles_list = col.get('roles', []) or []
    role       = ', '.join(roles_list) if roles_list else col.get('role', '')
    is_company = col.get('isCompany', False)
    co_name    = col.get('companyName', '')
    co_reg     = col.get('companyRegistration', '')
    co_tax     = col.get('companyTaxId', '')
    co_addr    = col.get('companyAddress', '')
    props      = col.get('properties', [])
    nick_str_en = f' (aka "<b>{nick}</b>")' if nick else ''
    dob_en = f'<br/><b>Date of Birth:</b> {dob_col}' if dob_col else ''
    dob_th2 = f'<br/><b>วันเกิด:</b> {dob_col}' if dob_col else ''
    dob_my2 = f'<br/><b>မွေးသက်ကရာဇတ် :</b> {dob_col}' if dob_col else ''
    nick_str_th = f' (ชื่อเล่น: "<b>{nick}</b>")' if nick else ''
    nick_str_my = f' (အမည်ချုပ် : "<b>{nick}</b>")' if nick else ''
    def _prop_table(s, props_list):
        """Helper: build a 4-col property table (Mgmt Pack % | Cut of Pack % | Effective %)."""
        tbl_data = [[Paragraph('<b>Property / Villa</b>', s['body_b']),
                     Paragraph('<b>Mgmt Pack %</b>', s['body_b']),
                     Paragraph('<b>Cut of Pack %</b>', s['body_b']),
                     Paragraph('<b>Effective %</b>', s['body_b'])]]
        for p in props_list:
            pack = p.get('managementPackRate', '') or ''
            cut  = p.get('commissionRate', '') or ''
            try:
                eff = f"{round(float(pack)*float(cut)/100,1)}&nbsp;%" if pack != '' and cut != '' else '—'
            except Exception:
                eff = '—'
            tbl_data.append([
                Paragraph(p.get('propertyName',''), s['body']),
                Paragraph(f"{pack}&nbsp;%" if pack != '' else '—', s['body']),
                Paragraph(f"{cut}&nbsp;%" if cut != '' else '—', s['body']),
                Paragraph(eff, s['body']),
            ])
        mt = Table(tbl_data, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
        mt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
            ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
            ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        return mt

    titles = {'en':'B2B Collaboration Agreement','th':'สัญญาความร่วมมือทางธุรกิจ (B2B)','my':'B2B ပူးပေါင်းဆောင်ရွက်မှု သဘောတူစာချုပ်'}
    title = titles.get(lang, titles['en'])

    def content(s):
        story = []
        story.append(cover_logo()); story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(title, s['doc_title']))
        story.append(Paragraph("Mister Property Siam Co.,LTD  |  Tax ID: 0845566025288", s['doc_sub']))
        story.append(hr()); story.append(Spacer(1, 0.2*cm))

        if lang == 'en':
            story.append(navy_box(
                "THIS IS NOT AN EMPLOYMENT CONTRACT. This agreement establishes a B2B service collaboration between two independent parties. "
                "The Collaborator is not an employee of Mister Property Siam Co.,LTD and is not entitled to employment benefits, social security, or statutory severance.", s))
        elif lang == 'th':
            story.append(navy_box(
                "เอกสารนี้ไม่ใช่สัญญาจ้างงาน นี่คือสัญญาความร่วมมือทางธุรกิจระหว่างคู่ค้าอิสระสองฝ่าย "
                "ผู้ร่วมงานไม่ถือเป็นลูกจ้างของ Mister Property Siam Co.,LTD และไม่มีสิทธิ์ได้รับสวัสดิการการจ้างงาน", s))
        else:
            story.append(navy_box(
                "ဤစာချုပ်သည် အလုပ်ခန့်ထားမှု သဘောတူစာချုပ် မဟုတ်ပေ။ ဤသည် လွတ်လပ်သောနှစ်ဖက် B2B ဝန်ဆောင်မှု ပူးပေါင်းမှု ဖြစ်သည်။ "
                "Collaborator သည် Mister Property Siam Co.,LTD ၏ ဝန်ထမ်းမဟုတ်ဘဲ အလုပ်ကာကွယ်ရေး အကျိုးခံစားမှုများ မရပိုင်ခွင့်ရှိ။", s))
        story.append(Spacer(1, 0.3*cm))

        if lang == 'en':
            story.append(Paragraph("This B2B Collaboration Agreement is entered into on the last date signed below, between:", s['body']))
        elif lang == 'th':
            story.append(Paragraph("สัญญาความร่วมมือทางธุรกิจนี้ทำขึ้น ณ วันที่ลงนามล่าสุดด้านล่าง ระหว่าง:", s['body']))
        else:
            story.append(Paragraph("ဤ B2B ပူးပေါင်းဆောင်ရွက်မှု သဘောတူစာချုပ် ကို အောက်တွင် နောက်ဆုံး လက်မှတ်ရေးထိုးသောရက်တွင် ချုပ်ဆိုသည် :", s['body']))

        story.append(Spacer(1, 0.4*cm))

        if lang == 'en':
            if is_company:
                collab_lines = (
                    f"<b>Company Name:</b> {co_name}<br/>"
                    f"<b>Registration No.:</b> {co_reg or '__________'}<br/>"
                    f"<b>Tax ID:</b> {co_tax or '__________'}<br/>"
                    f"<b>Registered Address:</b> {co_addr or '__________'}<br/>"
                    f"<b>Represented by:</b> {fname}{nick_str_en}<br/>"
                    f"<b>Phone:</b> {phone}<br/><b>Email:</b> {email}"
                    + (f"<br/><b>Role / Position:</b> {role}" if role else ''))
            else:
                collab_lines = (
                    f"<b>Name:</b> {fname}{nick_str_en}<br/><b>ID / Passport:</b> {idno}{dob_en}<br/>"
                    f"<b>Phone:</b> {phone}<br/><b>Email:</b> {email}"
                    + (f"<br/><b>Role / Position:</b> {role}" if role else ''))
            party = [
                [Paragraph("Company:", s['body_b']),
                 Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>Registered: 115/26 Moo 6, Bo Phut, Koh Samui, Surat Thani 84320, Thailand<br/>"
                           "Tax ID: 0845566025288  |  Email: info@mrpropertysiam.com", s['body'])],
                [Paragraph("Collaborator:", s['body_b']),
                 Paragraph(collab_lines, s['body'])],
            ]
        elif lang == 'th':
            if is_company:
                collab_lines_th = (
                    f"<b>ชื่อบริษัท:</b> {co_name}<br/>"
                    f"<b>เลขทะเบียนบริษัท:</b> {co_reg or '__________'}<br/>"
                    f"<b>เลขประจำตัวผู้เสียภาษี:</b> {co_tax or '__________'}<br/>"
                    f"<b>ที่อยู่จดทะเบียน:</b> {co_addr or '__________'}<br/>"
                    f"<b>ผู้แทน:</b> {fname}{nick_str_th}<br/>"
                    f"<b>โทรศัพท์:</b> {phone}<br/><b>อีเมล:</b> {email}"
                    + (f"<br/><b>ตำแหน่ง:</b> {role}" if role else ''))
            else:
                collab_lines_th = (
                    f"<b>ชื่อ:</b> {fname}{nick_str_th}<br/><b>บัตร / หนังสือเดินทาง:</b> {idno}<br/>"
                    f"<b>โทรศัพท์:</b> {phone}<br/><b>อีเมล:</b> {email}"
                    + (f"<br/><b>ตำแหน่ง:</b> {role}" if role else ''))
            party = [
                [Paragraph("บริษัท:", s['body_b']),
                 Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>ที่อยู่: 115/26 หมู่ 6 ตำบลบ่อผุด เกาะสมุย สุราษฎร์ธานี 84320<br/>"
                           "อีเมล: info@mrpropertysiam.com", s['body'])],
                [Paragraph("ผู้ร่วมงาน:", s['body_b']),
                 Paragraph(collab_lines_th, s['body'])],
            ]
        else:
            if is_company:
                collab_lines_my = (
                    f"<b>ကုမ္ပဏီအမည် :</b> {co_name}<br/>"
                    f"<b>မှတ်ပုံတင်အမှတ် :</b> {co_reg or '__________'}<br/>"
                    f"<b>အခွန်မှတ်ပုံတင်နံပါတ် :</b> {co_tax or '__________'}<br/>"
                    f"<b>မှတ်ပုံတင်လိပ်စာ :</b> {co_addr or '__________'}<br/>"
                    f"<b>ကိုယ်စားလှယ် :</b> {fname}{nick_str_my}<br/>"
                    f"<b>ဖုန်း :</b> {phone}<br/><b>အီးမေးလ် :</b> {email}"
                    + (f"<br/><b>ရာထူး :</b> {role}" if role else ''))
            else:
                collab_lines_my = (
                    f"<b>အမည် :</b> {fname}{nick_str_my}<br/><b>မှတ်ပုံတင်/ပတ်စ်ပို့ :</b> {idno}<br/>"
                    f"<b>ဖုန်း :</b> {phone}<br/><b>အီးမေးလ် :</b> {email}"
                    + (f"<br/><b>ရာထူး :</b> {role}" if role else ''))
            party = [
                [Paragraph("ကုမ္ပဏီ :", s['body_b']),
                 Paragraph("<b>Mister Property Siam Co.,LTD</b><br/>မှတ်ပုံတင်လိပ်စာ : 115/26 Moo 6, Bo Phut, Koh Samui, Surat Thani 84320<br/>"
                           "အီးမေးလ် : info@mrpropertysiam.com", s['body'])],
                [Paragraph("ပူးပေါင်းသူ :", s['body_b']),
                 Paragraph(collab_lines_my, s['body'])],
            ]
        pt = Table(party, colWidths=[3.2*cm, CW - 3.7*cm])
        pt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(pt)

        if lang == 'en':
            story.append(sdiv()); story.append(Paragraph("1.  Scope of Services", s['sec_head']))
            _n = [1]
            def _c(text, _story=story, _s=s, _n=_n):
                _story.append(Paragraph(f"1.{_n[0]}  {text}", _s['body']))
                _n[0] += 1
            if roles_list:
                roles_display = ' &nbsp;·&nbsp; '.join(f'<b>{r}</b>' for r in roles_list)
                _c(f"The Collaborator is engaged under this Agreement in the following service capacities: {roles_display}")
                _c(f"General scope of work and description:<br/><b>{svcs}</b>")
                _en_scope = B2B_ROLE_SCOPE.get('en', {})
                for _rname in roles_list:
                    _duties = _en_scope.get(_rname)
                    if _duties:
                        _c(f"<b>{_rname}</b> — Specific Duties &amp; Deliverables:")
                        for _d in _duties:
                            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp; {_d}", s['body']))
            else:
                _c(f"The Collaborator agrees to provide the following services to the Company on a non-exclusive basis:<br/><b>{svcs}</b>")
            _c("Services shall be performed to a professional standard, in good faith, and in accordance with the Company's policies and procedures.")
            _c("The Collaborator is an independent contractor. Nothing in this Agreement creates an employer-employee relationship, partnership, joint venture, or agency.")

            story.append(sdiv()); story.append(Paragraph("2.  Compensation", s['sec_head']))
            if props:
                story.append(Paragraph("2.1  The Company shall pay the Collaborator a management commission on qualifying transactions for the following properties:", s['body']))
                story.append(_prop_table(s, props)); story.append(Spacer(1,0.3*cm))
                if rate and str(rate) not in ('__', ''):
                    story.append(Paragraph(f"For transactions not covered by the above properties, a general rate of <b>{rate}%</b> applies.", s['body']))
            else:
                story.append(Paragraph(f"2.1  The Company shall pay the Collaborator a commission of <b>{rate}%</b> on qualifying transactions as defined in Schedule 1 (attached).", s['body']))
            story.append(Paragraph(f"2.2  Payment terms: <b>{terms}</b>. Payment will be made by bank transfer to the account designated by the Collaborator.", s['body']))
            story.append(Paragraph("2.3  The Collaborator is responsible for all personal taxes and statutory contributions applicable to income received under this Agreement.", s['body']))

            story.append(sdiv()); story.append(Paragraph("3.  Client Origin, Non-Solicitation &amp; Brand Protection", s['sec_head']))
            for t in [
                "3.1  <b>Non-Exclusive.</b>  This Agreement is non-exclusive. The Collaborator retains full rights to operate their own business and service other clients. MPS acknowledges the Collaborator's independent business activities.",
                "3.2  <b>Non-Solicitation.</b>  During this Agreement and for twelve (12) months following termination, the Collaborator shall not directly or indirectly solicit, induce, or encourage any active MPS client or property owner to reduce, terminate, or divert their relationship with MPS.",
                "3.3  <b>MPS-Originated Client Disclosure.</b>  If a prospective client contacts the Collaborator and that contact was directly or indirectly generated through MPS branding, marketing materials, listed properties, or referral chains originating from MPS, the Collaborator must notify MPS in writing within <b>five (5) business days</b> before signing any engagement.",
                "3.4  <b>MPS Response Window.</b>  Upon receiving notice under clause 3.3, MPS has <b>five (5) business days</b> to: (a) grant written clearance for the Collaborator to proceed independently; or (b) identify the client as MPS-originated and propose a referral fee arrangement in good faith. Failure to respond within this period shall be deemed clearance, and the Collaborator may proceed freely.",
                "3.5  <b>Good-Faith Resolution.</b>  If the parties cannot agree on a referral arrangement within ten (10) business days of MPS's response under clause 3.4(b), the Collaborator is free to proceed without restriction and without liability.",
                "3.6  <b>Pre-Existing Clients.</b>  Clients with whom the Collaborator had a documented professional relationship prior to the commencement date of this Agreement are explicitly excluded from clauses 3.2 and 3.3. The Collaborator shall maintain a brief list of such pre-existing clients, made available to MPS upon request.",
                "3.7  <b>Breach &amp; Remedy.</b>  A breach of clause 3.2 (direct solicitation) may result in damages of up to six (6) months' projected referral revenue attributable to the diverted client. Failure to notify under clause 3.3 alone does not constitute a breach but shall be taken into account in the event of a dispute.",
            ]:
                story.append(Paragraph(t, s['body']))

            story.append(sdiv()); story.append(Paragraph("4.  Confidentiality", s['sec_head']))
            story.append(Paragraph("4.1  The Collaborator shall keep all Confidential Information (as defined in Section 7 of the Employment Agreement) strictly confidential and shall not use it for any purpose other than the performance of services under this Agreement.", s['body']))
            story.append(Paragraph("4.2  This obligation survives termination of this Agreement indefinitely.", s['body']))

            story.append(sdiv()); story.append(Paragraph("5.  Term and Termination", s['sec_head']))
            story.append(Paragraph("5.1  This Agreement commences on the date of signing and continues until terminated by either party with thirty (30) days' written notice.", s['body']))
            story.append(Paragraph("5.2  Either party may terminate immediately in the event of material breach, insolvency, or conduct seriously damaging to the other party's reputation.", s['body']))

            story.append(sdiv()); story.append(Paragraph("6.  Governing Law", s['sec_head']))
            story.append(Paragraph("This Agreement is governed by the laws of the Kingdom of Thailand. Any dispute shall be resolved in the Thai courts.", s['body']))

        elif lang == 'th':
            story.append(sdiv()); story.append(Paragraph("1.  ขอบเขตการให้บริการ", s['sec_head']))
            _nth = [1]
            def _cth(text, _story=story, _s=s, _nth=_nth):
                _story.append(Paragraph(f"1.{_nth[0]}  {text}", _s['body']))
                _nth[0] += 1
            if roles_list:
                roles_display_th = ' &nbsp;·&nbsp; '.join(f'<b>{r}</b>' for r in roles_list)
                _cth(f"ผู้ร่วมงานได้รับการแต่งตั้งให้ปฏิบัติงานในฐานะต่อไปนี้ภายใต้สัญญานี้: {roles_display_th}")
                _cth(f"ขอบเขตการให้บริการโดยรวม:<br/><b>{svcs}</b>")
                _th_scope = B2B_ROLE_SCOPE.get('th', {})
                for _rname_th in roles_list:
                    _duties_th = _th_scope.get(_rname_th)
                    if _duties_th:
                        _cth(f"<b>{_rname_th}</b> — หน้าที่และขอบเขตงานเฉพาะ:")
                        for _d_th in _duties_th:
                            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp; {_d_th}", s['body']))
            else:
                _cth(f"ผู้ร่วมงานตกลงให้บริการต่อไปนี้แก่บริษัทในลักษณะไม่ผูกขาด:<br/><b>{svcs}</b>")
            _cth("ผู้ร่วมงานเป็นผู้รับจ้างอิสระ ไม่ใช่ลูกจ้างของบริษัท ไม่มีสิทธิ์ได้รับสวัสดิการพนักงาน")

            story.append(sdiv()); story.append(Paragraph("2.  ค่าตอบแทน", s['sec_head']))
            if props:
                story.append(Paragraph("2.1  บริษัทจะจ่ายค่านายหน้าการบริหารจัดการให้ผู้ร่วมงานสำหรับธุรกรรมที่มีสิทธิ์ของทรัพย์สินต่อไปนี้:", s['body']))
                tbl_data_th = [[Paragraph('<b>ทรัพย์สิน / วิลล่า</b>', s['body_b']),
                               Paragraph('<b>แพ็กเกจบริหาร %</b>', s['body_b']),
                               Paragraph('<b>ส่วนแบ่ง %</b>', s['body_b']),
                               Paragraph('<b>รายได้จริง %</b>', s['body_b'])]]
                for p in props:
                    pack_th = p.get('managementPackRate', '') or ''
                    cut_th  = p.get('commissionRate', '') or ''
                    try:
                        eff_th = f"{round(float(pack_th)*float(cut_th)/100,1)}&nbsp;%" if pack_th != '' and cut_th != '' else '—'
                    except Exception:
                        eff_th = '—'
                    tbl_data_th.append([
                        Paragraph(p.get('propertyName',''), s['body']),
                        Paragraph(f"{pack_th}&nbsp;%" if pack_th != '' else '—', s['body']),
                        Paragraph(f"{cut_th}&nbsp;%" if cut_th != '' else '—', s['body']),
                        Paragraph(eff_th, s['body']),
                    ])
                mt_th = Table(tbl_data_th, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
                mt_th.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
                    ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
                    ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
                    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                ]))
                story.append(mt_th); story.append(Spacer(1,0.3*cm))
                if rate and str(rate) not in ('__', ''):
                    story.append(Paragraph(f"สำหรับธุรกรรมที่ไม่ครอบคลุมโดยทรัพย์สินข้างต้น อัตราค่านายหน้าทั่วไป <b>{rate}%</b> ใช้บังคับ", s['body']))
            else:
                story.append(Paragraph(f"2.1  บริษัทจะจ่ายค่านายหน้า <b>{rate}%</b> ของธุรกรรมที่มีสิทธิ์", s['body']))
            story.append(Paragraph(f"2.2  เงื่อนไขการชำระเงิน: <b>{terms}</b>", s['body']))
            story.append(Paragraph("2.3  ผู้ร่วมงานรับผิดชอบภาษีและเงินสมทบทั้งหมดที่เกี่ยวข้องกับรายได้ภายใต้สัญญานี้", s['body']))

            story.append(sdiv()); story.append(Paragraph("3.  การรักษาความลับ", s['sec_head']))
            story.append(Paragraph("ผู้ร่วมงานต้องเก็บรักษาข้อมูลลับทั้งหมดของบริษัทและไม่เปิดเผยต่อบุคคลที่สาม พันธะหน้าที่นี้ยังคงมีผลบังคับหลังสิ้นสุดสัญญา", s['body']))

            story.append(sdiv()); story.append(Paragraph("4.  การคุ้มครองลูกค้า การไม่ชักชวน และการคุ้มครองแบรนด์", s['sec_head']))
            for t in [
                "4.1  <b>ไม่ผูกขาด.</b>  สัญญานี้ไม่มีลักษณะผูกขาด ผู้ร่วมงานยังคงมีสิทธิ์ดำเนินธุรกิจของตนเองและให้บริการลูกค้ารายอื่น MPS รับทราบกิจกรรมทางธุรกิจอิสระของผู้ร่วมงาน",
                "4.2  <b>การไม่ชักชวน.</b>  ในระหว่างสัญญาและ 12 เดือนหลังสิ้นสุด ผู้ร่วมงานต้องไม่ชักชวน โน้มน้าว หรือเบี่ยงเบนลูกค้า MPS ที่กำลังใช้บริการอยู่ให้ออกจาก MPS",
                "4.3  <b>การเปิดเผยลูกค้าที่มาจาก MPS.</b>  หากลูกค้าติดต่อผู้ร่วมงานผ่านช่องทางที่มาจาก MPS (แบรนด์ การตลาด ทรัพย์สิน หรือการแนะนำ) ผู้ร่วมงานต้องแจ้ง MPS เป็นลายลักษณ์อักษรภายใน <b>5 วันทำการ</b> ก่อนลงนามสัญญาใด ๆ",
                "4.4  <b>ระยะเวลาตอบสนองของ MPS.</b>  MPS มีเวลา 5 วันทำการในการ (ก) อนุมัติให้ดำเนินการอิสระ หรือ (ข) ระบุว่าเป็นลูกค้าที่มาจาก MPS และเสนอค่าตอบแทนการแนะนำโดยสุจริต หากไม่มีการตอบสนองภายในกำหนดถือว่าอนุมัติแล้ว ผู้ร่วมงานสามารถดำเนินการได้อิสระ",
                "4.5  <b>ลูกค้าที่มีอยู่ก่อนหน้า.</b>  ลูกค้าที่ผู้ร่วมงานมีความสัมพันธ์ทางวิชาชีพที่มีหลักฐานก่อนวันเริ่มสัญญานี้จะได้รับการยกเว้นจากข้อ 4.2 และ 4.3 ผู้ร่วมงานจัดทำรายชื่อลูกค้าดังกล่าวให้ MPS เมื่อมีการร้องขอ",
            ]:
                story.append(Paragraph(t, s['body']))

            story.append(sdiv()); story.append(Paragraph("5.  กฎหมายที่ใช้บังคับ", s['sec_head']))
            story.append(Paragraph("สัญญานี้อยู่ภายใต้กฎหมายแห่งราชอาณาจักรไทย", s['body']))

        else:  # my
            story.append(sdiv()); story.append(Paragraph("၁.  ဝန်ဆောင်မှု နယ်ပယ်", s['sec_head']))
            _nmy = [1]
            def _cmy(text, _story=story, _s=s, _nmy=_nmy):
                _story.append(Paragraph(f"၁.{_nmy[0]}  {text}", _s['body']))
                _nmy[0] += 1
            if roles_list:
                roles_display_my = ' &nbsp;·&nbsp; '.join(f'<b>{r}</b>' for r in roles_list)
                _cmy(f"ပူးပေါင်းသူသည် ဤစာချုပ်အောက် အောက်ပါ ဝန်ဆောင်မှုနယ်ပယ်များတွင် တာဝန်ထမ်းဆောင်ရမည် : {roles_display_my}")
                _cmy(f"ယေဘုယျ ဝန်ဆောင်မှု နယ်ပယ် :<br/><b>{svcs}</b>")
                _my_scope = B2B_ROLE_SCOPE.get('my', {})
                for _rname_my in roles_list:
                    _duties_my = _my_scope.get(_rname_my)
                    if _duties_my:
                        _cmy(f"<b>{_rname_my}</b> — သီးခြား တာဝန်နှင့် ဆောင်ရွက်ချက်များ :")
                        for _d_my in _duties_my:
                            story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp; {_d_my}", s['body']))
            else:
                _cmy(f"ပူးပေါင်းသူသည် ဤဝန်ဆောင်မှုများကို ကုမ္ပဏီသို့ တစ်ဦးသာ မဟုတ်သောနည်းဖြင့် ပေးရန် သဘောတူသည် :<br/><b>{svcs}</b>")
            _cmy("ပူးပေါင်းသူသည် လွတ်လပ်သောကန်ထရိုက်တာ ဖြစ်ပြီး ဝန်ထမ်းမဟုတ်ဘဲ အလုပ်ကာကွယ်ရေး အကျိုးခံစားမှုများ မရပိုင်ခွင့်ရှိ")

            story.append(sdiv()); story.append(Paragraph("၂.  ငွေကြေးဆိုင်ရာ", s['sec_head']))
            if props:
                story.append(Paragraph("၂.၁  ကုမ္ပဏီသည် အောက်ပါ အိမ်ခြံမြေများအတွက် သင့်တော်သောငွေပေးချေမှုများ၏ စီမံခန့်ခွဲမှု ကော်မရှင် ပေးမည် :", s['body']))
                tbl_data_my = [[Paragraph('<b>အိမ်ခြံမြေ / Villa</b>', s['body_b']),
                               Paragraph('<b>စီမံ Pack %</b>', s['body_b']),
                               Paragraph('<b>ရငွေ %</b>', s['body_b']),
                               Paragraph('<b>ထိရောက် %</b>', s['body_b'])]]
                for p in props:
                    pack_my = p.get('managementPackRate', '') or ''
                    cut_my  = p.get('commissionRate', '') or ''
                    try:
                        eff_my = f"{round(float(pack_my)*float(cut_my)/100,1)}&nbsp;%" if pack_my != '' and cut_my != '' else '—'
                    except Exception:
                        eff_my = '—'
                    tbl_data_my.append([
                        Paragraph(p.get('propertyName',''), s['body']),
                        Paragraph(f"{pack_my}&nbsp;%" if pack_my != '' else '—', s['body']),
                        Paragraph(f"{cut_my}&nbsp;%" if cut_my != '' else '—', s['body']),
                        Paragraph(eff_my, s['body']),
                    ])
                mt_my = Table(tbl_data_my, colWidths=[CW*0.38, CW*0.20, CW*0.20, CW*0.18])
                mt_my.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,0),(0.11,0.14,0.25)),
                    ('TEXTCOLOR',(0,0),(-1,0),(1,1,1)),
                    ('GRID',(0,0),(-1,-1),0.5,(0.83,0.78,0.72)),
                    ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
                ]))
                story.append(mt_my); story.append(Spacer(1,0.3*cm))
                if rate and str(rate) not in ('__', ''):
                    story.append(Paragraph(f"အထက်ပါ အိမ်ခြံမြေများ မပါဝင်သော ငွေပေးချေမှုများအတွက် ယေဘုယျ နှုန်း <b>{rate}%</b> ကျင့်သုံးမည်", s['body']))
            else:
                story.append(Paragraph(f"၂.၁  ကုမ္ပဏီသည် ပူးပေါင်းသူကို သင့်တော်သောငွေပေးချေမှုများ၏ <b>{rate}%</b> ကော်မရှင် ပေးမည်", s['body']))
            story.append(Paragraph(f"၂.၂  ပေးချေမှုသတ်မှတ်ချက် : <b>{terms}</b>", s['body']))
            story.append(Paragraph("၂.၃  ပူးပေါင်းသူသည် ဤစာချုပ်အောက် ရငွေနှင့် ပတ်သက်သော ကိုယ်ရေးကိုယ်တာ အခွန်များ ကိုယ်တိုင် ကျသင့်မည်", s['body']))

            story.append(sdiv()); story.append(Paragraph("၃.  လျှို့ဝှက်ချက်ထိန်းသိမ်းခြင်း", s['sec_head']))
            story.append(Paragraph("ပူးပေါင်းသူသည် ကုမ္ပဏီ၏ လျှို့ဝှက်သတင်းအချက်အလက် အားလုံးကို တင်းကြပ်စွာ လျှို့ဝှက်ထိန်းသိမ်းရမည်။ ဤတာဝန်ဝတ္တရားသည် ဤစာချုပ်ဆုံးစဲပြီးနောက်ကာလပါ ဆက်လက်ရှိနေသည်", s['body']))

            story.append(sdiv()); story.append(Paragraph("၄.  ဖောက်သည်ကာကွယ်ရေး၊ မဆွဲဆောင်ကြောင်းနှင့် အမှတ်တံဆိပ်ကာကွယ်ရေး", s['sec_head']))
            for t in [
                "၄.၁  <b>တစ်ဦးသာ မဟုတ်သောနည်း.</b>  ဤစာချုပ်သည် တစ်ဦးသာ ချုပ်ဆိုသောနည်းမဟုတ်ပေ။ ပူးပေါင်းသူသည် မိမိ၏ လုပ်ငန်းကို ဆက်လက်လည်ပတ်ပြီး အခြားဖောက်သည်များကို ဝန်ဆောင်မှုပေးနိုင်သည်။",
                "၄.၂  <b>မဆွဲဆောင်ကြောင်း.</b>  ဤစာချုပ်ကာလနှင့် ဖျက်ပြီးနောက် ၁၂ လ အတွင်း ပူးပေါင်းသူသည် MPS ဖောက်သည်များကို တိုက်ရိုက် သို့မဟုတ် သွယ်ဝိုက်စွာ ဆွဲဆောင်ခြင်း မပြုရ။",
                "၄.၃  <b>MPS မှ ဆင်းသက်သောဖောက်သည် ထုတ်ဖော်ပြောဆိုခြင်း.</b>  MPS ၏ brand၊ marketing၊ အိမ်ခြံမြေများ သို့မဟုတ် referral chain မှ ဖောက်သည်ရရှိပါက ပူးပေါင်းသူသည် မည်သည့် contract မဆို လက်မှတ်မထိုးမီ <b>ရုံးဖွင့်ရက် ၅ ရက်</b> အတွင်း MPS ကို စာဖြင့် အကြောင်းကြားရမည်။",
                "၄.၄  <b>MPS ၏ ပြန်ကြားချိန်.</b>  MPS သည် ရုံးဖွင့်ရက် ၅ ရက်အတွင်း (က) လွတ်လပ်စွာ ဆောင်ရွက်ရန် ခွင့်ပြုချက် ပေးနိုင်သည် သို့မဟုတ် (ခ) referral fee အဆိုပြုနိုင်သည်။ ပြန်မကြားပါက ခွင့်ပြုသည်ဟု မှတ်ယူမည်။",
                "၄.၅  <b>ကြိုတင်ရှိသောဖောက်သည်များ.</b>  ဤစာချုပ်မစတင်ခင် ဆက်ဆံမှုအထောက်အထားရှိသောဖောက်သည်များကို ပုဒ်မ ၄.၂ နှင့် ၄.၃ မှ ကင်းလွတ်ခွင့်ပြုသည်။",
            ]:
                story.append(Paragraph(t, s['body']))

            story.append(sdiv()); story.append(Paragraph("၅.  ကျင့်သုံးမည့်ဥပဒေ", s['sec_head']))
            story.append(Paragraph("ဤစာချုပ်ကို ထိုင်းနိုင်ငံ ဥပဒေနှင့်အညီ ကျင့်သုံးမည်", s['body']))

        story += sig_block(s, lang)
        return story

    return content

# ─── MAIN ──────────────────────────────────────────────────────
def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    ensure_fonts()

    contract_type = data.get('contractType', 'employment')
    dept_raw      = data.get('department', 'housekeeping')
    languages     = data.get('languages', ['en'])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for lang in languages:
            lang_dir = {'en': 'EN', 'th': 'TH', 'my': 'MY'}.get(lang, lang.upper())

            if contract_type == 'b2b':
                b2b_fn = build_b2b(data, lang)
                b2b_bytes = make_pdf(f"B2B Agreement ({lang_dir})", b2b_fn, lang)
                zf.writestr(f"{lang_dir}/MPS-{lang_dir}-B2B-Collaboration-Agreement.pdf", b2b_bytes)
            else:
                # Employment Agreement
                if lang == 'en':
                    ea_fn = build_ea_en(data)
                elif lang == 'th':
                    ea_fn = build_ea_th(data)
                else:
                    ea_fn = build_ea_my(data)
                ea_bytes = make_pdf(f"Employment Agreement ({lang_dir})", ea_fn, lang)
                zf.writestr(f"{lang_dir}/MPS-{lang_dir}-Employment-Agreement.pdf", ea_bytes)

                # Annex A
                annex_a_fn = build_annex_a(data, lang)
                aa_bytes = make_pdf(f"Annex A ({lang_dir})", annex_a_fn, lang)
                dept_label = {'housekeeping': 'A1', 'office': 'A2', 'pool_garden_handyman': 'A3'}.get(dept_raw, 'A')
                zf.writestr(f"{lang_dir}/MPS-{lang_dir}-Annex-{dept_label}.pdf", aa_bytes)

                # Annex B
                annex_b_fn = build_annex_b(data, lang)
                ab_bytes = make_pdf(f"Annex B ({lang_dir})", annex_b_fn, lang)
                zf.writestr(f"{lang_dir}/MPS-{lang_dir}-Annex-B-Performance-Bonus.pdf", ab_bytes)

    # Write ZIP to temp file and print path
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
        f.write(buf.getvalue())
        tmp = f.name

    print(tmp)
    sys.stdout.flush()

if __name__ == '__main__':
    main()
