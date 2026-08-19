from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

pdfmetrics.registerFont(TTFont("Oswald", "oswald/Oswald-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Oswald-Bold", "oswald/Oswald-Bold.ttf"))

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