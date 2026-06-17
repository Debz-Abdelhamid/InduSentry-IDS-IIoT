"""Report Generator — IDS-IIoT  (professional layout)"""

import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    pdfmetrics.registerFont(TTFont('Inter', 'static/fonts/Inter-Regular.ttf'))
except Exception:
    pass

# ── Brand palette ──────────────────────────────────────────────────────────────
NAVY   = colors.HexColor('#1A2744')
BLUE   = colors.HexColor('#2563EB')
CYAN   = colors.HexColor('#0891B2')
GREEN  = colors.HexColor('#059669')
RED    = colors.HexColor('#DC2626')
ORANGE = colors.HexColor('#D97706')
BG_PAGE = colors.HexColor('#F8FAFC')
BG_ALT  = colors.HexColor('#EFF6FF')
BORDER  = colors.HexColor('#CBD5E1')
TEXT    = colors.HexColor('#1E293B')
MUTED   = colors.HexColor('#64748B')

PAGE_W, PAGE_H = A4


# ── Logo (matplotlib, white background) ────────────────────────────────────────
def _build_pdf_logo() -> str:
    from matplotlib.patches import Polygon as MpPoly, FancyBboxPatch

    fig = plt.figure(figsize=(7.8, 1.55), facecolor='white')
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 7.8)
    ax.set_ylim(0, 1.55)
    ax.axis('off')
    ax.set_facecolor('white')

    cx, cy, r = 0.78, 0.775, 0.62
    angles = np.radians(np.arange(0, 360, 60))
    hx = cx + r * np.cos(angles)
    hy = cy + r * np.sin(angles)
    hex_pts = list(zip(hx, hy))

    ax.add_patch(MpPoly(hex_pts, closed=True, facecolor='#EFF6FF',
                        edgecolor='#3B82F6', linewidth=1.4, zorder=1))
    for i, (x, y) in enumerate(hex_pts):
        ax.plot(x, y, 'o', markersize=4,
                color='#3B82F6' if i in (0, 3) else '#06B6D4', zorder=4)

    ax.plot([cx + r, cx + r + 0.1], [cy, cy],
            color='#3B82F6', linewidth=0.9, alpha=0.35, zorder=2)
    ax.plot(cx + r + 0.1, cy, 'o', markersize=3,
            color='#3B82F6', alpha=0.35, zorder=2)

    sw, sh = 0.50, 0.72
    shield_pts = [
        (cx,              cy + sh * 0.52),
        (cx + sw / 2,     cy + sh * 0.26),
        (cx + sw / 2,     cy - sh * 0.16),
        (cx + sw/2*0.75,  cy - sh * 0.44),
        (cx,              cy - sh * 0.55),
        (cx - sw/2*0.75,  cy - sh * 0.44),
        (cx - sw / 2,     cy - sh * 0.16),
        (cx - sw / 2,     cy + sh * 0.26),
    ]
    ax.add_patch(MpPoly(shield_pts, closed=True,
                        facecolor='#2563EB', edgecolor='#1D4ED8',
                        linewidth=0.5, zorder=3))

    lbx, lby, lbw, lbh = cx - 0.13, cy - 0.37, 0.26, 0.20
    ax.add_patch(FancyBboxPatch((lbx, lby), lbw, lbh,
                               boxstyle='round,pad=0.02',
                               facecolor='white', edgecolor='none', zorder=6))

    arc_r = 0.105
    theta = np.linspace(0, np.pi, 30)
    ax.plot(cx + arc_r * np.cos(theta),
            (lby + lbh) + arc_r * np.sin(theta),
            color='white', linewidth=2.0, zorder=7)

    ax.plot(cx, lby + lbh * 0.52, 'o', color='#1D4ED8', markersize=3.5, zorder=8)
    ax.plot([cx, cx], [lby + lbh * 0.52 - 0.04, lby + lbh * 0.12],
            color='#1D4ED8', linewidth=1.2, zorder=8)

    ax.plot([1.52, 1.52], [0.18, 1.36], color='#E2E8F0', linewidth=1.0, zorder=1)

    ax.text(1.65,  0.92, 'Indu',   fontsize=21, fontweight='bold', color='#1E293B',
            va='center', ha='left', zorder=5)
    ax.text(2.535, 0.92, 'Sentry', fontsize=21, fontweight='bold', color='#2563EB',
            va='center', ha='left', zorder=5)
    ax.text(1.66,  0.50, 'IDS-IIoT SECURITY PLATFORM',
            fontsize=6.8, fontweight='bold', color='#64748B',
            va='center', ha='left', zorder=5, fontfamily='monospace')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    fig.savefig(tmp.name, dpi=220, bbox_inches='tight',
                facecolor='white', transparent=False)
    plt.close(fig)
    return tmp.name


