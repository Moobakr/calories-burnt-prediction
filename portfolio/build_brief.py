"""Build the two-page aggregate-evidence brief; no data/model/test evaluation."""

import argparse
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
GREEN = colors.HexColor("#164A3E")
INK = colors.HexColor("#18332E")
MUTED = colors.HexColor("#52625C")
PALE = colors.HexColor("#EDF3ED")
AMBER = colors.HexColor("#A06129")
WIDTH = A4[0] - 84


class CoverageChart(Flowable):
    def __init__(self, groups):
        super().__init__()
        self.groups = groups
        self.width, self.height = WIDTH, 151

    def draw(self):
        c, left, bar_width = self.canv, 154, 284
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        for tick in (0, 25, 50, 75, 100):
            x = left + bar_width * tick / 100
            c.setStrokeColor(colors.HexColor("#D8E0DA"))
            c.line(x, 35, x, 126)
            c.drawCentredString(x, 21, str(tick))
        for index, group in enumerate(self.groups):
            y = 109 - index * 31
            coverage = group["coverage"] * 100
            c.setFillColor(INK)
            c.setFont("Helvetica", 9.3)
            c.drawString(0, y + 2, f"{group['group']} min  (n={group['n']:,})")
            c.setFillColor(GREEN if coverage >= 90 else AMBER)
            c.rect(left, y, bar_width * coverage / 100, 16, fill=1, stroke=0)
            c.setFont("Helvetica-Bold", 9)
            c.drawRightString(WIDTH - 2, y + 3, f"{coverage:.2f}%")
        x = left + bar_width * .9
        c.setDash(3, 2)
        c.setStrokeColor(AMBER)
        c.line(x, 35, x, 130)
        c.setDash()
        c.setFillColor(AMBER)
        c.setFont("Helvetica", 8.5)
        c.drawString(left, 138, "Observed coverage of recorded test labels")
        c.drawString(left, 4, "0-100% scale; dashed line = 90% nominal target")


