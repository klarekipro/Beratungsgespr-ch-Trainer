"""Localized report framing; original conversation and author text remain verbatim."""
import io
from xml.sax.saxutils import escape
from .exports import _fonts

LABELS={
'de': ['Gesprächsauswertung','Gespräch','Szenario','Trainingssprache','Prüfstatus','Eigener Versuch','Beim Mentor eingereicht','Vom Mentor geprüft','Vorläufige KI-Rückmeldung','Veröffentlichte Rückmeldung','Mentor','Datum','Ergebnis','Transkript','Mitarbeiter','Kunde','Unternehmensversion','Materialversion','Nicht erfasst','Klare KI - Zertifikat über den Abschluss eines Lernthemas','Teilnehmer','Thema / Kompetenz','Grundlage','Kommentar','Nummer','Status','Lernziel','Beobachtungen','Entwurf','Ausgestellt','Widerrufen','Ersetzt'],
'en': ['Consultation review','Conversation','Scenario','Training language','Review status','Independent attempt','Submitted to mentor','Reviewed by mentor','Preliminary AI feedback','Published mentor feedback','Mentor','Date','Outcome','Transcript','Employee','Customer','Company revision','Material revision','Not recorded','Klare KI Certificate of Learning Topic Completion','Participant','Topic / skill','Basis','Comment','Number','Status','Learning goal','Observations','Draft','Issued','Revoked','Replaced'],
'ru': ['Разбор консультации','Беседа','Сценарий','Язык тренировки','Статус проверки','Самостоятельная попытка','Отправлено наставнику','Проверено наставником','Предварительный ИИ-разбор','Опубликованная обратная связь','Наставник','Дата','Фактический исход','Транскрипт','Сотрудник','Клиент','Версия предприятия','Версия материалов','Не зафиксировано','Сертификат прохождения учебной темы Klare KI','Сотрудник','Тема / навык','Основания','Комментарий','Номер','Статус','Учебная цель','Наблюдения','Черновик','Выдан','Отозван','Заменён']}
OUTCOMES={
'de':['Kein vereinbarter nächster Schritt','Interesse / Angebot zur Prüfung','Diagnose vorläufig vereinbart','Termin bestätigt','Reparatur vereinbart','Leistung nicht verfügbar','Kunde lehnt ab','Auftrag bestätigt','Vorläufige Vereinbarung','Entscheidung mit weiterer Person vertagt'],
'en':['No agreed next step','Interest / offer under consideration','Tentative diagnosis','Visit confirmed','Repair agreed','Service unavailable','Customer declined','Order confirmed','Tentative agreement','Decision deferred to another participant'],
'ru':['Нет согласованного следующего шага','Интерес / предложение на рассмотрении','Предварительная диагностика','Выезд подтверждён','Ремонт согласован','Услуга недоступна','Клиент отказался','Заказ подтверждён','Предварительная договорённость','Решение отложено для обсуждения']}
OUTCOME_KEYS=['no_next_step','interested','diagnosis_tentative','visit_confirmed','repair_agreed','service_unavailable','customer_declined','order_confirmed','tentative_agreement','deferred_decision']
EXTRA={'de':['Unternehmenskarte','Katalog und Bedingungen','Geschlossene Kundenkarte','Phasenentscheidung','Erreicht','Teilweise erreicht','Noch nicht erreicht','Noch nicht beurteilt'], 'en':['Company card','Catalogue and terms','Private customer card','Stage assessment','Achieved','Partly achieved','Not yet achieved','Not assessed'], 'ru':['Карточка компании','Каталог и условия','Закрытая карточка клиента','Решение по этапам','Достигнуто','Частично достигнуто','Пока не достигнуто','Не оценено']}
STAGES={'de':['Bedarf','Möglichkeiten und Grenzen','Begründetes Angebot'],'en':['Needs','Capabilities and limits','Justified proposal'],'ru':['Потребности','Возможности и ограничения','Обоснованное предложение']}
RATINGS={'de':['Nicht geprüft','Erfüllt','Teilweise erfüllt','Nicht erfüllt'],'en':['Not reviewed','Completed','Partial','Not completed'],'ru':['Не проверено','Выполнено','Частично выполнено','Не выполнено']}
GOALS=['achieved','partly','not_achieved','not_reviewed']
def lang(value):return value if value in LABELS else 'de'
def report_text(s,language='de'):
    language=lang(language);t=LABELS[language];e=EXTRA[language];v=s.get('learning',{});ctx=v.get('learning_context',{});r=v.get('published_review');sc=s['scenario_snapshot']
    from .review_service import heading
    h=heading(s,ctx or {'source':'legacy_fallback_not_original'})
    lines=[t[0],f"{t[1]}: {s['id']}",f"{t[2]}: {h['title']}",f"{t[3]}: {dict(de='Deutsch',en='English',ru='Русский').get(sc['language'],sc['language'])}",f"{t[4]}: {t[{'not_submitted':5,'submitted':6,'reviewed':7}.get(s['review_status'],5)]}",f"{t[16]}: {s['company_snapshot']['revision']}",f"{t[17]}: {(ctx.get('materials') or {}).get('id',t[18])}",f"{t[26]}: {h['objective'] or t[18]}",f"{t[11]}: {s['created_at']}"]
    if ctx.get('source')=='legacy_fallback_not_original':lines.append({'de':'Diese Orientierungen wurden nachträglich angewendet; kein ursprünglicher Aufgabenschnappschuss.','en':'This guidance was applied after the attempt; it is not an original assignment snapshot.','ru':'Эти ориентиры применены после попытки; это не исходный снимок задания.'}[language])
    a=v.get('analysis',{})
    if a.get('status')=='ready':
        lines+=['',t[8]]
        from pathlib import Path
        import json
        labels=json.loads((Path(__file__).resolve().parents[3]/'frontend/locales'/f'{language}.json').read_text())
        if a.get('attempt_status')=='error':lines.append(labels['review22.previous_analysis'])
        for item in a['result']['sections']:
            title=labels.get('review22.'+item['title'],t[8] if item['title']=='summary' else item['title'])
            if item['title']=='next_attempt':title=labels['review23.training_priorities' if a['result'].get('recommendation') else 'review23.legacy_priorities']
            text=item['text']
            if not text and item['title'] in ('gaps','next_attempt'):text=labels['review25.no_gaps' if item['title']=='gaps' else 'review25.no_required_changes']
            lines += [title,text]
        for claim in a['result'].get('claim_checks',[]):
            lines += [labels['review23.conditions'],claim['statement'],labels['review23.verdict_'+claim['verdict']],claim['observation']]
            lines += [ref.get('quote') or labels['review23.source_missing'] for ref in claim['material_evidence']]
        advice=a['result'].get('recommendation')
        if advice:lines += [labels['review23.title'],labels['review23.'+advice['action']],advice['explanation'],*advice['priorities'],labels['review23.advisory']]
        from .review_service import message_ids
        ids=message_ids(s)
        for stage in a['result'].get('stages',[]):
            lines += [labels['review22.'+stage['key']],labels['review22.'+stage['status']],stage['observation']]
            for evidence in stage['evidence']:
                if evidence['message_id'] in ids:lines += [f"[{ids.index(evidence['message_id'])+1}] "+evidence['quote']]

    if r:
        import json
        from pathlib import Path
        labels=json.loads((Path(__file__).resolve().parents[3]/'frontend/locales'/f'{language}.json').read_text())
        assessment=r.get('assessment') or {}
        outcome=assessment.get('commercial_outcome')
        outcome_label=labels.get('review.outcome.'+str(outcome),labels['review.unset'])
        fit_label=labels.get('review.fit.'+assessment.get('company_fit','not_checked'),labels['review.fit.not_checked'])
        lines+=['',t[9],f"{t[10]}: {r['mentor_name']}",f"{t[11]}: {r['published_at']}",
                f"{labels['review.commercial']}: {outcome_label}",f"{labels['review.company_fit']}: {fit_label}",
                f"{t[26]}: {e[4+GOALS.index(r.get('goal'))] if r.get('goal') in GOALS else t[18]}",
                f"{t[27]}: {r.get('observations','')}",r['note']]
        for index,stage in enumerate(['needs','capabilities','proposal']):
            rating=(r.get('assessment') or {}).get('stages',{}).get(stage,'not_reviewed')
            labels=['not_reviewed','completed','partial','not_completed']
            lines.append(STAGES[language][index]+': '+(RATINGS[language][labels.index(rating)] if rating in labels else t[18]))
    elif s.get('review_note'):
        lines+=['',t[9],s['review_note']]
    if not r:lines += [f'{t[12]}: {t[18]}']
    lines+=['',t[13]]
    for i,m in enumerate(s['messages']):lines += [f"[{i+1}] {t[14] if m['role']=='learner' else t[15]}:",m['text'],'']
    lines+=['',e[0],s['company_snapshot']['name'],s['company_snapshot']['description']]
    for service in s['company_snapshot']['services']:lines += [service['title'],service['description'],service['conditions']]
    lines += [s['company_snapshot']['limitations']]
    m=ctx.get('materials')
    if m:
        lines += ['',e[1],m['markdown']]
        for product in m['products']:lines += [' | '.join(str(product.get(k,'')) for k in ['id','name','category','features','price_eur','price_includes','availability','promotion','valid_until'])]
    if not s.get('restricted_export'):
        lines+=['',e[2]]
        for fact in sc['facts']:lines += [fact['label'],fact['value']]
    return '\n'.join(lines)