# ── Chart helpers ──────────────────────────────────────────────────────────────
def _pie_chart(labels, values, clrs) -> str:
    fig, ax = plt.subplots(figsize=(4.8, 3.8), facecolor='white')
    ax.set_facecolor('white')
    if sum(values) > 0:
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct='%1.1f%%',
            colors=clrs, startangle=90,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            pctdistance=0.80,
        )
        for t in texts:
            t.set_fontsize(9); t.set_color('#334155')
        for a in autotexts:
            a.set_fontsize(8.5); a.set_color('white'); a.set_fontweight('bold')
    ax.axis('equal')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    fig.savefig(tmp.name, bbox_inches='tight', dpi=180, facecolor='white')
    plt.close(fig)
    return tmp.name


def _bar_chart(labels, values, clrs) -> str:
    fig, ax = plt.subplots(figsize=(7.0, 3.2), facecolor='white')
    ax.set_facecolor('white')
    bars = ax.bar(labels, values, color=clrs, edgecolor='white',
                  linewidth=0.8, width=0.55)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color='#E2E8F0', linewidth=0.8)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#CBD5E1')
    ax.tick_params(axis='x', labelrotation=30, labelsize=8, colors='#475569')
    ax.tick_params(axis='y', labelsize=8,  colors='#475569')
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h,
                    f'{int(h):,}', ha='center', va='bottom',
                    fontsize=7.5, color='#1E293B', fontweight='bold')
    fig.tight_layout()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    fig.savefig(tmp.name, bbox_inches='tight', dpi=180, facecolor='white')
    plt.close(fig)
    return tmp.name