def build(output):
    metrics = json.loads((ROOT / "docs/FINAL_EVALUATION_METRICS.json").read_bytes())
    verification = json.loads((ROOT / "docs/STATIC_DEMO_VERIFICATION.json").read_bytes())
    systems = {row["name"]: row for row in metrics["results"]}
    primary = systems["xgboost_heart_rate"]
    groups = [row for row in primary["test"]["groups"] if row["axis"] == "duration"]
    assert verification["synthetic_sessions_verified"] == 5854
    assert round(primary["test"]["overall"]["mae"], 3) == .978
    assert len(groups) == 3
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("EyebrowCustom", fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=GREEN, spaceAfter=9))
    styles.add(ParagraphStyle("TitleCustom", fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=INK, spaceAfter=8))
    styles.add(ParagraphStyle("SubCustom", fontName="Helvetica", fontSize=9, leading=13, textColor=MUTED, spaceAfter=13))
    styles.add(ParagraphStyle("LeadCustom", fontName="Helvetica", fontSize=11, leading=15, textColor=INK, spaceAfter=13))
    styles.add(ParagraphStyle("HeadCustom", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=GREEN, spaceBefore=11, spaceAfter=6))
    styles.add(ParagraphStyle("BodyCustom", fontName="Helvetica", fontSize=9.4, leading=13, textColor=INK, spaceAfter=7))
    styles.add(ParagraphStyle("SmallCustom", fontName="Helvetica", fontSize=8.4, leading=11.5, textColor=MUTED, spaceAfter=6))
    styles.add(ParagraphStyle("CardValue", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=GREEN, alignment=TA_CENTER))
    styles.add(ParagraphStyle("CardLabel", fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER))
    story = []
    def p(text, style="BodyCustom"):
        story.append(Paragraph(text, styles[style]))
    p("CALORIE LAB / APPLIED MACHINE LEARNING", "EyebrowCustom")
    p("Sensor requirements<br/>and reliability", "TitleCustom")
    p("Moobakr | AI-assisted research implementation | 11 October 2026", "SubCustom")
    p("Temperature could be omitted under a predefined benchmark rule when heart rate was available. A low overall error still concealed a long-session reliability gap.", "LeadCustom")
    cards = Table([[Paragraph("0.978", styles["CardValue"]), Paragraph("6 vs 7", styles["CardValue"]), Paragraph("79.54%", styles["CardValue"])],
                   [Paragraph("primary test MAE*", styles["CardLabel"]), Paragraph("required input fields", styles["CardLabel"]), Paragraph("long-session interval coverage", styles["CardLabel"])]], colWidths=[WIDTH/3]*3)
    cards.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("TOPPADDING",(0,0),(-1,0),10),("BOTTOMPADDING",(0,1),(-1,1),10)]))
    story += [cards, Spacer(1, 7)]
    p("A controlled comparison", "HeadCustom")
    p("The supplied 15,000-record CSV yielded 14,999 observations after one exact duplicate was removed. IDs were excluded from inputs. Fixed partitions contain 8,999 development, 3,000 calibration and 3,000 test records; five development folds are shared across comparisons.")
    p("A mean baseline, four Ridge pipelines and four XGBoost pipelines were compared. Each XGBoost input set received the same 30-configuration search. Calibration separates 1,500 interval-fit from 1,500 interval-audit records. Model selection and thresholds were frozen before a one-time final test release; test results did not retune the system.")
    p("Frozen XGBoost results", "HeadCustom")
    rows = [["Available inputs", "Fields", "Test MAE*", "Test RMSE*"]]
    for mode, label, fields in (("duration","Duration only",1),("basic","Basic measurements",5),("heart_rate","Basic + heart rate (primary)",6),("full","Full, including temperature",7)):
        value = systems[f"xgboost_{mode}"]["test"]["overall"]
        rows.append([label,str(fields),f"{value['mae']:.3f}",f"{value['rmse']:.3f}"])
    table = Table(rows, colWidths=[255,52,99,WIDTH-406], repeatRows=1)
    table.setStyle(TableStyle([("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTNAME",(0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),9),("TEXTCOLOR",(0,0),(-1,0),colors.white),("BACKGROUND",(0,0),(-1,0),GREEN),
        ("BACKGROUND",(0,3),(-1,3),PALE),("LINEBELOW",(0,1),(-1,-1),.4,colors.HexColor("#D8E0DA")),
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story += [table, Spacer(1, 8)]
    p("*Against the same 3,000 recorded labels, in interpreted kcal/session. Original units and label construction are unverified.", "SmallCustom")
    p("The heart-rate model's relative MAE change versus full inputs is <b>-5.22%</b>; approximate paired 95% percentile interval <b>[-6.52%, -3.82%]</b> using 2,000 row resamples. Its upper bound passes the project's +10% tolerance. Removing both sensors fails. One fewer field is an input-count result, not measured cost or time savings.")
    p("Scope: previously explored benchmark; unknown collection, possible participant dependence and unresolved dataset licensing. This is not verified physiological calorie measurement.", "SmallCustom")
    story.append(PageBreak())
    p("RELIABILITY / IMPLEMENTATION / EVIDENCE", "EyebrowCustom")
    p("Make the failure cases visible", "TitleCustom")
    p("The primary fixed 90%-nominal interval covers 90.67% overall. Coverage differs substantially by session duration; an overall score does not establish reliability for every group.", "LeadCustom")
    story.append(CoverageChart(groups))
    p("For 21-30 minute sessions (997 records), coverage is only <b>79.54%</b>. Bounds remain unclipped; no subgroup recalibration followed the test. An earlier simulated Gaussian heart-rate-noise stress test (SD 5 bpm) raised development MAE from 1.080 to 7.777. That is a chosen simulation, not a measured device error distribution.")
    p("A deployed, verifiable implementation", "HeadCustom")
    p("The free Hugging Face Static Space runs four exported frozen forests in the browser. Feature order, binary one-hot encoding, float32 comparisons and summation reproduce the Python pipelines. The app sends no prediction inputs to a prediction API and saves no submissions; hosting may retain asset-request logs.")
    p("Served files and repository hashes match the reviewed package. Downloaded JavaScript and models match Python predictions and unclipped bounds exactly on <b>5,854 synthetic sessions</b>, including split boundaries. The current source passes <b>82 Python tests and four JavaScript checks</b>. The author confirmed basic demo interaction; automated browser/mobile/accessibility checks were unavailable.")
    p("This demonstrates browser model delivery and deployment verification. A Python/Waitress Docker template is retained locally, but Linux container execution and hosted Docker deployment were not verified.", "SmallCustom")
    p("Authorship and what is not measured", "HeadCustom")
    p("The author supplied the existing notebook/data, directed project choices, selected free hosting, completed account authentication and checked basic live interaction. Research code, evaluation tooling and documentation were produced with substantial AI-assistant support. Project ownership does not establish independent mastery of every implementation detail.")
    p("The usability study was skipped at the author's request: <b>no participant results or measured user benefit</b> exist. No clinical validity, adoption, health improvement, cost savings or new algorithm is claimed. Row bootstrap intervals assume exchangeability and omit training uncertainty. A documented measured-data replication would be a separate future study.")
    p("Explore the evidence", "HeadCustom")
    p('<link href="https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors" color="#164A3E">Live demo: huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors</link><br/><link href="https://github.com/Moobakr/calories-burnt-prediction" color="#164A3E">Project source: github.com/Moobakr/calories-burnt-prediction</link>', "SmallCustom")
    p("The repository and accompanying source archive contain the evaluation protocol, final and reliability reports, aggregate metrics, deployment checks and an explicit contribution record.", "SmallCustom")
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D8E0DA"))
        canvas.line(42, 36, A4[0]-42, 36)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(42, 23, "Calorie Lab | recorded-label benchmark | AI-assisted project")
        canvas.drawRightString(A4[0]-42, 23, f"{doc.page} / 2")
        canvas.restoreState()
    output.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(output), pagesize=A4, rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=49,
                      title="Calorie Lab - Sensor Requirements and Reliability",author="Moobakr",
                      subject="AI-assisted benchmark study and verified browser deployment; no measured user impact").build(story,onFirstPage=footer,onLaterPages=footer)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"output/pdf/Calorie_Lab_Project_Brief.pdf")
    args=parser.parse_args()
    print(build(args.output.resolve()))
