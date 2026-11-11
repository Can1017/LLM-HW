"""Build report and appendix from Markdown with Word styles and real figures."""
import json
import re
from pathlib import Path
from urllib.parse import unquote
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE

ROOT = Path(__file__).resolve().parents[2]
TITLE = '大语言模型后训练演进与强化学习代码研究'
OUT = ROOT/'reports'
FONT = 'Microsoft YaHei'

def font(run, size=11, bold=False, face=FONT, color='000000'):
    run.font.name=face
    run.font.size=Pt(size)
    run.font.bold=bold
    run.font.color.rgb=RGBColor.from_string(color)
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),face)

def setup():
    doc=Document()
    sec=doc.sections[0]
    sec.page_width=Inches(8.5); sec.page_height=Inches(11)
    sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.62)
    sec.left_margin=Inches(.70); sec.right_margin=Inches(.70)
    for name, size in [('Normal',11),('Title',18),('Heading 1',13),('Heading 2',11.5),('Heading 3',11)]:
        s=doc.styles[name]; s.font.name=FONT; s.font.size=Pt(size)
        s.font.color.rgb=RGBColor(0,0,0)
        s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),FONT)
        s.paragraph_format.space_after=Pt(5 if name=='Normal' else 6)
        s.paragraph_format.line_spacing=1.12
        if name!='Normal': s.paragraph_format.keep_with_next=True
    footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=footer.add_run(); fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE')
    r._r.addnext(fld); font(r,9,color='666666')
    return doc

def inline(p, text, size=11):
    # Preserve clickable citations, bold phrases and code spans in the Word file.
    pattern=r'(\[[^\]]+\]\([^)]+\)|\*\*.*?\*\*|'+chr(96)+r'[^'+chr(96)+r']+'+chr(96)+r')'
    for item in re.split(pattern,text):
        if not item: continue
        link=re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)',item)
        if link:
            h=OxmlElement('w:hyperlink')
            h.set(qn('r:id'),p.part.relate_to(link[2],RELATIONSHIP_TYPE.HYPERLINK,is_external=True))
            r=OxmlElement('w:r'); rp=OxmlElement('w:rPr')
            co=OxmlElement('w:color'); co.set(qn('w:val'),'245B9E'); rp.append(co)
            sz=OxmlElement('w:sz'); sz.set(qn('w:val'),str(int(size*2))); rp.append(sz)
            r.append(rp); t=OxmlElement('w:t'); t.text=link[1]; r.append(t); h.append(r); p._p.append(h)
        else:
            bold=item.startswith('**')
            code=item.startswith(chr(96))
            clean=item[2:-2] if bold else item[1:-1] if code else item
            font(p.add_run(clean),size,bold,face='Consolas' if code else FONT)

def addtable(doc,rows):
    n=len(rows[0]); t=doc.add_table(rows=0,cols=n); t.autofit=False
    ratios={2:[.68,.32],3:[.27,.37,.36],4:[.13,.27,.31,.29]}.get(n,[1/n]*n)
    for col,ratio in zip(t.columns,ratios): col.width=Inches(7.1*ratio)
    for i,row in enumerate(rows):
        cells=t.add_row().cells
        for j,(c,txt) in enumerate(zip(cells,row)):
            c.width=Inches(7.1*ratios[j]); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr()
            shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'E8EEF4' if i==0 else ('F7F9FB' if i%2==0 else 'FFFFFF')); pr.append(shade)
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'D9D9D9'); borders.append(e)
            pr.append(borders)
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge); e.set(qn('w:w'),'75'); e.set(qn('w:type'),'dxa'); margins.append(e)
            pr.append(margins)
            p=c.paragraphs[0]; p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.05
            inline(p,txt,size=9)
            if i==0:
                for r in p.runs: r.bold=True
        tr=t.rows[-1]._tr.get_or_add_trPr(); tr.append(OxmlElement('w:cantSplit'))
        if i==0: tr.append(OxmlElement('w:tblHeader'))
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(2); p.paragraph_format.space_before=Pt(0)
    return t

def convert(md, output, appendix=False):
    lines=md.read_text(encoding='utf-8').splitlines()
    doc=setup(); i=0; eq=0; in_refs=False; pending_page=False
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line=='<!-- PAGE -->': pending_page=True; i+=1; continue
        if line.startswith('<!--'): i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(set(x)<=set('-: ') for x in row): rows.append(row)
                i+=1
            addtable(doc,rows); continue
        if line.startswith('!['):
            target=re.search(r'\]\(([^)]+)\)',line)[1]
            if target.startswith('https://raw.githubusercontent.com/'):
                target=unquote(target.split('/reports/',1)[1])
            path=md.parent/target
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            pic=p.add_run().add_picture(str(path),width=Inches(7.05))
            pic._inline.docPr.set('descr',re.search(r'!\[([^]]*)',line)[1])
            p.paragraph_format.space_after=Pt(2)
            i+=1; continue
        if line in (r'\[','$$'):
            eq+=1
            closing='$$' if line=='$$' else r'\]'
            i+=1
            while i<len(lines) and lines[i].strip()!=closing: i+=1
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(OUT/'figures'/f'equation-{eq}.png'),width=Inches(6.6))
            i+=1; continue
        if line.startswith(chr(96)*3):
            code=[]; i+=1
            while i<len(lines) and not lines[i].strip().startswith(chr(96)*3):
                code.append(lines[i]); i+=1
            for row in code:
                p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1
                font(p.add_run(row),8,face='Consolas')
            i+=1; continue
        if line.startswith('#'):
            level=len(line)-len(line.lstrip('#')); text=line[level:].strip()
            p=doc.add_paragraph(style='Title' if level==1 else 'Heading '+str(min(level-1,3)))
            pending_page=False
            if level==1: p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if level==1:
                ppr=p._p.get_or_add_pPr()
                for border in list(ppr.findall(qn('w:pBdr'))):
                    ppr.remove(border)
            inline(p,text,size=18 if level==1 else 13 if level==2 else 11.5)
            if text=='参考文献': in_refs=True
            i+=1; continue
        p=doc.add_paragraph()
        if line.startswith('图') or line.startswith('表'):
            p.paragraph_format.space_after=Pt(5); inline(p,line,size=9)
        else:
            inline(p,line,size=9 if in_refs else 11)
        i+=1
    doc.core_properties.title=TITLE+(' 附件' if appendix else '')
    doc.core_properties.subject='Post-training code study'
    doc.core_properties.author=''
    for root in [doc.styles.element, doc.element]:
        for border in root.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    doc.save(output)
    print(str(output))

if __name__=='__main__':
    convert(OUT/(TITLE+'.md'),OUT/(TITLE+'.docx'))
    annex=OUT/(TITLE+'-附件.md')
    if annex.exists(): convert(annex,OUT/(TITLE+'-附件.docx'),True)