# ── Main generator ─────────────────────────────────────────────────────────────
def generate_ids_report(summary_data: dict, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path   = os.path.join(output_dir, f"ids_report_{timestamp}.pdf")
    date_str   = datetime.now().strftime("%B %d, %Y")
    date_short = datetime.now().strftime("%Y-%m-%d")

    # ── Page callbacks ─────────────────────────────────────────────────────
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(2.5)
        canvas.line(0, PAGE_H - 0.35*cm, PAGE_W, PAGE_H - 0.35*cm)
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2*cm, 1.85*cm, PAGE_W - 2*cm, 1.85*cm)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(2*cm, 1.25*cm,
            f"InduSentry  ·  IDS-IIoT Security Report  ·  {date_str}")
        canvas.drawRightString(PAGE_W - 2*cm, 1.25*cm, f"Page {doc.page}")
        canvas.restoreState()

    def _cover_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 0.6*cm, PAGE_W, 0.6*cm, fill=1, stroke=0)
        canvas.restoreState()

    # ── Document ───────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        topMargin=2.2*cm, bottomMargin=2.6*cm,
        leftMargin=2*cm,  rightMargin=2*cm,
    )

    # ── Styles ─────────────────────────────────────────────────────────────
    SS = getSampleStyleSheet()

    def _ps(name, **kw):
        return ParagraphStyle(name, parent=SS['Normal'], **kw)

    title_st    = _ps('T', fontName='Helvetica-Bold', fontSize=28,
                       textColor=NAVY, alignment=1, spaceAfter=4)
    subtitle_st = _ps('S', fontName='Helvetica', fontSize=12,
                       textColor=MUTED, alignment=1)
    section_st  = _ps('H', fontName='Helvetica-Bold', fontSize=12,
                       textColor=NAVY, spaceBefore=4, spaceAfter=6)
    label_st    = _ps('L', fontName='Helvetica-Bold', fontSize=7.5,
                       textColor=MUTED, alignment=1)
    value_st    = _ps('V', fontName='Helvetica-Bold', fontSize=20,
                       textColor=NAVY, alignment=1)

    # ── Table style factory ────────────────────────────────────────────────
    def _ts(hdr=NAVY, align='LEFT', num_cols=2):
        aligns = [('ALIGN', (0, 0), (-1, 0), 'CENTER')]
        if align == 'CENTER':
            aligns = [('ALIGN', (0, 0), (-1, -1), 'CENTER')]
        return TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  hdr),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0),  10),
            ('TOPPADDING',    (0, 0), (-1, 0),  9),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  9),
            ('LEFTPADDING',   (0, 0), (-1, -1), 11),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 11),
            ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',      (0, 1), (-1, -1), 9.5),
            ('TOPPADDING',    (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',         (0, 1), (-1, -1), align),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_ALT]),
            ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
            ('LINEBELOW',     (0, 0), (-1, -1), 0.4, BORDER),
        ] + aligns)

    # ── Section heading builder ────────────────────────────────────────────
    def _section(title):
        return [
            Paragraph(title, section_st),
            HRFlowable(width='100%', thickness=1.5, color=BLUE,
                       spaceAfter=8, spaceBefore=2),
        ]

    # ── Data ───────────────────────────────────────────────────────────────
    total    = summary_data.get('total_samples', 0)
    normal   = summary_data.get('normal_count', 0)
    anomaly  = summary_data.get('anomaly_count', max(total - normal, 0))
    known    = summary_data.get('known_count', 0)
    zero_day = summary_data.get('zero_day_count', 0)
    dist     = {k: v for k, v in (summary_data.get('attack_distribution') or {}).items()
                if k.lower() != 'normal'}

    def pct(v, b):
        return f"{(v / b * 100):.1f}%" if b > 0 else "—"

    # ══════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════
    story = [Spacer(1, 2.5*cm)]

    logo_img = Image(_build_pdf_logo(), width=11*cm, height=2.2*cm)
    logo_img.hAlign = 'CENTER'
    story.append(logo_img)
    story.append(Spacer(1, 1.6*cm))

    # Blue rule
    story.append(HRFlowable(width='100%', thickness=2, color=BLUE,
                             spaceBefore=0, spaceAfter=0.8*cm))
    story.append(Paragraph("IDS-IIoT Security Report", title_st))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Industrial IoT Intrusion Detection System", subtitle_st))
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER,
                             spaceBefore=0, spaceAfter=1.6*cm))

    # 2-column cover metadata
    cover_tbl = Table(
        [
            [Paragraph("REPORT DATE",      label_st),
             Paragraph("SAMPLES ANALYZED", label_st)],
            [Paragraph(date_short,         value_st),
             Paragraph(f"{total:,}",       value_st)],
        ],
        colWidths=[8.5*cm, 8.5*cm],
    )
    cover_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BG_ALT),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
        ('LINEAFTER',     (0, 0), (1, -1),  0.5, BORDER),
        ('LINEBELOW',     (0, 0), (-1, 0),  0.5, BORDER),
    ]))
    story.append(cover_tbl)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 2: DETECTION SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    story.extend(_section("Detection Summary"))

    # 4 KPI cards
    def _kpi(label, val, col):
        return [Paragraph(label, label_st), Paragraph(val, _ps('kv', fontName='Helvetica-Bold',
                fontSize=22, textColor=col, alignment=1))]

    kpi_tbl = Table(
        [[_kpi("TOTAL SAMPLES",   f"{total:,}",    NAVY),
          _kpi("NORMAL TRAFFIC",  f"{normal:,}",   GREEN),
          _kpi("KNOWN ATTACKS",   f"{known:,}",    BLUE),
          _kpi("ZERO-DAY THREATS",f"{zero_day:,}", ORANGE)]],
        colWidths=[4.25*cm, 4.25*cm, 4.25*cm, 4.25*cm],
    )
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BG_ALT),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER),
        ('LINEAFTER',     (0, 0), (2, -1),  0.5, BORDER),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 0.5*cm))

    # Summary stats table
    metrics_tbl = Table(
        [
            ["Classification",  "Count",           "Share of Total"],
            ["Normal Traffic",  f"{normal:,}",     pct(normal,   total)],
            ["Known Attacks",   f"{known:,}",      pct(known,    total)],
            ["Zero-Day Threats",f"{zero_day:,}",   pct(zero_day, total)],
            ["Total Anomalies", f"{anomaly:,}",    pct(anomaly,  total)],
        ],
        colWidths=[7*cm, 5*cm, 5*cm],
    )
    metrics_tbl.setStyle(_ts(hdr=NAVY, align='CENTER'))
    story.append(metrics_tbl)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 3: AUTOENCODER PHASE
    # ══════════════════════════════════════════════════════════════════════
    story.extend(_section("Phase 1 — AutoEncoder Analysis"))

    ae_tbl = Table(
        [
            ["Class",    "Count",        "Share"],
            ["Normal",   f"{normal:,}",  pct(normal,  total)],
            ["Anomaly",  f"{anomaly:,}", pct(anomaly, total)],
        ],
        colWidths=[5*cm, 5*cm, 5*cm],
    )
    ae_tbl.setStyle(_ts(hdr=BLUE, align='CENTER'))
    story.append(ae_tbl)
    story.append(Spacer(1, 0.5*cm))

    ae_chart = _pie_chart(
        ["Normal", "Anomaly"],
        [normal, anomaly],
        ['#059669', '#DC2626'],
    )
    img = Image(ae_chart, width=9*cm, height=7.2*cm)
    img.hAlign = 'CENTER'
    story.append(img)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 4: ATTACK CLASSIFICATION
    # ══════════════════════════════════════════════════════════════════════
    story.extend(_section("Phase 2 — Attack Classification"))

    # Known vs Zero-Day side-by-side: table left, chart right
    kz_tbl = Table(
        [
            ["Category",       "Count",         "Share of Anomalies"],
            ["Known Attacks",  f"{known:,}",    pct(known,    anomaly)],
            ["Zero-Day",       f"{zero_day:,}", pct(zero_day, anomaly)],
        ],
        colWidths=[6*cm, 4.5*cm, 4.5*cm],
    )
    kz_tbl.setStyle(_ts(hdr=NAVY, align='CENTER'))
    story.append(kz_tbl)
    story.append(Spacer(1, 0.5*cm))

    kz_chart = _bar_chart(
        ["Known Attacks", "Zero-Day"],
        [known, zero_day],
        ['#2563EB', '#D97706'],
    )
    img_kz = Image(kz_chart, width=12*cm, height=5*cm)
    img_kz.hAlign = 'CENTER'
    story.append(img_kz)
    story.append(Spacer(1, 0.6*cm))

    # Attack distribution breakdown
    if dist:
        story.extend(_section("Known Attack Breakdown"))
        sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        known_total = sum(dist.values())

        dist_rows = [["Attack Type", "Count", "Share of Known"]]
        dist_rows += [[name, f"{cnt:,}", pct(cnt, known_total)]
                      for name, cnt in sorted_dist]

        dist_tbl = Table(dist_rows, colWidths=[8*cm, 4*cm, 5*cm])
        dist_tbl.setStyle(_ts(hdr=BLUE, align='CENTER'))
        story.append(dist_tbl)
        story.append(Spacer(1, 0.5*cm))

        top = sorted_dist[:10]
        if top:
            atk_chart = _bar_chart(
                [n for n, _ in top],
                [v for _, v in top],
                ['#2563EB'] * len(top),
            )
            img_atk = Image(atk_chart, width=15*cm, height=5.5*cm)
            img_atk.hAlign = 'CENTER'
            story.append(img_atk)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 5: DETECTION PARAMETERS
    # ══════════════════════════════════════════════════════════════════════
    story.extend(_section("Detection Parameters"))

    params = [
        ["Parameter",                   "Value"],
        ["Detection Method",             "AutoEncoder + XGBoost + OOD"],
        ["OOD Score Weighting",          "Mahalanobis 60%  ·  AE Error 30%  ·  Entropy 10%"],
        ["AE Reconstruction Threshold",  str(round(summary_data.get('ae_threshold', 0), 6))],
        ["AE High Threshold (85th pct)", str(round(summary_data.get('ae_threshold_high', 0), 6))],
        ["OOD Threshold (80th pct)",     str(round(summary_data.get('ood_threshold', 0), 6))],
        ["Per-Sample Latency",           f"{summary_data.get('latency_ms', '—')} ms"],
    ]

    params_tbl = Table(params, colWidths=[7*cm, 10*cm])
    params_tbl.setStyle(_ts(hdr=NAVY))
    story.append(params_tbl)

    # ── Build ──────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_cover_page, onLaterPages=_footer)
    return out_path


class IDSReportGenerator:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir

    def generate_report(self, summary_data, samples_data=None, output_filename=None):
        return generate_ids_report(summary_data, self.output_dir)
