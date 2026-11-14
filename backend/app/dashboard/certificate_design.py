"""A39 certificate artwork. Saved inputs only; no inference or provider access."""
import io
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
from .exports import _fonts

VERSION = 'a39-v2'
TEXT = {
 'de': {'title':'ZERTIFIKAT','subtitle':'für praxisorientierte Beratungskompetenz','badge':'KOMPETENZNACHWEIS','studio':'BERATUNGSSTUDIO','body':'hat im Rahmen eines begleiteten Beratungstrainings Kompetenzen in der strukturierten Kundenberatung nachgewiesen.','stages':'Bedarf klären · Möglichkeiten transparent erläutern · nächste Schritte begründen','decision':'Die Ausstellung beruht auf einer eigenständigen Gesamtbeurteilung durch den Mentor.','topic':'KOMPETENZBEREICH','date':'AUSSTELLUNGSDATUM','mentor':'MENTOR','signature':'Unterschrift','issuer':'KLARE KI · INTERNER KOMPETENZNACHWEIS','limit':'Keine staatlich anerkannte Qualifikation.','draft':'MUSTER','draft_footer':'ENTWURF · NICHT AUSGESTELLT','number':'Zertifikat-Nr.','revoked':'WIDERRUFEN','replaced':'ERSETZT'},
 'en': {'title':'CERTIFICATE','subtitle':'of practical consultation competence','badge':'COMPETENCE RECORD','studio':'CONSULTATION STUDIO','body':'has demonstrated competencies in structured customer consultations within a mentored consultation training programme.','stages':'Clarify needs · explain possibilities transparently · justify next steps','decision':'Issued on the basis of an independent overall assessment by the mentor.','topic':'COMPETENCE AREA','date':'ISSUE DATE','mentor':'MENTOR','signature':'Signature','issuer':'KLARE KI · INTERNAL COMPETENCE RECORD','limit':'Not a state-recognised qualification.','draft':'SAMPLE','draft_footer':'DRAFT · NOT ISSUED','number':'Certificate no.','revoked':'REVOKED','replaced':'REPLACED'},
 'ru': {'title':'СЕРТИФИКАТ','subtitle':'практической компетентности в консультировании','badge':'ПОДТВЕРЖДЕНИЕ КОМПЕТЕНЦИИ','studio':'СТУДИЯ КОНСУЛЬТАЦИЙ','body':'продемонстрировал(а) компетенции в структурированном консультировании клиентов в рамках обучения под руководством наставника.','stages':'Выяснять потребности · ясно объяснять возможности · обосновывать следующие шаги','decision':'Выдаётся на основании самостоятельной общей оценки наставником.','topic':'ОБЛАСТЬ КОМПЕТЕНЦИИ','date':'ДАТА ВЫДАЧИ','mentor':'НАСТАВНИК','signature':'Подпись','issuer':'KLARE KI · ВНУТРЕННЕЕ ПОДТВЕРЖДЕНИЕ КОМПЕТЕНЦИИ','limit':'Не является государственной квалификацией.','draft':'ОБРАЗЕЦ','draft_footer':'ПРОЕКТ · НЕ ВЫДАН','number':'Номер сертификата','revoked':'ОТОЗВАН','replaced':'ЗАМЕНЁН'}
}
class CertificateLayoutError(ValueError):
    pass

