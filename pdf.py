from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from datetime import datetime, timezone, timedelta

pdfmetrics.registerFont(TTFont("Oswald", "oswald/Oswald-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Oswald-Bold", "oswald/Oswald-Bold.ttf"))
pdfmetrics.registerFontFamily("Oswald", normal="Oswald", bold="Oswald-Bold")

def create_reimbursement(user, _approved: bool, place: str, name: str, number: str, mail: str, bank: str, cnumber:str, anumber: str, recipient: str, total: float, description: str, receipt: list[str]):
    pdf = SimpleDocTemplate(f"reimbursement-{user.id}.pdf", pagesize=A4, topMargin=1*cm)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title", fontName="Oswald-Bold", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=18)
    body_style = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=14, leading=16)
    body_style_small = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=10)

    content = []

    logo = Image("P-Logga_LOD1_white1.png")
    logo.drawHeight = 2.5*cm
    logo.drawWidth = 2.5*cm

    approved = "Ja" if _approved else "Nej"
    header_text = Paragraph("PRODUKTIONSSEKTIONEN, THS", ParagraphStyle("TopTitle", fontName="Oswald-Bold", fontSize=12))

    header = Table([[logo, header_text]], colWidths=[2.5*cm, 13*cm])

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0,0), (-1, -1), 0),
        ("RIGHTPADDING", (0,0), (-1, -1), 0),
        ("TOPPADDING", (0,0), (-1, -1), 0),
        ("BOTTOMPADDING", (0,0), (-1, -1), 0)
    ]))

    content.append(header)
    content.append(Spacer(1, 0.5*cm))
    content.append(Paragraph("ERSÄTTNINGSBLANKETT", title_style))

    content.append(Paragraph("OBLIGATORISK INFORMATION", ParagraphStyle("TopTitle", fontName="Oswald-Bold", fontSize=14)))
    content.append(Spacer(1, 0.2*cm))

    checkbox = Table([[""]], colWidths=[0.5*cm], rowHeights=[0.5*cm])
    checkbox.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black)
    ]))
    content.append(Paragraph(f"Jag bekräftar att jag meddelat om inköpet och det har godkänts i förväg av berörd attestant: {approved}", body_style))

    top_body = Table([[[Paragraph(f"Kostnadsställe: {place}", body_style), Paragraph("Styrelsen, QP, Mottagning, Studienämnden, Aktivitetsnämnden, etc.", body_style_small)]]], colWidths=[pdf.width])
    top_body.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.black),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))

    content.append(Spacer(1, 0.5*cm))
    content.append(top_body)

    entries = [
        [Paragraph(f"Namn: {name}", body_style)],
        [Paragraph(f"Telefonnummer: {number}", body_style)],
        [Paragraph(f"Mail: {mail}", body_style)],
        [Paragraph(f"Bank: {bank}", body_style)],
        [Paragraph(f"Clearingnummer: {cnumber}", body_style)],
        [Paragraph(f"Kontonummer: {anumber}", body_style)],
        [Paragraph(f"Betalningsmottagare: {recipient}", body_style)],
        [Paragraph(f"Summa: {total} SEK", body_style)],
        [Paragraph(f"Beskrivning av inköp: {description}", body_style)]
    ]
    bottom_body = Table(entries, colWidths=[pdf.width], rowHeights=[1*cm]*8 + [2.3*cm])
    bottom_body.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP")
    ]))

    content.append(Spacer(1, 0.5*cm))
    content.append(bottom_body)

    content.append(Paragraph("Uppgifterna du lämnat kommer lagras i bokföringssyfte för Produktionssektionen, THS. I enlighet med bokföringslagen och dataskyddsförordningen, GDPR.", body_style))
    content.append(Spacer(1, 0.5*cm))
    content.append(Paragraph("ATTESTERING", ParagraphStyle("TopTitle", fontName="Oswald-Bold", fontSize=14)))
    content.append(Spacer(1, 0.3*cm))
    content.append(Paragraph("Attestant för kostnadsstället godkänner ansökan om ersättning och ansvarar för att den följer sektionens stadgar, reglementen och riktlinjer.", body_style))

    content.append(Spacer(1, 2*cm))
    signatures = Table(
        [["", "", ""], [Paragraph("Underskrift", body_style), "", Paragraph("Namnförtydligande", body_style)]],
        colWidths=[pdf.width/3, pdf.width/3, pdf.width/3],
        rowHeights=[0.8*cm, 0.1*cm]
        )
    signatures.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (0,0), 1, colors.black),
        ("LINEABOVE", (1,0), (1,0), 1, colors.white),
        ("LINEABOVE", (-1,0), (-1,0), 1, colors.black),
        ("ALIGN", (0,1), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,1), (-1,1), 8),
    ]))

    content.append(signatures)

    content.append(PageBreak())

    for i, im in enumerate(receipt):
        img = Image(im)
        max_width = pdf.width
        max_height = pdf.height - 20

        scale = min(
            max_width / img.imageWidth,
            max_height / img.imageHeight
        )

        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        content.append(img)

        if i < len(receipt) - 1:
            content.append(PageBreak())

    content.append(Spacer(1, 0.3*cm))
    divider = Table(
        [[""]], colWidths=[pdf.width],
        rowHeights=[0.1*cm]
    )
    divider.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (0,0), 1, colors.black),
        ("ALIGN", (0,1), (-1,-1), "CENTER")
    ]))
    content.append(divider)
    content.append(Paragraph(f"Denna ersättningsblankett skapades av Heidrun på begäran av individ {user.name} ({user.id})", body_style_small))

    pdf.build(content)

