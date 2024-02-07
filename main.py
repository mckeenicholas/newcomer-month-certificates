import argparse
import sys

import reportlab
import requests
from PyPDF2 import PdfWriter, PdfReader
import io
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import glob

template_path = "template.pdf"
fonts_dir = "Fonts"  # Folder containing all fonts being
Y = 217

# Set default font here
default_font_path = "Fonts/Inter-Regular.ttf"

default_font = default_font_path[:-3]

# Fallback fonts for characters not encoded in default
fonts = [(default_font, default_font_path)]
fonts.extend([(name[:-3], name) for name in glob.glob(f"{fonts_dir}/*.ttf")
              if name != default_font])

font_widths = {}

for font_name, file in fonts:
    font = TTFont(font_name, file)
    pdfmetrics.registerFont(font)
    font_widths[font_name] = font.face.charWidths


def create_certificates(names: list, comp_name: str):
    output = PdfWriter()

    total = len(names) - 1
    print("")

    for i, name in enumerate(names):
        # Create a progress bar:
        sys.stdout.write('\x1b[1A')
        sys.stdout.write('\x1b[2K')
        percent_done = i/total
        print(f"[{'#' * int(percent_done*30)}{'-' * (30-int(percent_done*30))}] {i}/{total} Certificates Generated")

        packet = io.BytesIO()
        template = PdfReader(open(template_path, "rb"))
        page = template.pages[0]
        c = reportlab.pdfgen.canvas.Canvas(packet, pagesize=(
            page.mediabox.width, page.mediabox.height))
        page_width = int(page.mediabox.width)
        c.setFont(default_font, 40)

        if "(" in name:
            try:
                alt_name = name[name.index("(") + 1:name.index(")")]
                ascii_name = name[:name.index("(") - 1]
            except ValueError:
                print(
                    f"Error creating certificate for {name} (likely incorrectly"
                    f" formatted profile data)")
                continue

            used_font = ""
            for f_name, width in font_widths.items():
                if all(ord(char) in width for char in alt_name):
                    used_font = f_name
                    break

            if used_font == "":
                print(f"Unable to find font supporting: {alt_name}")
                continue

            alt_width = stringWidth(alt_name, used_font, 40)
            full_offset = stringWidth(ascii_name + " ()", default_font,
                                      40) + alt_width
            ascii_offset = stringWidth(ascii_name + " (", default_font,
                                       40) - alt_width - 7
            end_offset = full_offset - stringWidth(")", default_font,
                                                   40)

            c.drawString((page_width - full_offset) / 2, Y, ascii_name + "(")
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

    output_stream = open(f"{comp_name}-certificates.pdf", "wb")
    output.write(output_stream)
    output_stream.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create personalized certificates for newcomers")
    parser.add_argument("compID", help="WCA competition ID")
    parser.add_argument("-a", "--all", action="store_true",
                        help="Generate for all 2024 IDs rather than just "
                             "newcomers")
    parser.add_argument("-o", "--omit", action="store_true",
                        help="Omit non-ASCII characters from names")
    args = parser.parse_args()

    persons = []

    url = f"https://www.worldcubeassociation.org/api/v0/competitions/{args.compID}/wcif/public"

    try:
        response = requests.get(url)
    except requests.exceptions as e:
        raise SystemExit(e)

    if response.status_code != 200:
        raise NameError(f"Competition {args.compID} not found.")

    data = response.json()

    for person in data["persons"]:
        if person["registration"] is not None and (person["wcaId"] is None or (person["wcaId"].startswith("2024") and args.all)):
            if args.omit and "(" in person["name"]:
                persons.append(person["name"][:person["name"].index("(") - 1])
            else:
                persons.append(person["name"])

    persons.sort()
    create_certificates(persons, args.compID)