def saved_analysis_text(session,analysis,language='de',audience='mentor'):
    """Format the explicitly selected saved audience; never generate or change sources."""
    import json
    from pathlib import Path
    language=lang(language)
    labels=json.loads((Path(__file__).resolve().parents[3]/'frontend/locales'/f'{language}.json').read_text())
    t=lambda key:labels.get(key,key)
    r=analysis['result']
    lines=[t('review22.preliminary') if audience=='learner' else t('mentor32.ai'),t('review22.notice') if audience=='learner' else t('mentor32.private_ai'),session['scenario_snapshot']['title'],analysis.get('completed_at','')]
    if analysis.get('attempt_status')=='error':lines.append(t('review22.previous_analysis'))
    sections=r.get('sections') or [{'title':k,'text':'\n'.join(r[k]) if isinstance(r[k],list) else r[k]} for k in ('summary','actual_outcome','strengths','gaps','next_attempt') if k in r]
    for section in sections:
        lines += ['',t('mentor32.summary') if section['title']=='summary' else labels.get('review22.'+section['title'],section['title']),section['text'] or (t('review25.no_gaps') if section['title']=='gaps' else t('review25.no_required_changes') if section['title']=='next_attempt' else '')]
        for index in section.get('messages',[]):
            if isinstance(index,int) and 0<=index<len(session['messages']):lines.append(f"[{index+1}] "+session['messages'][index]['text'])
    def evidence(items):return [item.get('quote','') for item in items]
    for stage in r.get('stages',[]):
        lines += ['',t('review22.'+stage['key']),t('review22.'+stage['status']),stage['observation'],*evidence(stage.get('evidence',[]))]
    for claim in r.get('claim_checks',[]):
        lines += ['',t('review23.conditions'),claim['statement'],t('review23.verdict_'+claim['verdict']),claim['observation'],*evidence(claim.get('evidence',[]))]
        lines += [item.get('quote') or t('review23.source_missing') for item in claim.get('material_evidence',[])]
    advice=r.get('recommendation')
    if advice:lines += ['',t('review23.title'),t('review23.'+advice['action']),advice['explanation'],*advice.get('priorities',[]),*evidence(advice.get('evidence',[])),t('review23.advisory')]
    return '\n'.join(str(line) for line in lines)