def create_invoice(guild, bank, index, items, due, customer, address):
    def get_end(date):
        if date.strftime('%d')[1] == "1":
            date_ending = "st"
        elif date.strftime('%d')[1] == "2":
            date_ending = "nd"
        elif date.strftime('%d')[1] == "3":
            date_ending = "rd"
        else:
            date_ending = "th"
        return date_ending

    total = 0
    for item in items:
        total += item.price * item.quantity

    pdf = SimpleDocTemplate(f"invoice-{guild.id}-{index}.pdf", pagesize=A4, topMargin=1*cm)
    background = colors.HexColor("#FFF2F2")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", fontName="Oswald-Bold", parent=styles["Heading1"], alignment=TA_RIGHT, fontSize=22)
    body_styler = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=14, leading=16)
    body_stylel = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=14, leading=16)
    body_styler_l = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=18, leading=16)
    body_stylel_l = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=18, leading=16)
    body_style_boldr = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=14, leading=16)
    body_style_boldl = ParagraphStyle("Body", fontName="Oswald-Bold", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=14, leading=16)
    body_style_small = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=10)

    content = []

    # INFO
    logo = Image("P-Logga_LOD1_white1.png")
    logo.drawHeight = 3*cm
    logo.drawWidth = 3*cm

    info = [
        Paragraph("INVOICE", title_style),
        Paragraph(f"<b>{bank.get('recipient')}</b>", body_styler),
        Paragraph(f"{bank.get('address')}", body_styler),
        Paragraph(f"{bank.get('contact')}", body_styler)
    ]

    # VERIFICATION
    date_send = datetime.now(timezone.utc)
    date_due = datetime.fromisoformat(due)
    date_send_ed = get_end(date_send)
    date_due_ed = get_end(date_due)

    header = Table(
        [[logo, info]],
        colWidths=[
            5 * cm,
            pdf.width - 5 * cm
        ]
    )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    content.append(header)

    invoice_info = Table(
        [
            [
                Paragraph(f"Invoice No#: {index}", body_stylel),
                Paragraph(f"{total:.2f} SEK", title_style)
            ],
            [
                Paragraph(f"Invoice date: {date_send.strftime(f'%d{date_send_ed} %B %Y') if date_send.strftime(f'%d')[0] != "0" else date_send.strftime(f'%d{date_send_ed} %B %Y')[1:]}", body_stylel),
                Paragraph("AMOUNT DUE", body_styler),
            ],
            [
                Paragraph(f"Due date: {date_due.strftime(f'%d{date_due_ed} %B %Y') if date_due.strftime(f'%d')[0] != "0" else date_due.strftime(f'%d{date_due_ed} %B %Y')[1:]}", body_stylel),
                ""
            ]
        ],
        colWidths=[
            pdf.width - 5 * cm,
            5 * cm
        ]
    )

    invoice_info.setStyle(TableStyle([
        #("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        #("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, -1), background),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (1, -1), "LEFT"),
        ("ALIGN", (2, 0), (3, -1), "RIGHT"),

        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5)
    ]))

    content.append(Spacer(1, 0.5 * cm))
    content.append(invoice_info)

    # CONTENTS
    content.append(Spacer(1, 0.5 * cm))

    bill_to = Table(
        [
            [Paragraph("BILL TO:", body_style_boldl)],
            [Paragraph(customer, body_stylel)],
            [Paragraph(address, body_stylel)],
        ],
        colWidths=[pdf.width],
    )

    bill_to.setStyle(TableStyle([
        #("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        #("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),

        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3)
    ]))

    content.append(bill_to)

    item_data = [
        [
            Paragraph("#", body_style_boldl),
            Paragraph("ITEMS", body_style_boldl),
            Paragraph("QTY/HRS", body_style_boldr),
            Paragraph("PRICE", body_style_boldr),
            Paragraph("AMOUNT (SEK)", body_styler)
        ]
    ]

    for i, item in enumerate(items):
        amount = item.quantity * item.price

        item_data.append([
            Paragraph(f"{i+1}", body_stylel),
            Paragraph(item.name, body_stylel),
            Paragraph(f"{item.quantity}", body_styler),
            Paragraph(f"{item.price:.2f} kr", body_styler),
            Paragraph(f"{amount:.2f} kr", body_styler)
        ])

    item_table = Table(
        item_data,
        colWidths=[
            pdf.width * 0.05,
            pdf.width * 0.40,
            pdf.width * 0.15,
            pdf.width * 0.175,
            pdf.width * 0.225
        ]
    )

    item_table.setStyle(TableStyle([
        # Header
        #("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),

        # Bottom border
        ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),

        # Alignment
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    content.append(Spacer(1, 0.5 * cm))
    content.append(item_table)

    # BANK INFO
    content.append(Spacer(1, 0.5 * cm))
    bank_info = Table(
        [
            [
                Paragraph(f"Bank Transfer (BG): {bank.get('bg')}", body_stylel),
                Paragraph(f"Subtotal: {total:.2f} kr", body_style_boldr)
            ],
            [
                Paragraph(f"Banknumber: {bank.get('bnumber')}", body_stylel),
                Paragraph(f"<b>Total: </b>{total:.2f} SEK", body_styler_l),
            ],
            [
                Paragraph(f"Clearing number: {bank.get('cnumber')}", body_stylel),
                Paragraph("Amount Paid: 0.00 SEK", body_style_boldr)
            ],
            [
                Paragraph(f"Bank name: {bank.get('name')}", body_stylel),
                Paragraph(f"<b>Amount Due: </b>{total:.2f} SEK", body_styler_l)
            ],
            [
                Paragraph(f"Recipient: {bank.get('recipient')}", body_stylel),
                ""
            ],
            [
                Paragraph(f"Swish: {bank.get('swish')}", body_stylel),
                ""
            ]
        ],
        colWidths=[
            pdf.width * 0.5,
            pdf.width * 0.5
        ]
    )

    bank_info.setStyle(TableStyle([
        # Top and bottom borders
        #("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        #("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),

        ("BACKGROUND", (0, 0), (0, -1), background),

        # Vertical alignment
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        # Left column
        ("ALIGN", (0, 0), (0, -1), "LEFT"),

        # Right column
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    content.append(bank_info)
    pdf.build(content)

def create_invoice_p(guild, bank, index, items, due, customer, description):
    def get_end(date):
        if date.strftime('%d')[1] == "1":
            date_ending = "st"
        elif date.strftime('%d')[1] == "2":
            date_ending = "nd"
        elif date.strftime('%d')[1] == "3":
            date_ending = "rd"
        else:
            date_ending = "th"
        return date_ending

    total = 0
    for item in items:
        total += item.price * item.quantity

    pdf = SimpleDocTemplate(f"invoice-{guild.id}-{index}.pdf", pagesize=A4, topMargin=1*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", fontName="Oswald", parent=styles["Heading1"], fontSize=22)
    body_style_l = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_LEFT, fontSize=14)
    body_style_r = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_RIGHT, fontSize=14)
    body_style_c = ParagraphStyle("Body", fontName="Oswald", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=14)

    content = []

    # INFO
    content.append(Paragraph("FAKTURA", title_style))
    content.append(Spacer(1, 0.1 * cm))

    logo = Image("P-Logga_LOD1_white1.png")
    logo.drawHeight = 3*cm
    logo.drawWidth = 3*cm

    info = [
        Paragraph(f"<b>{bank.get('recipient')}</b>", body_style_l),
        Paragraph(f"{bank.get('address')}", body_style_l),
        Paragraph(f"{bank.get('post')}", body_style_l),
        Paragraph(f"BG-nmr: {bank.get('bg')}", body_style_l),
        Paragraph(f"Org.nummer: {bank.get('org_number')}", body_style_l)
    ]

    seller_ref = [
        Paragraph("<u>Vår referens</u>", body_style_l),
        Paragraph(f"{bank.get('contact').get('name')}", body_style_l),
        Paragraph(f"{bank.get('contact').get('position')}", body_style_l),
        Paragraph(f"{bank.get('contact').get('mail')}", body_style_l)
    ]

    header = Table(
        [[logo, info, seller_ref]],
        colWidths=[
            3.5 * cm,
            7 * cm,
            pdf.width - 10.5 * cm
        ]
    )

    header.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    content.append(header)

    # DESCRIPTION
    content.append(Spacer(1, 0.5 * cm))
    content.append(Paragraph(description, body_style_l))

    # CUSTOMER REF
    seller_ref = [
        Paragraph("Er referens", body_style_l),
        Paragraph(f"{customer.get('contact').get('name')}", body_style_l),
        Paragraph(f"{customer.get('contact').get('mail')}", body_style_l)
    ]

    content.append(Spacer(1, 0.5 * cm))
    content.append(Paragraph("<u>Er referens</u>", body_style_l))
    content.append(Paragraph(f"{customer.get('contact').get('name')}", body_style_l))
    content.append(Paragraph(f"{customer.get('contact').get('mail')}", body_style_l))
    if customer.get('contact').get('address') is not None:
        content.append(Paragraph(f"{customer.get('contact').get('address')}", body_style_l))

    # SPECIFICATION
    content.append(Spacer(1, 0.5 * cm))
    content.append(Paragraph("<b>Specifikation</b>", body_style_l))

    date_send = datetime.now(timezone.utc)
    date_due = datetime.fromisoformat(due)

    info = Table(
        [[
            Paragraph(f"Fakturanr: {index}", body_style_l), 
            Paragraph(f"Faktureringsdag: {date_send.strftime(f'%Y-%m-%d')}", body_style_c), 
            Paragraph(f"Förfallodag: {date_due.strftime(f'%Y-%m-%d')}", body_style_r)
        ]],
        colWidths=[
            5 * cm,
            6 * cm,
            5 * cm
        ]
    )

    info.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    content.append(Spacer(1, 0.5 * cm))
    content.append(info)

    # ITEMS
    item_data = [
        [
            Paragraph("<b><u>Benämning</u></b>", body_style_l),
            Paragraph("<b><u>á-pris</u></b>", body_style_r),
            Paragraph("<b><u>Antal</u></b>", body_style_c),
            Paragraph("<b><u>Belopp</u></b>", body_style_r)
        ]
    ]

    total = 0
    for item in items:
        quantity = item.quantity
        price = item.price
        amount = quantity * price
        total += amount

        item_data.append([
            Paragraph(item.name, body_style_l),
            Paragraph(f"{price}", body_style_r),
            Paragraph(f"{quantity}", body_style_c),
            Paragraph(f"{amount} kr", body_style_r)
        ])
    item_data.append([
        Paragraph("<b>Totalt</b>", body_style_l),
        Paragraph(""),
        Paragraph(""),
        Paragraph(f"<b>{total} kr</b>", body_style_r)
    ])

    item_table = Table(
        item_data,
        colWidths=[
            8 * cm,
            3 * cm,
            2 * cm,
            3 * cm
        ],
        repeatRows=1
    )

    item_table.setStyle(TableStyle([
        #("GRID", (0, 0), (-1, -1), 1, colors.black),

        # Header
        #("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        #("FONTNAME", (0, 0), (-1, 0), "Oswald-Bold"),

        # Alignment
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    content.append(Spacer(1, 0.5 * cm))
    content.append(item_table)

    # PAYMENT INFO
    payment_data = [
        [
            Paragraph("<b>Bankgiro</b>", body_style_l),
            Paragraph("<b>Mottagare</b>", body_style_l),
            Paragraph("<b>Meddelande</b>", body_style_l),
            Paragraph("<b>Att betala</b>", body_style_l)
        ],
        [
            Paragraph(f"{bank.get('bg')}", body_style_l),
            Paragraph(f"{bank.get('recipient')}", body_style_l),
            Paragraph("Fakturanummer", body_style_l),
            Paragraph(f"{total} kr", body_style_l)
        ]
    ]

    payment_table = Table(
        payment_data,
        colWidths=[
            3 * cm,
            5 * cm,
            4 * cm,
            4 * cm
        ]
    )

    payment_table.setStyle(TableStyle([
        #("GRID", (0, 0), (-1, -1), 1, colors.black),

        # Header
        #("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        #("FONTNAME", (0, 0), (-1, 0), "Oswald-Bold"),

        # Alignment
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),

        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    content.append(Spacer(1, 1 * cm))
    content.append(payment_table)

    # ENDING
    content.append(Spacer(1, 1 * cm))
    content.append(Paragraph(f"Föreningen {bank.get('recipient')} är ej momspliktig.", body_style_l))

    pdf.build(content)