def render_certificate(record):
    _fonts();language=record.get('language','de');t=TEXT[language]
    buf=io.BytesIO();width,height=landscape(A4)
    c=Canvas(buf,pagesize=(width,height),pageCompression=1,invariant=1)
    c.setTitle('Klare KI - '+t['title']);c.setAuthor('Klare KI')
    ink=colors.HexColor('#163E35');green=colors.HexColor('#24624F');gold=colors.HexColor('#AD9063');muted=colors.HexColor('#53645C')
    c.setFillColor(colors.HexColor('#FCFBF6'));c.rect(0,0,width,height,fill=1,stroke=0)
    c.setStrokeColor(ink);c.setLineWidth(1.5);c.roundRect(30,30,width-60,height-60,8,fill=0)
    c.setStrokeColor(gold);c.setLineWidth(.6);c.roundRect(35,35,width-70,height-70,4,fill=0)
    for x,dx in [(44,20),(width-44,-20)]:
        for y,dy in [(44,20),(height-44,-20)]:c.lines([(x,y,x+dx,y),(x,y,x,y+dy)])
    def box(text,x,top,w,h,size=12,minimum=9,bold=False,align=0,color=ink):
        text=escape(str(text)).replace('\n','<br/>')
        while size>=minimum:
            style=ParagraphStyle('certificate',fontName='KlareBold' if bold else 'KlareRegular',fontSize=size,leading=size*1.23,textColor=color,alignment=align,splitLongWords=True)
            p=Paragraph(text,style);_,ph=p.wrap(w,h)
            if ph<=h+.1:p.drawOn(c,x,top-ph);return
            size-=.5
        raise CertificateLayoutError('Shorten the certificate text to fit one printable page')
    c.setFillColor(ink);c.roundRect(63,481,47,47,8,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('KlareBold',26);c.drawString(73,496,'K·')
    box('klare ki',122,529,230,30,24,24,True)
    box(t['studio'],123,500,260,18,8,8,color=green)
    c.setFillColor(green);c.roundRect(width-278,498,215,26,13,fill=1,stroke=0)
    box(t['badge'],width-271,517,201,16,8,7.5,True,1,colors.white)
    c.setStrokeColor(colors.HexColor('#C8DFD2'));c.line(63,462,width-63,462)
    box(t['title'],70,428,width-140,43,35,30,True,1)
    box(t['subtitle'],70,382,width-140,24,13,11,False,1,muted)
    box(record.get('recipient_full_name',record['print_name']),70,342,width-140,66,32,18,True,1)
    c.setStrokeColor(gold);c.setLineWidth(1);c.line(width/2-110,270,width/2+110,270)
    box(t['body'],width/2-275,259,550,36,12,11,False,1)
    box(t['stages'],75,211,width-150,30,10.5,9.5,False,1,green)
    if record.get('comment'):
        box(record['comment'],95,178,width-190,42,11,9.5,False,1)
    box(t['decision'],75,127,width-150,17,8,7.5,False,1,muted)
    c.setStrokeColor(colors.HexColor('#C8DFD2'));c.line(66,116,width-66,116)
    box(t['topic'],71,103,280,12,8,8,True,color=green)
    box(record['topic'],71,94,315,45,12,9,True)
    box(t['date'],407,103,130,12,8,8,True,color=green)
    issued=record.get('issued_at') or record['created_at']
    date=datetime.fromisoformat(issued.replace('Z','+00:00')).strftime('%d.%m.%Y')
    box(date,407,88,130,22,12,10,True)
    issuer_label={'de':'MENTOR / AUSSTELLER','en':'MENTOR / ISSUER','ru':'НАСТАВНИК / ВЫДАЮЩИЙ'}[language] if 'issuer_full_name' in record else t['mentor']
    box(issuer_label,550,103,221,12,8,8,True,color=green)
    box(record.get('issuer_full_name',record['mentor_name']),550,94,221,30,12,8,True)
    # A labelled empty line is a place for a real signature, never a simulated signature.
    c.setStrokeColor(gold);c.line(550,61,771,61)
    box(t['signature'],550,59,221,8,6.5,6.5,color=muted)
    box(t['issuer']+' · '+t['limit'],71,45,490,9,6.2,6.2,color=muted)
    status=record['status']
    if status=='draft':
        c.saveState();c.translate(width/2,height/2);c.rotate(24);c.setFillColor(colors.HexColor('#9CB19F'));c.setFillAlpha(.7);c.setFont('KlareBold',66);c.drawCentredString(0,0,t['draft']);c.restoreState()
        box(t['draft_footer'],565,45,207,9,6.5,6.5,True,2,green)
    else:
        box((t[status]+' · ' if status in ('revoked','replaced') else '')+t['number']+': '+record['number'],565,45,207,9,6.5,6.5,False,2,muted)
        if status in ('revoked','replaced'):
            c.saveState();c.translate(width/2,height/2);c.rotate(24);c.setFillColor(colors.HexColor('#A54532'));c.setFillAlpha(.75);c.setFont('KlareBold',56);c.drawCentredString(0,0,t[status]);c.restoreState()
    c.showPage();c.save();return buf.getvalue()