def mentor_analysis_text(session,analysis,language='de'):
    return saved_analysis_text(session,analysis,language,'mentor')

def published_feedback_text(session,record,language='de'):
    """Only a published human decision. No draft or private analysis is consulted."""
    import json
    from pathlib import Path
    labels=json.loads((Path(__file__).resolve().parents[3]/'frontend/locales'/f'{lang(language)}.json').read_text())
    t=lambda key:labels.get(key,key)
    a=record.get('assessment') or {}
    lines=[t('review22.mentor_feedback'),session['scenario_snapshot']['title'],record.get('mentor_name',''),record.get('published_at',''),'',t('review22.mentor_stages'),t('mentor32.goal_outcome')+': '+t('learning.'+record.get('goal','not_reviewed'))]
    for key in ('needs','capabilities','proposal'):
        lines.append(t('review22.'+key)+': '+t('review.rating.'+a.get('stages',{}).get(key,'not_reviewed')))
    lines += [t('review.commercial')+': '+t('review.outcome.'+a['commercial_outcome'] if a.get('commercial_outcome') else 'review.unset'),t('review.company_fit')+': '+t('review.fit.'+a.get('company_fit','not_checked'))]
    lines += ['',t('review22.mentor_feedback'),record.get('note','')]
    if record.get('observations'):lines += ['',t('learning.observations'),record['observations']]
    return '\n'.join(str(line) for line in lines)

