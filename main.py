import argparse
import csv
import reportlab
from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import glob

cert = "template.pdf"
fonts_dir = "Fonts" # Folder containing all fonts being
Y = 217

# Set default font here
fonts = [("Inter", "Fonts/Inter-Regular.ttf")]

# Fallback fonts for characters not encoded in default
fonts.extend([(name[:-3], name) for name in glob.glob(f"{fonts_dir}/*.ttf")])

font_widths = {}

for font_name, file in fonts:
    font = TTFont(font_name, file)
    pdfmetrics.registerFont(font)
    font_widths[font_name] = font.face.charWidths


def create_certificates(names: list):
    output = PdfWriter()

    for name in names:
        packet = io.BytesIO()
        template = PdfReader(open(cert, "rb"))
        page = template.pages[0]
        c = reportlab.pdfgen.canvas.Canvas(packet, pagesize=(
            page.mediabox.width, page.mediabox.height))
        page_width = int(page.mediabox.width)
        c.setFont("Inter", 40)

        if "(" in name:
            alt_name = name[name.index("(") + 1:name.index(")")]
            ascii_name = name[:name.index("(") - 1]

            used_font = ""
            for f_name, width in font_widths.items():
                if all(ord(char) in width for char in alt_name):
                    used_font = f_name
                    break

            if used_font == "":
                print(f"Unable to find font for: {alt_name}")
                continue

            alt_width = stringWidth(alt_name, used_font, 40)
            full_offset = stringWidth(ascii_name + " ()", "Inter",
                                      40) + alt_width
            ascii_offset = stringWidth(ascii_name + " (", "Inter",
                                       40) - alt_width - 7
            end_offset = full_offset - stringWidth(")", "Inter",
                                                   40)

            c.drawString((page_width - full_offset) / 2, Y, ascii_name + " (")
            c.drawString((page_width + end_offset) / 2, Y, ")")

            c.setFont(used_font, 40)
            c.drawString((page_width + ascii_offset) / 2, Y, alt_name)

        else:
            c.drawCentredString(page_width / 2, Y, name)

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

    with open(args.filename, encoding='utf8') as reg_file:
        next(reg_file)
        reg = csv.reader(reg_file)
        for person in reg:
            if person[3] == "" or (person[3][:4] == "2024" and args.all):
                persons.append(person[1])

    persons.sort()

    create_certificates(persons)
