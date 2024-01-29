import argparse
import csv
import reportlab
from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

cert = "template.pdf"

pdfmetrics.registerFont(TTFont("Inter", "Inter-Regular.ttf"))


def create_certificates(names: list):
    output = PdfWriter()

    for name in names:
        packet = io.BytesIO()
        template = PdfReader(open(cert, "rb"))
        page = template.pages[0]
        c = reportlab.pdfgen.canvas.Canvas(packet, pagesize=(
            page.mediabox.width, page.mediabox.height))
        c.setFont("Inter", 40)
        c.drawCentredString(420, 217, name)
        c.save()

        packet.seek(0)
        new_pdf = PdfReader(packet)
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

    output_stream = open("certificates.pdf", "wb")
    output.write(output_stream)
    output_stream.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create personalized certificates for newcomers")
    parser.add_argument("filename", help="name of registrations CSV")
    parser.add_argument("-a", "--all", action="store_true",
                        help="Generate for all 2024 IDs rather than just "
                             "newcomers")
    args = parser.parse_args()

    persons = []

    with open(args.filename) as reg_file:
        next(reg_file)
        reg = csv.reader(reg_file)
        for person in reg:
            if person[3] == "" or (person[3][:4] == "2024" and args.all):
                persons.append(person[1])

    create_certificates(persons)
