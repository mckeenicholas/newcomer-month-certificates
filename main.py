import argparse
import sys
import io
import os
import glob
import requests
from tqdm import tqdm
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

TEMPLATE_PATH = "template.pdf"
FONTS_DIR = "Fonts"
DEFAULT_FONT_PATH = "Fonts/Inter-Regular.ttf"
DEFAULT_FONT = DEFAULT_FONT_PATH[:-4]
Y_COORDINATE = 217


def load_fonts():
    """
    Loads fonts into reportlab, and returns a dict with the width of each font for alignment
    """
    fonts = [(DEFAULT_FONT, DEFAULT_FONT_PATH)]
    fonts.extend(
        [
            (font_path[:-4], font_path)
            for font_path in glob.glob(f"{FONTS_DIR}/*.ttf")
            if font_path != DEFAULT_FONT_PATH
        ]
    )

    font_widths = {}
    for font_name, font_file in fonts:
        font = TTFont(font_name, font_file)
        pdfmetrics.registerFont(font)
        font_widths[font_name] = font.face.charWidths

    return fonts, font_widths


def create_certificates(names, competition_name, output_dir="."):
    """
    Main function for creating certificates, writes 1 PDF file with the person's name overlayed for each name in `names`
    """
    output = PdfWriter()
    _, font_widths = load_fonts()

    for name in tqdm(names, desc="Generating Certificates", unit="certificates"):
        packet = io.BytesIO()
        template = PdfReader(open(TEMPLATE_PATH, "rb"))
        page = template.pages[0]
        page_width = int(page.mediabox.width)
        c = canvas.Canvas(packet, pagesize=(page.mediabox.width, page.mediabox.height))
        c.setFont(DEFAULT_FONT, 40)

        if "(" in name:
            try:
                alt_name = name[name.index("(") + 1 : name.index(")")]
                ascii_name = name[: name.index("(") - 1]
            except ValueError:
                tqdm.write(
                    f"Error creating certificate for {name} (incorrectly formatted profile data)"
                )
                continue

            used_font = next(
                (
                    f_name
                    for f_name, widths in font_widths.items()
                    if all(ord(char) in widths for char in alt_name)
                ),
                "",
            )

            if not used_font:
                tqdm.write(f"Unable to find font supporting: {alt_name}")
                continue

            alt_width = stringWidth(alt_name, used_font, 40)
            full_offset = stringWidth(ascii_name + " ()", DEFAULT_FONT, 40) + alt_width
            ascii_offset = (
                stringWidth(ascii_name + " (", DEFAULT_FONT, 40) - alt_width - 7
            )
            end_offset = full_offset - stringWidth(")", DEFAULT_FONT, 40)

            c.drawString((page_width - full_offset) / 2, Y_COORDINATE, ascii_name + "(")
            c.drawString((page_width + end_offset) / 2, Y_COORDINATE, ")")

            c.setFont(used_font, 40)
            c.drawString((page_width + ascii_offset) / 2, Y_COORDINATE, alt_name)
        else:
            c.drawCentredString(page_width / 2, Y_COORDINATE, name)

        c.save()

        packet.seek(0)
        new_pdf = PdfReader(packet)
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)

    output_path = os.path.join(output_dir, f"{competition_name}-certificactes.pdf")
    with open(output_path, "wb") as output_stream:
        output.write(output_stream)


def process_name(name, should_skip):
    """
    Process a person's name based on skip argument.
    If skip is True and name contains non-ASCII characters in parentheses,
    return only the ASCII part before the parentheses.
    """
    if should_skip and "(" in name:
        return name[: name.index("(") - 1]
    return name


def is_eligible_participant(person, include_all_2025):
    """
    Check if a person is eligible for a certificate based on registration and WCA ID.
    """
    # Must have an active registration
    if person["registration"] is None:
        return False

    # Either a newcomer (no WCA ID) or a 2025 ID if include_all_2025 is True
    has_no_id = person["wcaId"] is None
    is_2025_competitor = person["wcaId"] is not None and person["wcaId"].startswith(
        "2025"
    )

    return has_no_id or (is_2025_competitor and include_all_2025)


def get_eligible_persons(data, args):
    """
    Get a list of eligible persons' names for certificates.
    """
    eligible_persons = []

    for person in data["persons"]:
        if is_eligible_participant(person, args.all):
            processed_name = process_name(person["name"], args.skip)
            eligible_persons.append(processed_name)

    return sorted(eligible_persons)


def main():
    parser = argparse.ArgumentParser(
        description="Create personalized certificates for newcomers"
    )
    parser.add_argument("compID", help="WCA competition ID")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include all 2025 IDs, not just newcomers",
    )
    parser.add_argument(
        "-s", "--skip", action="store_true", help="Omit non-ASCII characters from names"
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        default=".",
        help="Output directory for generated certificates",
    )
    args = parser.parse_args()

    wca_url = f"https://www.worldcubeassociation.org/api/v0/competitions/{args.compID}/wcif/public"

    try:
        response = requests.get(wca_url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise SystemExit(f"Error fetching competition data: {e}")

    data = response.json()
    persons = get_eligible_persons(data, args)

    persons.sort()
    create_certificates(persons, args.compID, args.out_dir)


if __name__ == "__main__":
    main()
