"""Render curated research sections and figures as HTML, Markdown and PDF.

Use a Python environment containing reportlab (the bundled document runtime is
sufficient). Analysis is performed separately by report_study_campaign.py.
"""

import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/studies_01_07"


def main():
    content = json.loads((OUT / "report_sections.json").read_text(encoding="utf-8"))
    title = content["title"]
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ResearchBody",
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            spaceAfter=9,
            textColor=colors.HexColor("#233541"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            spaceAfter=12,
            textColor=colors.HexColor("#576778"),
        )
    )
    styles["Title"].textColor = colors.HexColor("#127e83")
    styles["Heading1"].textColor = colors.HexColor("#127e83")
    styles["Heading1"].fontSize = 19
    styles["Heading2"].fontSize = 13
    styles.add(ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["Cell"], textColor=colors.white))
    story = [
        Paragraph(html.escape(title), styles["Title"]),
        Paragraph(html.escape(content["subtitle"]), styles["ResearchBody"]),
        Spacer(1, 12),
    ]
    markdown = ["# " + title, "", content["subtitle"], ""]
    web = [
        f"<h1>{html.escape(title)}</h1><p class='subtitle'>{html.escape(content['subtitle'])}</p>"
    ]
    nav = []
    width, height = landscape(A4)
    usable_width, usable_height = width - 84, height - 86
    for number, section in enumerate(content["sections"]):
        identifier = f"section-{number}"
        nav.append(f"<a href='#{identifier}'>{html.escape(section['heading'])}</a>")
        if number:
            story.append(PageBreak())
        story.append(Paragraph(html.escape(section["heading"]), styles["Heading1"]))
        web.append(f"<section id='{identifier}'><h2>{html.escape(section['heading'])}</h2>")
        markdown.extend(["## " + section["heading"], ""])
        for block in section["blocks"]:
            if "paragraph" in block:
                text = block["paragraph"]
                story.append(KeepTogether([Paragraph(html.escape(text), styles["ResearchBody"])]))
                web.append("<p>" + html.escape(text) + "</p>")
                markdown.extend([text, ""])
            elif "table" in block:
                headers, rows = block["table"]["headers"], block["table"]["rows"]
                cells = [[Paragraph(html.escape(str(c)), styles["TableHead"]) for c in headers]] + [
                    [Paragraph(html.escape(str(c)), styles["Cell"]) for c in row] for row in rows
                ]
                table = Table(
                    cells,
                    colWidths=[usable_width / len(headers)] * len(headers),
                    repeatRows=1,
                    hAlign="LEFT",
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#127e83")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.HexColor("#f1f6f7"), colors.white],
                            ),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.extend([table, Spacer(1, 12)])
                web.append(
                    "<div class='table-scroll'><table><thead><tr>"
                    + "".join("<th>" + html.escape(str(c)) + "</th>" for c in headers)
                    + "</tr></thead><tbody>"
                    + "".join(
                        "<tr>"
                        + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row)
                        + "</tr>"
                        for row in rows
                    )
                    + "</tbody></table></div>"
                )
                markdown.extend(
                    [
                        "| " + " | ".join(headers) + " |",
                        "| " + " | ".join("---" for _ in headers) + " |",
                        *[
                            "| " + " | ".join(str(c).replace("|", "/") for c in row) + " |"
                            for row in rows
                        ],
                        "",
                    ]
                )
            elif "figure" in block:
                filename, caption = block["figure"], block["caption"]
                path = OUT / "figures" / (filename + ".png")
                iw, ih = ImageReader(str(path)).getSize()
                scale = min(usable_width / iw, (usable_height - 65) / ih)
                picture = Image(str(path), width=iw * scale, height=ih * scale)
                picture.hAlign = "CENTER"
                story.extend(
                    [
                        PageBreak(),
                        KeepTogether(
                            [
                                picture,
                                Spacer(1, 7),
                                Paragraph(html.escape(caption), styles["Caption"]),
                            ]
                        ),
                    ]
                )
                web.append(
                    f"<figure><a href='figures/{filename}.svg'><img src='figures/{filename}.png' alt='{html.escape(caption, quote=True)}'></a><figcaption>{html.escape(caption)}</figcaption></figure>"
                )
                markdown.extend([f"![{caption}](figures/{filename}.png)", "", caption, ""])
        web.append("</section>")
    footer = (
        "<section><h2>Download the evidence</h2><ul>"
        + "".join(
            f"<li><a href='{name}'>{label}</a></li>"
            for name, label in [
                ("research_report.pdf", "PDF report"),
                ("condition_results.csv", "All presentation condition estimates"),
                ("paired_defense_contrasts.csv", "Paired defense contrasts"),
                ("pilot_results.csv", "Separate pilot estimates"),
                ("run_provenance.csv", "95-run provenance ledger"),
                ("audit.json", "Dataset audit"),
                ("combined_crisis_diagnostic.json", "Combined-crisis budget and expiry diagnostic"),
                ("source_manifests.json", "Engine source manifests and event archive metadata"),
            ]
        )
        + "</ul></section>"
    )
    css = "body{margin:0;background:#f1f5f6;color:#233541;font:17px/1.65 system-ui,sans-serif}main{max-width:1180px;margin:auto;background:white;padding:55px}h1{font-size:42px;line-height:1.15;color:#127e83}h2{border-top:2px solid #e0ecec;padding-top:30px;color:#127e83}nav{display:flex;gap:12px;flex-wrap:wrap;font-size:14px}a{color:#127e83}.subtitle{color:#576778}figure{margin:30px 0}img{width:100%;height:auto}figcaption{font-size:14px;color:#576778}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th{background:#127e83;color:white;text-align:left}td,th{padding:9px;border-bottom:1px solid #dce5e8}tr:nth-child(even){background:#f1f6f7}@media(max-width:700px){main{padding:22px}h1{font-size:31px}}"
    (OUT / "index.html").write_text(
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"
        + html.escape(title)
        + "</title><style>"
        + css
        + "</style><main><nav>"
        + "".join(nav)
        + "</nav>"
        + "".join(web)
        + footer
        + "</main></html>",
        encoding="utf-8",
    )
    (OUT / "RESEARCH_REPORT.md").write_text("\n".join(markdown), encoding="utf-8")

    def page_footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#576778"))
        canvas.drawString(
            42, 24, "Synthetic fan-governance experiments | Studies 01-07 | November 2026"
        )
        canvas.drawRightString(width - 42, 24, str(document.page))

    document = SimpleDocTemplate(
        str(OUT / "research_report.pdf"),
        pagesize=landscape(A4),
        rightMargin=42,
        leftMargin=42,
        topMargin=38,
        bottomMargin=42,
        title=title,
        author="Football Fan Governance Research Project",
    )
    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print("Published PDF, HTML, and Markdown research reports")


if __name__ == "__main__":
    main()
