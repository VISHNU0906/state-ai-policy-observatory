"""Render the three submission documents from their reviewed Markdown sources."""
from pathlib import Path
import html, re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ROOT=Path(__file__).resolve().parent
FONTDIR=Path('C:/Windows/Fonts')
if (FONTDIR/'segoeui.ttf').exists():
    pdfmetrics.registerFont(TTFont('Body',str(FONTDIR/'segoeui.ttf')))
    pdfmetrics.registerFont(TTFont('BodyBold',str(FONTDIR/'segoeuib.ttf')))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
    FONT='Body'
else:FONT='Helvetica'
INK=colors.HexColor('#292722');ACCENT=colors.HexColor('#8a3c29');MUTED=colors.HexColor('#625d54');LINE=colors.HexColor('#d9d4cb')
styles=getSampleStyleSheet()
for n in ['BodyText','Normal']:styles[n].fontName=FONT;styles[n].fontSize=9;styles[n].leading=12.4;styles[n].textColor=INK
styles.add(ParagraphStyle(name='TitleCustom',fontName=FONT,fontSize=22,leading=27,textColor=INK,spaceAfter=18))
styles.add(ParagraphStyle(name='SectionCustom',fontName=FONT,fontSize=13,leading=17,textColor=ACCENT,spaceBefore=15,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='SubCustom',fontName=FONT,fontSize=10.5,leading=14,textColor=INK,spaceBefore=10,spaceAfter=5,keepWithNext=True))
styles.add(ParagraphStyle(name='CellCustom',fontName=FONT,fontSize=7.8,leading=11,textColor=INK))
styles.add(ParagraphStyle(name='CodeCustom',fontName='Courier',fontSize=7,leading=10,textColor=INK,backColor=colors.HexColor('#f4f1eb'),spaceAfter=5))

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',r'<link href="\2" color="#8a3c29"><u>\1</u></link>',s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'<font name="Courier" size="8">\1</font>',s)
    return s

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(LINE);canvas.line(40,37,A4[0]-40,37)
    canvas.setFont(FONT,7);canvas.setFillColor(MUTED);canvas.drawString(40,25,'STATE AI POLICY OBSERVATORY  |  Research cutoff: 10 Nov 2026');canvas.drawRightString(A4[0]-40,25,str(doc.page));canvas.restoreState()

def render(source,dest,rationale=False):
    lines=source.read_text(encoding='utf-8').splitlines();story=[];i=0;code=False
    body=ParagraphStyle('RationaleBody',parent=styles['BodyText'],fontSize=9.7,leading=13.7) if rationale else styles['BodyText']
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('```'):code=not code;continue
        if code:story.append(Paragraph(html.escape(line).replace(' ','&nbsp;'),styles['CodeCustom']));continue
        if line.startswith('|'):
            rows=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i].strip());i+=1
            rows=[r for r in rows if not re.fullmatch(r'[| :\-]+',r)]
            cells=[[Paragraph(inline(c.strip()),styles['CellCustom']) for c in r.strip('|').split('|')] for r in rows]
            n=len(cells[0]);width=A4[0]-80
            weights={2:[.25,.75],3:[.22,.36,.42],4:[.16,.28,.28,.28]}.get(n,[1/n]*n)
            table=Table(cells,colWidths=[width*w for w in weights],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ece6dc')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,LINE),('LINEBELOW',(0,1),(-1,-1),.3,LINE),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.extend([table,Spacer(1,8)]);continue
        if line.startswith('# '):story.append(Paragraph(inline(line[2:]),styles['TitleCustom']));continue
        if line.startswith('## '):story.append(Paragraph(inline(line[3:]),styles['SectionCustom']));continue
        if line.startswith('### '):story.append(Paragraph(inline(line[4:]),styles['SubCustom']));continue
        if line.startswith('- '):line='• '+line[2:]
        story.extend([Paragraph(inline(line),body),Spacer(1,6)])
    dest.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(dest),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=37,bottomMargin=49,title=source.stem.replace('_',' '),author='Project Maintainer')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

if __name__=='__main__':
    for src,name,short in [('RATIONALE.md','Rationale.pdf',True),('RESEARCH_FINDINGS.md','Research_Report.pdf',False),('AGGREGATION_RESEARCH.md','Collection_Architecture.pdf',False)]:
        render(ROOT/'docs'/src,ROOT/'output'/name,short)
    from pypdf import PdfReader
    for p in (ROOT/'output').glob('*.pdf'):print(p.name,len(PdfReader(p).pages),'pages')