def pdf_lines(title, lines, headings=()):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    _fonts();buf=io.BytesIO();doc=SimpleDocTemplate(buf,title=title,author='Klare KI',leftMargin=48,rightMargin=48,topMargin=50,bottomMargin=48)
    body=ParagraphStyle('body',fontName='KlareRegular',fontSize=10,leading=15,textColor=colors.HexColor('#173B35'),spaceAfter=4)
    heading=ParagraphStyle('heading',parent=body,fontName='KlareBold',fontSize=23,leading=29,spaceAfter=24)
    section=ParagraphStyle('section',parent=body,fontName='KlareBold',spaceBefore=8,spaceAfter=6,keepWithNext=True)
    story=[Paragraph('KLARE KI',body),Spacer(1,18),Paragraph(escape(title),heading)]
    for line in lines:story.append(Paragraph(escape(str(line)).replace('\n','<br/>') or ' ',section if line in headings else body))
    def footer(c,d):
        c.setFont('KlareRegular',8);c.drawString(48,28,'Klare KI');c.drawRightString(547,28,str(d.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer);return buf.getvalue()
def review_document_pdf(text,language='de'):
    import json
    from pathlib import Path
    labels=json.loads((Path(__file__).resolve().parents[3]/'frontend/locales'/f'{lang(language)}.json').read_text())
    keys=['mentor32.summary','review22.actual_outcome','review22.strengths','review22.gaps','review22.next_attempt','review22.needs','review22.capabilities','review22.proposal','review22.evidence_found','review22.no_clear_evidence','review22.insufficient_evidence','review22.mentor_stages','review22.mentor_feedback','review23.conditions','review23.title','learning.observations']
    lines=text.splitlines()
    return pdf_lines(lines[0],lines[1:],[labels[key] for key in keys])

def report_pdf(s,language='de'):
    language=lang(language);lines=report_text(s,language).splitlines()
    headings=[LABELS[language][i] for i in [8,9,13]]+EXTRA[language][:3]+[f['label'] for f in s['scenario_snapshot']['facts']]+[x['title'] for x in s['company_snapshot']['services']]
    return pdf_lines(lines[0],lines[1:],headings)
def certificate_pdf(r,language='de'):
    if r.get('design_version'):
        import base64
        from .certificate_design import render_certificate
        snapshot=r.get('pdf_snapshots',{}).get(r['status'])
        return base64.b64decode(snapshot) if snapshot else render_certificate(r)
    t=LABELS[lang(language)];status=t[{'draft':28,'issued':29,'revoked':30,'replaced':31}[r['status']]]
    return pdf_lines(t[19],[f"{t[25]}: {status}",f"{t[20]}: {r['print_name']}",f"{t[21]}: {r['topic']}",f"{t[24]}: {r.get('number',t[28])}",f"{t[11]}: {r.get('issued_at',r['created_at'])[:10]}",f"{t[10]}: {r['mentor_name']}",f"{t[23]}: {r['comment']}",f"{t[22]}:",*r['basis']])
