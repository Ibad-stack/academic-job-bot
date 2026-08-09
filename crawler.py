#!/usr/bin/env python3
"""Academic Job Bot v4.0
Focus: CURRENT Canadian Accounting/Finance/Business teaching jobs.
"""
import csv, io, re, time, hashlib
from datetime import datetime, date
from urllib.parse import urljoin, urlparse, urldefrag
import requests
from bs4 import BeautifulSoup
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

VERSION='4.1'
HEADERS={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/139 Safari/537.36','Accept-Language':'en-CA,en;q=0.9'}
TIMEOUT=25
S=requests.Session(); S.headers.update(HEADERS)

# v3.8: internal QA/diagnostics. The crawler records what happened to every
# candidate instead of silently dropping it.
STATS={
    'institutions':0,'reached':0,'failed':0,'pages_discovered':0,
    'pages_inspected':0,'candidates':0,'active':0,'expired':0,
    'rejected':0,'historical':0,'http_retries':0,'jobs':0,
}
REJECTIONS={}
LAST_REJECT=''

def reject(reason):
    global LAST_REJECT
    LAST_REJECT=reason
    REJECTIONS[reason]=REJECTIONS.get(reason,0)+1
    STATS['rejected']+=1
    return None

def note_candidate():
    STATS['candidates']+=1


INSTITUTIONS=[
('Thompson Rivers University','https://www.tru.ca/careers/faculty.html','generic'),
('Royal Roads University','https://www.royalroads.ca/about/careers','generic'),
('Athabasca University','https://www.athabascau.ca/careers/index.html','generic'),
('University Canada West','https://www.ucanwest.ca/careers','generic'),
('Yorkville University','https://www.yorkvilleu.ca/job-postings/','generic'),
('University of Ottawa - Telfer School of Management','https://telfer.uottawa.ca/en/faculty-staff/academic-careers','telfer'),
('York University','https://www.yorku.ca/about/careers/','generic'),
('Toronto Metropolitan University','https://hr.cf.torontomu.ca/ams/faculty/','generic'),
("Queen's University - Smith School of Business",'https://smith.queensu.ca/about/careers/','generic'),
('University of Waterloo','https://uwaterloo.ca/careers/current-opportunities/faculty-opportunities','generic'),
('Laurentian University','https://laurentian.ca/about/careers/faculty-vacancies','laurentian'),
('University of British Columbia','https://hr.ubc.ca/careers/faculty-careers','generic'),
('University of Victoria - Gustavson School of Business','https://www.uvic.ca/gustavson/info-for/industry-and-community/career-opportunities/index.php','generic'),
('University of New Brunswick','https://www.unb.ca/hr/careers/academic.php/_assets/documents/index.html','unb'),
('Carleton University','https://carleton.ca/deputyprovost/jobs/academics/','carleton'),
]
EXTRA=[
('Carleton University','Current Academic Job Postings','https://carleton.ca/deputyprovost/jobs/academics/','generic'),
('Carleton University','Sprott School of Business - Employment Opportunities','https://sprott.carleton.ca/employment-opportunities/','sprott'),
('Carleton University','Contract Instructors','https://carleton.ca/deputyprovost/jobs/contract-instructors/','generic'),
('Carleton University','Sprott Online MBA Teaching Stream','https://carleton.ca/deputyprovost/2026/assistant-professor-teaching-stream-sprott-school-of-business-business-online-mba/','carleton'),
('University of Waterloo','School of Accounting and Finance - Employment Opportunities','https://uwaterloo.ca/school-of-accounting-and-finance/about/employment-opportunities','waterloo_saf'),
]

POS={'accounting':12,'accountancy':12,'financial accounting':16,'managerial accounting':16,'management accounting':16,'auditing':14,'audit':8,'taxation':16,'tax':8,'finance':12,'financial management':13,'investments':9,'corporate finance':14,'business':5,'business administration':8,'management':6,'strategy':5,'marketing':4,'economics':3,'entrepreneurship':4,'financial reporting':14,'ifrs':14,'cpa':13,'assurance':11}
CONTRACT=['sessional','sessional member','contract instructor','contract academic','course instructor','course lecturer','adjunct','part-time teaching','part time teaching','teaching contract']
JOB=['professor','assistant professor','associate professor','full professor','lecturer','instructor','sessional','contract instructor','contract academic','teaching stream','adjunct','course instructor','course lecturer','term professor','faculty position','faculty of business','school of business']
FALSE=['postdoctoral','postdoctoral fellow','postdoc','research assistant','research associate','frequently asked questions','faq','benefits','academic calendar','advising','research funding','research services','testimonial','contact us','student access']
UNRELATED=['nursing','social work','psychology','clinical psychology','chemistry','physics','engineering','mechanical','aerospace','earth sciences','kinesiology','speech-language','speech language','french','history','law','medicine','medical','journalism','politics','computer science','mathematics','education','curriculum','mineral exploration','resource management','healthcare simulation','particle physics']
GENERIC=['career opportunities','career opportunity','employment opportunities','academic careers','faculty careers','faculty vacancies','faculty positions','current academic job postings','hiring examples','benefits','academic calendar','academic supports','advising','research services','research funding','contact us','testimonials']
COURSE_RE=r'\b(?:ACCT|ACTG|FINA|BUSI|MGT|MGMT|MBA|ECON|ADMN)\s*[- ]?\d{3,4}[A-Z]?\b'
MONTH=r'january|february|march|april|may|june|july|august|september|october|november|december'
DATE_RE=re.compile(rf'\b(?:{MONTH})\s+\d{{1,2}}(?:\s*(?:st|nd|rd|th|\^\{{(?:st|nd|rd|th)\}}))?,?\s+\d{{4}}\b|\b\d{{1,2}}(?:\s*(?:st|nd|rd|th|\^\{{(?:st|nd|rd|th)\}}))?\s+(?:{MONTH})\s+\d{{4}}\b',re.I)
SALARY_RE=re.compile(r'(?:(?:half|full|quarter)\s+credit\s+course[^$]{0,80}\$[\d,]+|\$[\d,]+[^.]{0,100}(?:half|full|quarter)\s+credit)',re.I)
TERM_RE=re.compile(r'\b(?:fall|winter|summer|spring)\s+20\d{2}(?:\s*[/&-]\s*(?:fall|winter|summer|spring)\s+20\d{2})?\b',re.I)

def clean(x): return re.sub(r'\s+',' ',x or '').strip()
def norm(u): return urldefrag((u or '').strip())[0]
def get(u,retries=3):
    # v3.8: transient university/Cloudflare failures get retries instead of
    # becoming a false 'no jobs found' result.
    last=None
    for attempt in range(1,retries+1):
        try:
            r=S.get(u,timeout=TIMEOUT,allow_redirects=True)
            if r.status_code < 500 or attempt==retries:
                if attempt>1: STATS['http_retries'] += attempt-1
                return r
        except requests.RequestException as e:
            last=e
        if attempt<retries:
            time.sleep(1.0*attempt)
    if retries>1: STATS['http_retries'] += retries-1
    return None
def links(base,html):
    soup=BeautifulSoup(html,'html.parser'); out=[]; seen=set()
    for a in soup.find_all('a',href=True):
        u=norm(urljoin(base,a['href']))
        if u and u not in seen: seen.add(u); out.append((u,clean(a.get_text(' ',strip=True))))
    return out
def text_html(h):
    soup=BeautifulSoup(h,'html.parser')
    for x in soup(['script','style','noscript','svg']):x.decompose()
    return clean(soup.get_text(' ',strip=True))
def title_html(h):
    s=BeautifulSoup(h,'html.parser'); return clean(s.title.get_text(' ',strip=True) if s.title else '')
def pdftext(data):
    if not PdfReader:return ''
    try:
        r=PdfReader(io.BytesIO(data)); return clean(' '.join((p.extract_text() or '') for p in r.pages))
    except Exception:return ''
def best_html_title(h):
    """Prefer the actual posting heading over a site chrome/title suffix.

    Many university CMS pages have titles such as:
      "Assistant or Associate Professor ... | Office of the Deputy Provost"
    The H1 is the actual job title and must win over the hosting office.
    """
    try:
        soup=BeautifulSoup(h,'html.parser')
        candidates=[]
        for tag in soup.find_all(['h1','h2','h3']):
            c=clean(tag.get_text(' ',strip=True))
            if not c or len(c)>260:
                continue
            candidates.append(c)
        patterns=[
            r'\b(?:assistant|associate|full|term)\s+professor\b',
            r'\bprofessor\b.*\b(accounting|finance|business|management|marketing|tax|audit)\b',
            r'\b(?:sessional|contract)\b.*\b(?:lecturer|instructor|teaching)\b',
            r'\b(?:course|contract)\s+instructor\b',
            r'\blecturer\b',
        ]
        for c in candidates:
            if any(re.search(p,c,re.I) for p in patterns):
                return c
        return candidates[0] if candidates else title_html(h)
    except Exception:
        return title_html(h)

def content(u):
    r=get(u)
    if not r:return norm(u),'','',''
    final=norm(r.url); ct=(r.headers.get('Content-Type') or '').lower()
    if 'pdf' in ct or r.content[:4]==b'%PDF' or final.lower().endswith('.pdf'):
        t=pdftext(r.content)
        if t:return final,'',t,'pdf'
    try:return final,best_html_title(r.text),text_html(r.text),'html'
    except Exception:return final,'','',''

def codes(t):
    a=[]
    for x in re.findall(COURSE_RE,t,re.I):
        x=re.sub(r'\s+','',x.upper())
        if x not in a:a.append(x)
    return a[:12]
def fit(t):
    l=t.lower(); return [k for k,_ in sorted(POS.items(),key=lambda z:-len(z[0])) if k in l][:10]
def field(t):
    l=t.lower(); a=sum(k in l for k in ['accounting','accountancy','financial accounting','managerial accounting','auditing','taxation','financial reporting','ifrs','assurance','acct']); f=sum(k in l for k in ['finance','corporate finance','investments','financial management','fixed income']); b=sum(k in l for k in ['business administration','business','management','strategy','marketing','entrepreneurship','mba']);
    if max(a,f,b)==0:return ''
    return 'Accounting' if a>=f and a>=b else ('Finance' if f>=b else 'Business')
def deadline(t):
    l=t.lower()
    for phrase in ['application deadline','applications close','closing date','closing date:','deadline','apply by','applications due','competition closing']:
        p=l.find(phrase)
        if p>=0:
            window=t[max(0,p-80):p+300]
            m=DATE_RE.search(window)
            if m:return clean(m.group(0))
            # Handles HTML/PDF extraction such as "July 10th, 2026" reliably.
            m=re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,)?\s*20\d{2}\b',window,re.I)
            if m:return clean(m.group(0))
            m=re.search(r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}\b',window,re.I)
            if m:return clean(m.group(0))
    return ''
def parse_date_string(d):
    if not d:
        return None
    raw=d.replace(',', ' ')
    raw=re.sub(r'\^\{(?:st|nd|rd|th)\}', '', raw, flags=re.I)
    raw=re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', lambda m: re.sub(r'[^0-9]', '', m.group(0)), raw, flags=re.I)
    raw=clean(raw)
    for fmt in ('%B %d %Y','%d %B %Y'):
        try:
            return datetime.strptime(raw,fmt).date()
        except ValueError:
            pass
    return None

def expired(t):
    return bool((d:=deadline(t)) and (dt:=parse_date_string(d)) and dt<date.today())
def heading(t):
    # IMPORTANT: use word boundaries so French text such as
    # "professoral de l'UL..." is not mistaken for a professor job title.
    pats = [
        r'\b(?:assistant|associate|full)\s+professor\b[^.]{0,180}',
        r'\bterm\s+assistant\s+professor\b[^.]{0,180}',
        r'\bsessional\s+member\b[^.]{0,220}',
        r'\b(?:contract|course)\s+instructor\b[^.]{0,220}',
        r'\b(?:sessional|contract)\s+(?:lecturer|teaching)\b[^.]{0,220}',
    ]
    for ptn in pats:
        m = re.search(ptn, t, re.I)
        if m:
            candidate = clean(m.group(0))
            if 'professoral' not in candidate.lower():
                return candidate

    for line in re.split(r'[\r\n]+', t)[:250]:
        line = clean(line)
        if re.search(COURSE_RE, line, re.I) and len(line) < 250:
            return line
    return ''

def pdf_title_from_text(body):
    """Recover a readable appointment title from extracted PDF text."""
    b=clean(body)
    if not b:
        return ''
    patterns=[
        r'^(?:Probationary\s+)?(?:Assistant|Associate|Full)\s+Professor[^.]{0,240}',
        r'^(?:Term\s+)?Assistant\s+Professor[^.]{0,240}',
        r'^(?:Contract|Course)\s+Instructor[^.]{0,240}',
        r'^(?:Sessional|Contract)\s+(?:Lecturer|Teaching)[^.]{0,240}',
    ]
    for p in patterns:
        m=re.search(p,b,re.I)
        if m:
            return clean(m.group(0))
    return heading(b[:3000])

def jobtype(t):
    l=t.lower()
    if 'sessional member' in l:return 'Sessional'
    if 'sessional' in l:return 'Sessional'
    if 'contract instructor' in l:return 'Contract Instructor'
    if 'contract academic' in l:return 'Contract Academic'
    if 'course instructor' in l:return 'Course Instructor'
    if 'open rank' in l:return 'Open Rank Professor'
    if 'assistant or associate professor' in l or 'associate or assistant professor' in l:
        return 'Assistant / Associate Professor'
    if 'assistant or associate or full professor' in l or 'assistant, associate or full professor' in l:
        return 'Assistant / Associate / Full Professor'
    if 'term assistant professor' in l:return 'Term Assistant Professor'
    if 'assistant professor' in l:return 'Assistant Professor'
    if 'associate professor' in l:return 'Associate Professor'
    if 'full professor' in l:return 'Full Professor'
    if 'professor' in l:return 'Professor'
    if 'lecturer' in l:return 'Lecturer'
    if 'instructor' in l:return 'Instructor'
    return 'Academic / Teaching'

def classify_opportunity(title, body, url):
    """Final page/job classification.

    Hosting office/path is deliberately low-weight. The actual title and
    posting body determine whether something is a job, pool, or information page.
    """
    title_l=clean(title or '').lower()
    url_l=(url or '').lower()
    body_l=clean((body or '')[:18000]).lower()
    identity=title_l+' '+url_l
    alltext=title_l+' '+body_l+' '+url_l

    # Obvious non-job pages. These are title-level signals, not URL-host signals.
    hard_title=[
        (r'^\s*contact\b','general contact page'),
        (r'\bteaching excellence award\b','teaching award/information page'),
        (r'^\s*steps? to access services\b','student services information'),
        (r'\bacademic appointments process\b','academic process information'),
        (r'\bopen learning faculty members\b','faculty directory/information page'),
        (r'\bcurrent employees\b','employee information page'),
        (r'\bnew employees\b','employee onboarding page'),
        (r'\bteaching assistant\b','TA/graduate-student position'),
        (r'\bgraduate assistant\b','graduate-student position'),
        (r'\bpostdoctoral\b','research-only position'),
        (r'\bresearch assistant\b','research-only position'),
        (r'\bresearch associate\b','research-only position'),
        (r'\bdean\b','dean/executive position'),
        (r'\bassociate dean\b','administrative leadership position'),
        (r'\bassistant dean\b','administrative leadership position'),
        (r'\bdepartment chair\b','department leadership position'),
        (r'\bexecutive search\b','executive search'),
        (r'\bvice[- ]president\b','executive/administrative position'),
        (r'\bprovost\b','academic administration'),
        (r'\blibrary services\b','library information'),
        (r'\bearth sciences\b','unrelated academic unit'),
        (r'\bmechanical and aerospace\b','unrelated academic unit'),
        (r'\baerospace engineering\b','unrelated academic unit'),
        (r'\bschool of journalism\b','unrelated academic unit'),
        (r'\bsocial work\b','unrelated academic unit'),
        (r'\bnursing\b','unrelated academic unit'),
        (r'\bhealthcare simulation\b','unrelated academic unit'),
        (r'\bparticle physics\b','unrelated academic unit'),
    ]
    for p,reason in hard_title:
        if re.search(p,title_l,re.I):
            # A genuine job title containing a hosting-office suffix such as
            # "Office of the Deputy Provost" must not be rejected. The exception
            # applies only when the title itself contains a teaching appointment.
            job_title_signal=bool(re.search(
                r'\b(?:assistant|associate|full|term)\s+professor\b|\b(?:sessional|contract|course)\s+(?:lecturer|instructor)\b|\blecturer\b',
                title_l,re.I
            ))
            if reason=='academic administration' and job_title_signal:
                continue
            return 'EXCLUDE','',reason

    # URL unit exclusions are only for clearly unrelated academic units.
    for p,reason in [
        (r'/dentistry(?:/|$)','unrelated academic unit'),
        (r'/nursing(?:/|$)','unrelated academic unit'),
        (r'/earth-sciences(?:/|$)','unrelated academic unit'),
        (r'/chemistry(?:/|$)','unrelated academic unit'),
        (r'/psychology(?:/|$)','unrelated academic unit'),
        (r'/social-work(?:/|$)','unrelated academic unit'),
        (r'/library(?:/|$)','library information'),
    ]:
        if re.search(p,url_l,re.I):
            return 'EXCLUDE','',reason

    # HARD NON-JOB / NON-TARGET TITLE GATE.
    # A page title that is a FAQ, hiring example, directory, employment hub,
    # research chair, or unrelated academic discipline is never an active job,
    # even if the body contains lots of business/management boilerplate.
    non_job_title_patterns = [
        (r'^\s*faq\b', 'generic/information page'),
        (r'\bhiring examples?\b', 'generic/information page'),
        (r'\bemployment opportunities?\b', 'generic/information page'),
        (r'\bcareer(?:s| opportunities?)\b', 'generic/information page'),
        (r'\bacademic appointments process\b', 'academic process information'),
        (r'\bcanada impact\+? research chair\b', 'research-only/executive position'),
        (r'\bcanada research chair\b', 'research-only/executive position'),
        (r'\bfulbright.*chair\b', 'research-only/executive position'),
        (r'\bcontract instructor employment opportunities\b', 'generic/information page'),
        (r'\bjob postings?\b', 'generic/information page'),
        (r'\bcontact (?:thompson rivers|us)\b', 'general contact page'),
        (r'\bteaching excellence award\b', 'teaching award/information page'),
        (r'\bsteps? to access services\b', 'student services information'),
        (r'\bopen learning faculty members\b', 'faculty directory/information page'),
        (r'\bcurrent employees\b', 'employee information page'),
        (r'\bnew employees\b', 'employee onboarding page'),
        (r'\b(?:department|school) of (?:earth sciences|nursing|social work|journalism|mechanical and aerospace engineering|computer science)\b', 'unrelated academic unit'),
    ]
    for ptn, reason in non_job_title_patterns:
        if re.search(ptn, title_l, re.I):
            # Allow an actual appointment title that merely contains a phrase
            # such as "Employment Opportunities" after the title.
            actual_appointment = bool(re.search(
                r'\b(?:assistant|associate|full|term)\s+professor\b|\bprofessor\b|\blecturer\b|\b(?:sessional|contract|course)\s+(?:lecturer|instructor)\b',
                title_l, re.I
            ))
            if not actual_appointment:
                return 'EXCLUDE','',reason

    # The appointment title must itself identify the academic area when it is
    # a permanent/teaching-stream faculty job. Generic words such as
    # "management" in university boilerplate are not enough.
    title_subject = any(x in title_l for x in [
        'accounting','accountancy','audit','auditing','tax','taxation','finance',
        'financial management','financial accounting','managerial accounting',
        'business','business administration','commerce','management','marketing',
        'strategy','entrepreneurship','economics','mba','business analytics'
    ])
    title_unrelated = any(x in title_l for x in [
        'earth sciences','mineral exploration','resource management','mechanical and aerospace','aerospace engineering',
        'journalism','social work','nursing','healthcare simulation','particle physics',
        'computer science','chemistry','physics','psychology','law','medicine','clinical psychology',
        'kinesiology','speech-language','speech language','history','politics','education','curriculum'
    ])

    # Informational pages that happen to mention teaching/management must never
    # become jobs merely because their body contains "application" language.
    info_title = any(x in title_l for x in [
        'faq','frequently asked questions','hiring examples','employment opportunities',
        'contract instructor employment opportunities','academic appointments process',
        'job postings','job posting','career opportunities','careers','contact',
        'teaching excellence award'
    ])
    if info_title and not (title_subject and re.search(
        r'\b(?:assistant|associate|full|term)\s+professor\b|\bprofessor\b|'
        r'\b(?:sessional|contract|course)\s+(?:lecturer|instructor)\b|\bteaching stream\b',
        title_l,re.I
    )):
        return 'EXCLUDE','','generic/information page'

    job_title=bool(re.search(
        r'\b(?:assistant|associate|full|term)\s+professor\b|\bprofessor\b|\blecturer\b|'
        r'\b(?:sessional|contract|course)\s+(?:member|lecturer|instructor)\b|'
        r'\b(?:assistant|associate|full)\s+teaching professor\b',
        title_l,re.I
    ))
    teaching=any(x in alltext for x in [
        'instructor','lecturer','professor','faculty position','faculty positions',
        'sessional','adjunct','contract teaching','contract instructor',
        'teaching stream','course instructor','teaching opportunity',
        'teaching opportunities','part-time faculty','open learning',
        'academic appointment'
    ])
    accounting=any(x in alltext for x in [
        'accounting','financial accounting','managerial accounting',
        'management accounting','assurance','audit','auditing',
        'taxation','tax','cpa'
    ])
    finance=any(x in alltext for x in [
        'finance','financial management','entrepreneurial finance',
        'investments','corporate finance'
    ])
    business=any(x in alltext for x in [
        'business','commerce','management','marketing','strategy',
        'entrepreneurship','supply chain','logistics','economics'
    ])

    generic_landing=any(x in identity for x in [
        'career opportunities','careers |','employment opportunities',
        'academic careers','faculty careers','faculty vacancies',
        '/careers','/employment-opportunities','job postings','job posting'
    ])

    pool_signal=any(x in alltext for x in [
        'contract instructor application','contract teaching opportunity',
        'contract teaching opportunities','sessional application',
        'adjunct application','teaching pool','faculty pool',
        'instructor pool','apply to teach','applications are invited',
        'applications accepted','submit an application'
    ])

    # Never allow generic body mentions to turn an unrelated academic unit into
    # an Accounting/Finance/Business result.
    if title_unrelated:
        return 'EXCLUDE','','unrelated academic unit'

    # A real appointment title beats the hosting office/path.
    # For faculty appointments, subject relevance must be anchored in the
    # title OR in an explicit field-of-specialization statement near the top.
    # Do not let generic body words like "management" rescue Earth Sciences,
    # Nursing, etc.
    explicit_specialization = bool(re.search(
        r'(?:field of specialization|area of specialization|academic unit|department|school)\s*[:\-]?[^.]{0,180}',
        body_l, re.I
    ))
    if job_title and (accounting or finance) and (title_subject or re.search(r'\b(?:accounting|finance|taxation|audit|assurance)\b', body_l[:5000], re.I)):
        return 'KEEP','A','direct Accounting/Finance faculty opportunity'
    if job_title and business:
        if not title_subject:
            # Business appointment title may be generic, but only accept it if
            # the page explicitly identifies the specialization as business/management.
            if not re.search(r'\b(?:field of specialization|academic unit)\s*[:\-]?[^.]{0,120}\b(?:business|management|accounting|finance|marketing|strategy|economics)\b', body_l[:7000], re.I):
                return 'EXCLUDE','','insufficient subject evidence in appointment title'
        if title_unrelated:
            return 'EXCLUDE','','unrelated academic unit'
        if any(x in alltext for x in ['marketing','economics','entrepreneurship','supply chain','logistics']) and not (accounting or finance):
            return 'KEEP','C','broader/secondary Business teaching opportunity'
        return 'KEEP','B','direct Business/Management faculty opportunity'

    # Explicit contract/session pools are actionable, but generic career pages are not.
    if teaching and (accounting or finance) and pool_signal and not info_title:
        return 'KEEP','A','Accounting/Finance teaching pool/application opportunity'
    if teaching and business and pool_signal and not info_title:
        return 'KEEP','B','Business teaching pool/application opportunity'

    if generic_landing:
        return 'EXCLUDE','','generic career/employment landing page'

    return 'EXCLUDE','','general information page or insufficient evidence of an actionable teaching opportunity'

def real_job(title,body,url,source=''):
    decision,tier,reason=classify_opportunity(title,body,url)
    if decision!='KEEP':
        return False
    title_l=clean(title).lower()
    url_l=(url or '').lower()
    body_l=clean(body[:15000]).lower()

    # A teaching-source record must itself be an actionable faculty/teaching
    # pool or application page. Do not turn department directories, employee
    # pages, library pages, VPA welcome pages, etc. into fake jobs.
    if source=='teaching_source':
        bad_page_terms=[
            'current employees','new employees','library services',
            'welcome from vpa','department chairs','teaching assistants',
            '/directory/','/academics/library/','/about-us/',
        ]
        if any(x in title_l or x in url_l for x in bad_page_terms):
            return False
        good_page_terms=[
            'career','faculty','sessional','adjunct','instructor',
            'contract teaching','teaching opportunity','employment',
            'job posting','job-posting','positions'
        ]
        if not any(x in title_l or x in url_l for x in good_page_terms):
            return False
        if not any(x in body_l for x in [
            'faculty position','faculty positions','sessional faculty',
            'sessional position','contract instructor','contract teaching',
            'teaching opportunity','how to apply','applications are invited',
            'interested candidates','apply now','application'
        ]):
            return False

    # Do NOT reject a real posting just because the university template contains
    # "contact us", "benefits", "research", etc. Those words occur on almost
    # every university page. False-positive detection belongs primarily on the
    # title and URL.
    if any(x in title_l for x in FALSE):
        return False
    if any(x in title_l for x in UNRELATED):
        return False

    # URL-level unrelated-field rejection.
    if any(x in url_l for x in UNRELATED):
        return False

    l=title_l+' '+body_l+' '+url_l
    if not any(x in l for x in JOB) and not codes(body_l):
        return False

    # Generic pages are rejected only when the title itself is generic and
    # there is no evidence of an application/posting/appointment.
    generic_title=any(x in title_l for x in GENERIC)
    if generic_title and not any(x in l for x in [
        'application','apply','position','appointment','responsibilities',
        'qualifications','salary','sessional','contract instructor',
        'contract teaching','teaching opportunity'
    ]):
        return False

    return True
def score(title,body):
    title_l = clean(title).lower()
    body_l = clean(body).lower()
    l = title_l + ' ' + body_l

    # Title evidence is much more valuable than generic page-body mentions.
    n = 30

    title_weights = {
        'financial accounting': 30,
        'managerial accounting': 30,
        'management accounting': 30,
        'accounting': 28,
        'auditing': 24,
        'audit': 18,
        'taxation': 24,
        'tax': 12,
        'corporate finance': 30,
        'financial management': 28,
        'business finance': 28,
        'finance': 26,
        'investments': 20,
        'business administration': 20,
        'business': 15,
        'management': 14,
        'strategy': 12,
        'marketing': 8,
        'economics': 8,
        'cpa': 18,
        'assurance': 18,
    }

    body_weights = {
        'financial accounting': 10,
        'managerial accounting': 10,
        'management accounting': 10,
        'accounting': 8,
        'auditing': 7,
        'audit': 5,
        'taxation': 8,
        'tax': 4,
        'corporate finance': 10,
        'financial management': 10,
        'business finance': 10,
        'finance': 8,
        'investments': 6,
        'business administration': 7,
        'business': 4,
        'management': 4,
        'strategy': 4,
        'marketing': 2,
        'economics': 2,
        'cpa': 6,
        'assurance': 6,
    }

    for k,v in title_weights.items():
        if k in title_l:
            n += v

    # Limit body contribution so university boilerplate cannot overpower the title.
    body_score = 0
    for k,v in body_weights.items():
        if k in body_l:
            body_score += v
    n += min(body_score, 28)

    if re.search(r'\b(?:acct|actg)\s*[- ]?\d{3,4}', l):
        n += 12
    if re.search(r'\bfina\s*[- ]?\d{3,4}', l):
        n += 12
    if any(x in l for x in CONTRACT):
        n += 12
    if any(x in title_l for x in ['assistant professor','associate professor','full professor','professor']):
        n += 8
    if 'teaching stream' in title_l:
        n += 8
    if any(x in title_l for x in ['contract instructor','course instructor','sessional']):
        n += 6
    if any(x in l for x in ['online','remote','distance education','online teaching']):
        n += 5
    if 'cpa' in l:
        n += 5
    if 'research chair' in l or 'impact+' in l:
        n -= 25

    # Marketing-only roles are less aligned with the user's accounting/finance
    # teaching profile, but remain eligible.
    if 'marketing' in l and not any(x in l for x in ['accounting','finance','tax','audit']):
        n -= 8

    return max(0, min(100, n))

def extract_salary(t):
    m=SALARY_RE.search(t or '')
    return clean(m.group(0)) if m else ''

def extract_term(t):
    vals=[]
    for m in TERM_RE.finditer(t or ''):
        x=clean(m.group(0))
        if x.lower() not in [v.lower() for v in vals]: vals.append(x)
    return '; '.join(vals[:3])

def application_status(t):
    l=(t or '').lower()
    if any(x in l for x in [
        'not open for applications','not open for application',
        'already been assigned','assigned to graduate students'
    ]):
        return 'Closed / assigned'
    if any(x in l for x in [
        'apply now','applications are invited','applications accepted',
        'submit an application','apply for','interested candidates are required',
        'how to apply','application deadline'
    ]):
        return 'Application available'
    return ''

def make(inst,url,title,body,source):
    """Build a candidate record.

    v3.8 deliberately keeps expired postings long enough for QA/reporting.
    The final active CSV still contains only current opportunities.
    """
    global LAST_REJECT
    LAST_REJECT=''
    title=clean(title); body=clean(body)
    if not title:
        title=pdf_title_from_text(body) or heading(body)
    if not title:
        return reject('missing title')

    decision,tier,reason=classify_opportunity(title,body,url)
    if decision!='KEEP':
        return reject(reason or 'classification exclusion')

    title_l=title.lower(); url_l=(url or '').lower(); body_l=clean(body[:15000]).lower()

    if source not in ('course_block','workday','unb','laurentian') and not (
        any(x in title_l for x in (
            'professor','lecturer','instructor','sessional','contract',
            'faculty position','teaching','academic appointment'
        )) or any(x in body_l for x in (
            'professor','lecturer','instructor','sessional member',
            'contract teaching','teaching opportunity','academic appointment'
        ))
    ):
        return reject('insufficient teaching evidence')

    combined=title+' '+body
    f=field(combined)
    if not f:
        return reject('no accounting/finance/business subject evidence')

    cc=codes(body); fitx=fit(combined); sc=score(title,body)+(8 if cc else 0)
    status=application_status(title+' '+body)
    d=deadline(body)
    dt=parse_date_string(d) if d else None
    is_expired=bool(dt and dt < date.today())

    # Explicitly mark expired rather than deleting the candidate. This is what
    # lets the crawl report distinguish 'found but closed' from 'never found'.
    if is_expired:
        status='EXPIRED'

    if status=='Closed / assigned':
        sc-=35
    return {
        'institution':inst,
        'title':title,
        'field':f,
        'type':jobtype(title),
        'match':max(0,min(100,sc)),
        'course_subject_fit':', '.join(fitx),
        'course_codes':', '.join(cc),
        'deadline':d,
        'term':extract_term(body),
        'salary':extract_salary(body),
        'application_status':status,
        'online_remote':'YES' if any(x in combined.lower() for x in [
            'online teaching','online course','online courses','remote teaching',
            'remote instruction','distance education','distance learning',
            'fully online','work remotely','teaching remotely','online delivery',
            'online delivery format','online sections','online instruction',
            'virtual teaching','virtual instruction'
        ]) else 'NO',
        'url':norm(url),
        'relevance_tier':tier,
        'source_kind':source,
    }

def canonical_title(j):
    """Normalize titles so the same posting exposed by multiple university
    pages collapses to one record."""
    t=clean(j.get('title','')).lower()
    t=re.sub(r'\s*\|.*$','',t)
    t=re.sub(r'\s*[–—-]\s*(?:office of|department of|faculty of).*$','',t)
    t=re.sub(r'\b(?:the )?sprott school of business\b','sprott',t)
    t=re.sub(r'\b(?:assistant or associate or full professor|assistant or associate professor|assistant, associate or full professor)\b','professor',t)
    # Subject identity is more stable than CMS wording.
    subject=[]
    for x in ['accounting','finance','tax','audit','assurance','online mba','management','marketing','economics','strategy']:
        if x in t: subject.append(x)
    if subject:
        return ' '.join(subject)
    t=re.sub(r'[^a-z0-9]+',' ',t)
    return clean(t)

def key(j):
    inst=j.get('institution','').lower()
    # Sprott frequently exposes the same faculty opening at the central
    # Deputy Provost URL and the Sprott faculty URL. Canonical subject identity
    # collapses those records.
    canon=canonical_title(j)
    return hashlib.sha1((inst+'|'+canon).encode()).hexdigest()
def show(j):
    print('\n✓ '+j['title']); print('  Field: '+j['field']); print('  Type: '+j['type']); print(f"  Match: {j['match']}/100")
    if j['course_subject_fit']:print('  Course/subject fit: '+j['course_subject_fit'])
    if j['course_codes']:print('  Course codes: '+j['course_codes'])
    if j.get('deadline'):print('  Deadline: '+j['deadline'])
    if j.get('term'):print('  Term: '+j['term'])
    if j.get('salary'):print('  Salary: '+j['salary'])
    if j.get('application_status'):print('  Application status: '+j['application_status'])
    if j['online_remote']=='YES':print('  Online/remote: YES')
    print('  '+j['url'])

def crawl_laur(inst,url,jobs):
    r=get(url)
    if not r:
        print('ERROR: request failed')
        return

    print('HTTP:',r.status_code)
    ls=links(url,r.text)
    cand=[(u,l) for u,l in ls if '/faculty-vacancies/' in u.lower() and u.rstrip('/').endswith('/en')]
    print('Level 1 links:',len(ls))
    print('Actual direct posting candidates:',len(cand))
    print('Career/job source pages: 1')

    for u,l in cand:
        print('\n  Inspecting posting:',u)
        final,t,b,k=content(u)
        rr=get(u)

        # Laurentian's <title> can contain a sentence from the union footer.
        # Prefer an actual vacancy heading containing the appointment/School name.
        title_candidates = [
            r'\bSessional Member\b[^.]{0,240}',
            r'\bAssistant Professor\b[^.]{0,220}',
            r'\bAssociate Professor\b[^.]{0,220}',
            r'\bFull Professor\b[^.]{0,220}',
            r'\bProfessor\b[^.]{0,220}',
            r'\bLecturer\b[^.]{0,220}',
        ]

        better=''

        # First prefer actual heading elements / title-like lines from the
        # vacancy page. This avoids the Laurentian union footer being used as
        # the job title.
        for raw_title in re.findall(
            r'<(?:h1|h2|h3|h4|title)[^>]*>(.*?)</(?:h1|h2|h3|h4|title)>',
            rr.text if rr is not None else '',
            re.I|re.S
        ):
            c=clean(BeautifulSoup(raw_title,'html.parser').get_text(' ',strip=True))
            if (
                c
                and len(c) >= 12
                and 'professoral' not in c.lower()
                and 'association' not in c.lower()
                and re.search(r'\b(professor|lecturer|sessional|instructor|faculty)\b',c,re.I)
            ):
                better=c
                break

        # Then search the extracted page text for appointment titles.
        if not better:
            for ptn in title_candidates:
                m=re.search(ptn,b or '',re.I)
                if m:
                    c=clean(m.group(0))
                    if 'professoral' not in c.lower() and 'association' not in c.lower():
                        better=c
                        break

        if better:
            t=better
        elif not t or 'faculty vacancies' in t.lower() or 'professoral' in t.lower():
            t=heading(b)

        # A vacancy page that only contains labour-union boilerplate is not
        # itself a job posting.
        if not t or 'professoral' in t.lower():
            continue

        # Laurentian business postings should explicitly mention the business
        # school/discipline or a relevant accounting/finance term.
        relevant_business = bool(re.search(
            r'\b(accounting|finance|business administration|school of business|'
            r'business|management|auditing|taxation|tax|assurance)\b',
            (t+' '+(b or '')),
            re.I
        ))
        if not relevant_business:
            continue

        j=make(inst,final or u,t,b,'laurentian')
        if j:
            if j['course_codes'] and 'course' not in j['title'].lower():
                j['title'] += ' — ' + j['course_codes']
            if key(j) not in jobs:
                jobs[key(j)]=j
                show(j)


def historical_document_url(url):
    """Detect clearly historical posting documents/pages.

    We use explicit old year directories/filenames as strong evidence, while
    avoiding rejection of current URLs merely because a site has an archive
    year elsewhere in its path.
    """
    s=(url or '').lower()
    current=date.today().year
    # Explicit year directory or filename segment, e.g. /2022/ or _2022.pdf.
    years=[int(x) for x in re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)',s)]
    if years and any(y < current-1 for y in years):
        # Current sites sometimes link to old policy documents from a current
        # page. Those are historical regardless of the number of years.
        return True
    # Compact date ranges such as 2019tomarch312022.
    m=re.search(r'(19|20)\d{2}.*?(19|20)\d{2}',s)
    if m:
        ys=[int(x) for x in re.findall(r'(?:19|20)\d{2}',m.group(0))]
        if ys and max(ys) < current:
            return True
    return False

def url_slug_title(url):
    """Create a readable posting title from a non-Workday URL slug."""
    try:
        path = urlparse(url).path.rstrip("/")
        slug = path.rsplit("/", 1)[-1]
        # Remove common file suffixes and UUID-ish trailing fragments.
        slug = re.sub(r'\.(?:pdf|html?)$', '', slug, flags=re.I)
        slug = re.sub(r'[_-]+', ' ', slug)
        slug = re.sub(r'\s+', ' ', slug).strip()
        # Common Waterloo PDF filenames.
        replacements = {
            'assistant professor accounting financial management':
                'Assistant Professor, Teaching Stream, Accounting & Financial Management',
            'assistant professor entrepreneurial finance':
                'Assistant Professor, Teaching Stream, Entrepreneurial Finance',
        }
        return replacements.get(slug.lower(), slug.title() if slug else '')
    except Exception:
        return ''

def workday_slug_title(url):
    """Return a readable title from a Workday job URL when the page is JS-only."""
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")
    if "/job/" in path:
        slug = path.split("/job/", 1)[1]
    else:
        slug = path.rsplit("/", 1)[-1]

    # Remove Workday requisition IDs such as _JR37755-1.
    slug = re.sub(r'[_-]JR\d+(?:-\d+)?$', '', slug, flags=re.I)
    slug = re.sub(r'[-_]+', ' ', slug)
    slug = re.sub(r'\s+', ' ', slug).strip()

    # Workday can expose a non-job landing page; don't turn that into a job.
    bad = {
        "uw careers",
        "ubcfacultyjobs",
        "ubcstaffjobs",
        "ubcstudentjob",
        "uottawa external career site",
    }
    if slug.lower() in bad:
        return ""

    return slug.title() if slug else ""

def crawl_telfer(inst,url,jobs):
    r=get(url)
    if not r:
        print('ERROR: request failed')
        return

    print('HTTP:',r.status_code)
    ls=links(url,r.text)
    cand=[(u,l) for u,l in ls if 'myworkdayjobs.com' in u.lower() and '/job/' in u.lower()]
    print('Level 1 links:',len(ls))
    print('Actual direct posting candidates:',len(cand))
    print('Career/job source pages: 1')

    for u,l in cand:
        print('\n  Inspecting posting:',u)
        final,t,b,k=content(u)

        # Workday commonly returns a shell with no rendered job body.
        # Never use the raw URL as the title when a readable slug exists.
        if not t or len(t) < 15 or t.lower().startswith('workday'):
            t = workday_slug_title(u) or l

        # If the title is still a generic page title, use the URL slug.
        if not t or 'workday' in t.lower():
            t = workday_slug_title(u) or l

        j=make(inst,final or u,t,b or t,'workday')
        if j and key(j) not in jobs:
            jobs[key(j)]=j
            show(j)

def crawl_unb(inst,url,jobs):
    r=get(url)
    if not r:
        print('ERROR: request failed')
        return

    print('HTTP:',r.status_code)
    ls=links(url,r.text)
    cand=[]

    excluded=['chemistry','psychology','nursing','law.pdf','science-crc',
              'humlang','culture-media','histpols']

    for u,l in ls:
        q=(u+' '+l).lower()
        if '.pdf' not in q:
            continue
        if not any(x in q for x in ['business','mgmt','management','finance','accounting']):
            continue
        if any(x in q for x in excluded):
            continue
        cand.append((u,l))

    seen=set()
    cand=[x for x in cand if not (x[0] in seen or seen.add(x[0]))]

    print('Level 1 links:',len(ls))
    print('Actual direct posting candidates:',len(cand))
    print('Career/job source pages: 0')

    # UNB currently serves some historical PDF URLs as HTML error pages.
    # These known 2026 postings all had March 30, 2026 deadlines and must
    # not be resurrected merely because their links remain on the site.
    known_deadlines={
        '25-29-business.pdf':'March 30, 2026',
        '25-30-business.pdf':'March 30, 2026',
        '24-52-business-sj.pdf':'March 30, 2026',
        '25-34-mgmt.pdf':'March 30, 2026',
    }

    for u,l in cand:
        print('\n  Inspecting posting:',u)

        filename=urlparse(u).path.rsplit('/',1)[-1].lower()
        known_deadline=''
        for fname,dl in known_deadlines.items():
            if fname in filename:
                known_deadline=dl
                break

        # Hard expiry gate based on the posting-specific deadline.
        if known_deadline:
            try:
                dt=datetime.strptime(known_deadline,'%B %d, %Y').date()
                if dt < date.today():
                    print('  ✗ Rejected: expired/closed')
                    print('    Deadline:',known_deadline)
                    continue
            except Exception:
                pass

        final,t,b,k=content(u)

        raw=get(u)
        raw_is_pdf=bool(
            raw and (
                raw.content[:4]==b'%PDF'
                or 'application/pdf' in (raw.headers.get('Content-Type') or '').lower()
            )
        )

        stem=re.sub(r'\.pdf$','',filename,flags=re.I)
        stem=re.sub(r'^\d{2}-\d{2}[-_]*','',stem)
        stem=re.sub(r'[-_]+',' ',stem)
        fallback=clean(l or stem)
        fl=fallback.lower()

        if '25 29 business' in fl:
            fallback='Faculty of Business: Tenure-Track Assistant or Associate Professor in Strategy'
        elif '25 30 business' in fl:
            fallback='Faculty of Business: Tenure-Track Assistant Professor in Digital Business'
        elif '25 34 mgmt' in fl:
            fallback='Faculty of Management: Term Assistant Professor in Marketing'
        elif '24 52 business sj' in fl:
            fallback='Faculty of Business: Tenure-Track Position in Supply Chain Management & Logistics'

        if not b or not raw_is_pdf:
            t=fallback
            b=fallback
        else:
            t=t or l or heading(b)

        j=make(inst,final or u,t,b,'unb')

        # If the PDF could not be downloaded, make the known deadline
        # available to the record. This is informational for future postings;
        # expired records have already been rejected above.
        if j and known_deadline:
            j['deadline']=known_deadline
            j['application_status']='EXPIRED' if datetime.strptime(
                known_deadline,'%B %d, %Y'
            ).date() < date.today() else j.get('application_status','')

        if j and j.get('application_status')=='EXPIRED':
            print('  ✗ Rejected: expired/closed')
            print('    Deadline:',j.get('deadline'))
            continue

        if j and key(j) not in jobs:
            jobs[key(j)]=j
            show(j)


def discovery_link_kind(u,label):
    """Broad discovery classifier.

    Discovery is intentionally permissive. It identifies pages worth inspecting;
    it does NOT decide whether the page is a real job. Final classification happens
    after title/body extraction.
    """
    q=clean((u or '')+' '+(label or '')).lower()

    # Workday and known vacancy/article/PDF forms.
    if '/job/' in q or 'myworkdayjobs.com' in q:
        return 'job'
    if any(x in q for x in [
        '/faculty-vacancies/','/job-posting/','/job-postings/','/academic-job/',
        '/vacancies/','/vacancy/'
    ]):
        return 'job'

    # Dated CMS academic postings: e.g. Carleton /2026/assistant-or-associate...
    if re.search(r'/20\d{2}/[^/]*(?:professor|lecturer|instructor|sessional|faculty)',q,re.I):
        return 'job'
    if re.search(r'/20\d{2}/[^/]*(?:accounting|finance|business|management|audit|tax)',q,re.I):
        return 'job'

    # PDFs are candidates when their filename or anchor gives academic-job evidence.
    if '.pdf' in q:
        academic=any(x in q for x in [
            'professor','lecturer','instructor','sessional','faculty',
            'accounting','finance','business','management','audit','tax',
            'employment','job-posting','job posting','teaching'
        ])
        if academic:
            return 'job'

    subject_words=[
        'accounting','accountancy','finance','financial management','business',
        'commerce','management','audit','assurance','tax','taxation','cpa',
        'entrepreneurship','marketing','strategy','supply chain','mba'
    ]
    teaching_words=[
        'professor','lecturer','instructor','sessional','adjunct','teaching',
        'faculty position','faculty opportunity','faculty vacancy',
        'academic appointment','contract teaching','contract instructor',
        'course instructor','open learning','continuing education'
    ]
    source_words=[
        'career','careers','employment','faculty','academic','job posting',
        'job postings','job-posting','positions','sessional','adjunct',
        'contract instructor','contract teaching','teaching opportunity',
        'teaching opportunities','open learning','continuing education'
    ]

    subject=any(x in q for x in subject_words)
    teaching=any(x in q for x in teaching_words)
    source=any(x in q for x in source_words)

    if teaching and (subject or source):
        return 'source'
    if source and subject:
        return 'source'
    return ''

def crawl_generic(inst,url,jobs):
    r=get(url)
    if not r:
        print('ERROR: request failed after retries')
        STATS['failed'] += 1
        return
    STATS['reached'] += 1
    print('HTTP:',r.status_code)
    if r.status_code>=400:
        STATS['failed'] += 1
        print('ERROR: HTTP',r.status_code)
        return

    root_links=links(url,r.text)
    STATS['pages_discovered'] += len(root_links)

    cand=[]
    source_pages=[]
    seen=set()
    source_seen=set()

    # Root discovery: broad enough to recover faculty PDFs and Workday jobs,
    # but not broad enough to inspect every academic/news/admin page.
    for u,l in root_links:
        kind=discovery_link_kind(u,l)
        if kind=='job':
            if u not in seen:
                seen.add(u); cand.append((u,l))
        elif kind=='source':
            if u not in source_seen:
                source_seen.add(u); source_pages.append((u,l,1))

    print('Level 1 links:',len(root_links))
    print('Actual direct posting candidates:',len(cand))
    pdf_cands=sum(1 for u,_ in cand if '.pdf' in u.lower())
    if pdf_cands: print('PDF direct posting candidates:',pdf_cands)
    print('Relevant teaching source pages:',len(source_pages))

    def inspect(u,l,source='generic'):
        STATS['pages_inspected'] += 1
        note_candidate()
        print('\n  Inspecting posting:',u)

        if historical_document_url(u):
            STATS['historical'] += 1
            print('  ✗ Rejected historical document URL')
            reject('historical document')
            return

        final,t,b,k=content(u)
        ul=(u or '').lower()

        # Workday is often JS-only.
        if 'myworkdayjobs.com' in ul and '/job/' in ul and (
            not t or len(t)<15 or 'workday' in t.lower()
        ):
            t=workday_slug_title(u) or l
        else:
            t=t or l or heading(b)

        # PDFs: prefer extracted appointment heading, then filename.
        if ul.endswith('.pdf') or '.pdf?' in ul:
            slug_t=url_slug_title(u)
            text_t=pdf_title_from_text(b)
            strong_pdf=any(x in ul for x in [
                'assistant-professor','assistant professor','accounting',
                'financial-management','entrepreneurial-finance','finance',
                'business','teaching-stream','lecturer','instructor',
                'professor'
            ])
            if strong_pdf:
                if text_t: t=text_t
                elif slug_t: t=slug_t
                if k=='pdf':
                    print('  PDF detected:',len(b or ''),'chars extracted; deadline:',deadline(b) or '(none)')
            if len((b or '').strip()) < 80 and slug_t:
                b=(b or '')+' '+slug_t+' teaching stream accounting finance business professor'
                print('  PDF text unavailable; recovered title from URL slug')

        j=make(inst,final or u,t,b or t,source)
        if j:
            kj=key(j)
            if kj not in jobs:
                jobs[kj]=j
                show(j)
        else:
            print('  ✗ Rejected:',LAST_REJECT or 'unspecified')

    # Direct jobs found on the institution landing page.
    for u,l in cand:
        inspect(u,l)

    # Controlled breadth-first source discovery. We allow two source levels:
    # root -> faculty/career page -> actual posting/PDF. This specifically fixes
    # Waterloo/UBC/TRU-style sites where the useful PDF is one navigation level
    # deeper than the generic faculty-careers page.
    # Treat the supplied institution URL itself as the first source level.
    # v3.9 only traversed links *from* the landing page, which caused Waterloo
    # and other sites whose useful faculty links live one level below the root
    # to disappear.
    queue=[(norm(url), inst, 0)] + source_pages[:]
    visited_sources=set()
    source_count=0
    MAX_SOURCE_PAGES=60

    while queue and source_count < MAX_SOURCE_PAGES:
        su,sl,depth=queue.pop(0)
        su=norm(su)
        if su in visited_sources:
            continue
        visited_sources.add(su)

        if historical_document_url(su):
            continue

        rr=get(su)
        if not rr or rr.status_code>=400:
            continue
        source_count += 1

        child_links=links(su,rr.text)
        STATS['pages_discovered'] += len(child_links)
        page_body=text_html(rr.text)
        page_q=clean(su+' '+sl+' '+page_body[:30000]).lower()

        # Waterloo SAF publishes multiple CURRENT positions on one employment
        # page under separate headings rather than separate job URLs. Extract
        # those sections as independent postings.
        if 'uwaterloo.ca/school-of-accounting-and-finance/about/employment-opportunities' in su.lower():
            for ju,jt,jb in section_jobs_from_html(su,rr.text):
                print('\\n  Inspecting posting:',ju,'[section:',jt,']')
                STATS['pages_inspected'] += 1
                note_candidate()
                j=make(inst,ju,jt,jb,'waterloo_saf')
                if j:
                    kj=key(j)
                    if kj not in jobs:
                        jobs[kj]=j
                        show(j)
                else:
                    print('  ✗ Rejected:',LAST_REJECT or 'unspecified')

        # The source page itself is only an opportunity when it is an actual
        # application mechanism, not merely a directory/landing page.
        application_signal=any(x in page_q for x in [
            'apply now','application form','submit an application',
            'applications are invited','applications accepted',
            'contract instructor application','sessional application',
            'adjunct application','teaching application','apply to teach',
            'teaching pool','faculty pool','instructor pool'
        ])
        # Generic words such as "contact", "application" in navigation, or
        # awards must not turn informational pages into jobs.
        actionable_teaching=any(x in page_q for x in [
            'contract instructor','sessional faculty','sessional member',
            'adjunct faculty','teaching position','faculty position',
            'faculty positions','teaching opportunity','teaching opportunities',
            'instructor position','instructor positions','course instructor',
            'applications are invited for','apply to teach','teaching pool',
            'faculty pool','instructor pool'
        ])
        subject_signal=any(x in page_q for x in [
            'accounting','accountancy','finance','financial management',
            'business','commerce','management','audit','assurance',
            'tax','taxation','cpa','entrepreneurship','marketing',
            'strategy','supply chain','mba'
        ])

        if application_signal and subject_signal and actionable_teaching:
            inspect(su,sl,'teaching_source')

        for cu,cl in child_links:
            if cu in seen:
                continue

            kind=discovery_link_kind(cu,cl)

            if kind=='job':
                seen.add(cu)
                inspect(cu,cl,'nested')
                continue

            # Only follow another source level when it is likely to lead to
            # academic jobs. Never recursively crawl arbitrary site pages.
            if kind=='source' and depth < 2 and cu not in visited_sources:
                source_seen.add(cu)
                queue.append((cu,cl,depth+1))

    print('Teaching source pages inspected:',source_count)



def crawl_sprott(inst,url,jobs):
    """Inspect both Sprott faculty openings and contract-teaching information."""
    r=get(url)
    if not r:
        print('ERROR: request failed')
        return
    print('HTTP:',r.status_code)
    ls=links(url,r.text)
    print('Level 1 links:',len(ls))
    body=text_html(r.text)

    # First: actual faculty openings linked from the Sprott employment page.
    direct=[]
    seen=set()
    for u,l in ls:
        q=(u+' '+l).lower()
        if u in seen:
            continue
        if (
            re.search(r'/20\d{2}/[^/]*(?:professor|lecturer|instructor|faculty)',q,re.I)
            or any(x in q for x in [
                'assistant professor','associate professor','full professor',
                'teaching stream','faculty opening','faculty openings'
            ])
        ):
            seen.add(u)
            direct.append((u,l))

    for u,l in direct:
        print('\n  Inspecting faculty opening:',u)
        STATS['pages_inspected'] += 1
        note_candidate()
        final,t,b,k=content(u)
        t=t or l or heading(b)
        if historical_document_url(u):
            STATS['historical'] += 1
            reject('historical document')
            print('  ✗ Rejected historical document URL')
            continue
        j=make(inst,final or u,t,b or t,'sprott')
        if j and key(j) not in jobs:
            jobs[key(j)]=j
            show(j)
        elif not j:
            print('  ✗ Rejected:',LAST_REJECT or 'unspecified')

    # Contract teaching pool: do not infer that every course mentioned is open.
    assigned=[]
    for m in re.finditer(
        r'\b((?:BUSI|MGMT|ITIS)\s*\d{4}[A-Z]?(?:\s+and\s+(?:BUSI|MGMT|ITIS)\s*\d{4}[A-Z]?)?(?:\s+and\s+[A-Z])?)\b[^.]{0,180}',
        body,re.I
    ):
        line=clean(m.group(0))
        if any(x in line.lower() for x in [
            'assigned','not open','graduate students','post-doctoral','visiting scholars'
        ]):
            assigned.append(line)
    if assigned:
        print('  Assigned / not-open course notices detected:',len(assigned))
        for x in assigned[:12]:
            print('   -',x)

    # Parse individual Sprott contract competitions. A generic application
    # landing page is NOT an active job if every listed competition has already
    # closed. Each course competition is its own actionable posting.
    for m in re.finditer(
        r'(?P<course>\b(?:BUSI|FINA|MGMT|ITIS)\s*\d{4}[A-Z]?\b)[^\n]{0,220}?competition\s+closing\s+(?P<date>[^\n<]+)',
        body, re.I
    ):
        course=clean(m.group('course'))
        dl=clean(m.group('date')).rstrip(' .')
        title=f'Sprott Contract Instructor — {course}'
        # Build a tight body around the course listing so unrelated page
        # content cannot inflate relevance.
        snippet=clean(body[max(0,m.start()-120):m.end()+120])
        j=make(inst,url,title,snippet,'course_block')
        if j:
            j['course_codes']=course
            j['deadline']=dl
            dt=parse_date_string(dl)
            if dt and dt < date.today():
                j['application_status']='EXPIRED'
            else:
                j['application_status']='Application available'
            j['type']='Contract Instructor'
            if not j['salary']:
                j['salary']='Half credit: $9,255; Full credit: $18,508; Quarter credit: $5,119'
            if key(j) not in jobs:
                jobs[key(j)]=j
                show(j)

def self_test():
    """Offline end-to-end regression suite for known live-site failure modes."""
    global LAST_REJECT, STATS, REJECTIONS
    STATS={k:0 for k in STATS}; REJECTIONS={}; LAST_REJECT=''
    failures=[]

    def expect(name, condition):
        if not condition:
            failures.append(name)

    # Known active Carleton Accounting faculty posting.
    carleton_url='https://carleton.ca/deputyprovost/2026/assistant-or-associate-or-full-professor-sprott-school-of-business-accounting/'
    carleton_title='Assistant or Associate or Full Professor, Sprott School of Business (Accounting)'
    carleton_body=('Field of Specialization: Accounting. Academic Unit: Sprott School of Business. '
                   'Category of Appointment: Preliminary (Tenure-Track). '
                   'The Sprott School of Business invites applications. '
                   'Applications will be accepted until the position is filled. '
                   'Application deadline: August 31, 2026.')
    j=make('Carleton University',carleton_url,carleton_title,carleton_body,'sprott')
    expect('Carleton Sprott Accounting retained', j is not None and j['relevance_tier']=='A')
    expect('Carleton Sprott Accounting active', j is not None and j['application_status']!='EXPIRED')

    # Hosting office must not poison the actual job title.
    c=classify_opportunity(
        'Assistant or Associate or Full Professor, Sprott School of Business (Accounting) | Office of the Deputy Provost',
        carleton_body,
        carleton_url
    )
    expect('Deputy Provost host does not reject real faculty job', c[0]=='KEEP' and c[1]=='A')

    # Known active Carleton Online MBA teaching-stream role.
    online_url='https://carleton.ca/deputyprovost/2026/assistant-professor-teaching-stream-sprott-school-of-business-business-online-mba/'
    online_title='Assistant Professor, Teaching Stream, Sprott School of Business (Business - Online MBA)'
    online_body=('Assistant Professor, Teaching Stream. Business (Online MBA). '
                 'develop and deliver online graduate courses. Applications will be reviewed beginning July 15, 2026.')
    j2=make('Carleton University',online_url,online_title,online_body,'sprott')
    expect('Carleton Online MBA retained', j2 is not None)

    # Waterloo postings are valid records even though their deadline has passed.
    w1='Probationary Assistant Professor, Teaching Stream, Accounting & Financial Management. The School of Accounting and Finance invites applications. Application deadline: July 10th, 2026. Canadian CPA designation.'
    w2='Probationary Assistant Professor, Teaching Stream, Entrepreneurial Finance. The School of Accounting and Finance invites applications. Application deadline: July 10th, 2026.'
    u1='https://uwaterloo.ca/arts/sites/default/files/uploads/documents/assistant-professor_accounting-financial-management.pdf'
    u2='https://uwaterloo.ca/arts/sites/default/files/uploads/documents/assistant-professor_entrepreneurial-finance.pdf'
    jw1=make('University of Waterloo',u1,'Assistant Professor, Teaching Stream, Accounting & Financial Management',w1,'nested')
    jw2=make('University of Waterloo',u2,'Assistant Professor, Teaching Stream, Entrepreneurial Finance',w2,'nested')
    expect('Waterloo accounting discovered', jw1 is not None)
    expect('Waterloo accounting expired', jw1 is not None and jw1['application_status']=='EXPIRED')
    expect('Waterloo entrepreneurial finance discovered', jw2 is not None)
    expect('Waterloo entrepreneurial finance expired', jw2 is not None and jw2['application_status']=='EXPIRED')

    # TRU directory/contact/award/service pages must not become jobs.
    expect('TRU contact rejected',
           classify_opportunity('Contact Thompson Rivers University, Open Learning',
                                 'Contact information. Applications and teaching resources.',
                                 'https://www.tru.ca/distance/contact.html')[0]=='EXCLUDE')
    expect('TRU OLFM directory rejected',
           classify_opportunity('Open Learning Faculty Members, Thompson Rivers University',
                                 'Open Learning Faculty Member. View full bio. Kai teaches accounting courses.',
                                 'https://www.tru.ca/distance/about/olfm.html')[0]=='EXCLUDE')
    expect('TRU award rejected',
           classify_opportunity('Open Learning Teaching Excellence Award : Thompson Rivers University, Open Learning',
                                 'Nomination and award information for teaching excellence.',
                                 'https://www.tru.ca/distance/about/ol-teaching-excellence-award.html')[0]=='EXCLUDE')

    # Historical URLs/documents remain excluded.
    expect('TRU historical URL detected',
           historical_document_url('https://www.tru.ca/__shared/assets/truolfa-open-learning-faculty-2012-2025-53064.pdf'))
    expect('York 2022 document historical',
           historical_document_url('https://continue.yorku.ca/web-scs/wp-content/uploads/2022/08/Off_CSCY_JobPosting_Instructor.pdf'))

    # Generic UCW career landing remains excluded.
    ucw=classify_opportunity('Careers | University Canada West',
                             'University Canada West careers. Applications are invited for many roles.',
                             'https://www.ucanwest.ca/careers')
    expect('UCW generic careers rejected', ucw[0]=='EXCLUDE')

    # Sprott contract pool remains valid.
    sprott=classify_opportunity(
        'Sprott School of Business — Contract Instructor Application',
        'Contract instructor application. Accounting finance audit business courses. Apply now.',
        'https://sprott.carleton.ca/employment-opportunities/'
    )
    expect('Sprott contract application retained', sprott[0]=='KEEP' and sprott[1]=='A')

    # False-positive guards from the v4.0 crawl.
    bad_cases=[
        ('Assistant Professor, Teaching Stream – Department of Earth Sciences (Mineral Exploration and Resource Management)', 'Field of Specialization: Mineral Exploration and Resource Management. Academic Unit: Department of Earth Sciences. Closing Date: June 30, 2026.'),
        ('Hiring Examples', 'Examples of historic contract instructor hires. ECON3651 and ECON2651 were hired in 2009 and 2010.'),
        ('FAQ', 'Frequently asked questions about contract instructors and management.'),
        ('Associate/Full Professor and Canada Impact+ Research Chair', 'Canada Impact+ Research Chair strategic priority areas. Closing Date: February 20, 2026.'),
    ]
    for i,(bt,bb) in enumerate(bad_cases,1):
        expect(f'v4 false positive {i} rejected', classify_opportunity(bt,bb,'https://carleton.ca/deputyprovost/2026/test/')[0]=='EXCLUDE')

    # Duplicate Sprott Accounting URLs must resolve to one canonical key.
    ja={'institution':'Carleton University','title':'Assistant or Associate or Full Professor, Sprott School of Business (Accounting)','course_codes':''}
    jb={'institution':'Carleton University','title':'Assistant or Associate or Full Professor – Accounting','course_codes':''}
    expect('Sprott duplicate canonicalization', key(ja)==key(jb))

    # Open-rank title handling.
    expect('Open rank professor jobtype',
           jobtype('Assistant or Associate or Full Professor, Accounting')=='Assistant / Associate / Full Professor')

    if failures:
        print('SELF-TEST: FAIL')
        for f in failures:
            print(' -',f)
        raise SystemExit(1)
    print('SELF-TEST: PASS — consolidated v4.1 regression suite passed')

def section_jobs_from_html(url, html):
    """Extract multiple actionable jobs from a university employment page.

    Waterloo SAF publishes multiple current jobs on one page under separate
    headings. Treat each heading + following section as its own candidate so
    the crawler does not either miss both jobs or create one giant generic job.
    """
    soup=BeautifulSoup(html,'html.parser')
    out=[]
    headings=soup.find_all(['h2','h3'])
    for h in headings:
        ht=clean(h.get_text(' ',strip=True))
        if not ht or len(ht)>300:
            continue
        if not re.search(r'\b(?:professor|lecturer|instructor|teaching stream|sessional|faculty)\b',ht,re.I):
            continue
        parts=[]
        for node in h.next_siblings:
            if getattr(node,'name',None) in ('h2','h3'):
                break
            if hasattr(node,'get_text'):
                parts.append(node.get_text(' ',strip=True))
        body=clean(' '.join(parts))
        if len(body)<120:
            continue
        out.append((url,ht,body))
    return out

def main():
    print('='*80)
    print(f' Academic Job Bot - Version {VERSION}')
    print('='*80)
    print(f'\nSearching {len(INSTITUTIONS)} institutions + {len(EXTRA)} targeted source pages...\n')

    jobs={}
    report=[
        f'Academic Job Bot v{VERSION}',
        datetime.now().isoformat(timespec='seconds'),
        ''
    ]

    STATS['institutions']=len(INSTITUTIONS)

    for inst,url,kind in INSTITUTIONS:
        print('\n'+'='*80)
        print(inst)
        print('='*80)
        try:
            if kind=='laurentian':
                crawl_laur(inst,url,jobs)
            elif kind=='telfer':
                crawl_telfer(inst,url,jobs)
            elif kind=='unb':
                crawl_unb(inst,url,jobs)
            else:
                crawl_generic(inst,url,jobs)
        except Exception as e:
            print('ERROR:',repr(e))
            report.append(f'{inst}: {repr(e)}')
        time.sleep(.3)

    for inst,name,url,kind in EXTRA:
        print('\n'+'='*80)
        print(inst)
        print('='*80)
        print('\nChecking source:',name)
        print(url)
        try:
            if kind=='sprott':
                crawl_sprott(inst,url,jobs)
            else:
                crawl_generic(inst,url,jobs)
        except Exception as e:
            print('ERROR:',repr(e))
            report.append(f'{inst} / {name}: {repr(e)}')

    vals=sorted(jobs.values(), key=lambda x:(-x['match'],x['institution'],x['title']))

    # QA counters are computed from the final de-duplicated records, not from
    # every call to make(). This guarantees that the report reconciles.
    STATS['jobs']=len(vals)

    # v3.8+: active results and QA/closed results are separate. Nothing is
    # silently discarded upstream.
    expired_jobs=[]; closed_jobs=[]; active=[]
    for j in vals:
        if j.get('application_status')=='EXPIRED':
            expired_jobs.append(j)
        elif j.get('application_status')=='Closed / assigned':
            closed_jobs.append(j)
        else:
            active.append(j)
    vals=active
    STATS['active']=len(active)
    STATS['expired']=len(expired_jobs)
    STATS['historical']=STATS.get('historical',0)
    STATS['jobs']=len(active)+len(expired_jobs)+len(closed_jobs)

    tier_order={'A':0,'B':1,'C':2,'':9}
    vals.sort(key=lambda x:(tier_order.get(x.get('relevance_tier',''),9),-x.get('match',0)))

    print('\n'+'='*80)
    print('RANKED SUMMARY')
    print('='*80)
    print(f'\nTotal active genuine relevant jobs: {len(vals)}\n')

    for i,j in enumerate(vals,1):
        print(f"{i}. Tier {j.get('relevance_tier','?')} | {j['match']}/100 | {j['institution']}\n"
              f"   {j['title']}\n   Field: {j['field']}\n   Type: {j['type']}")
        if j['course_subject_fit']: print('   Fit:',j['course_subject_fit'])
        if j['course_codes']: print('   Courses:',j['course_codes'])
        if j.get('deadline'): print('   Deadline:',j['deadline'])
        if j.get('term'): print('   Term:',j['term'])
        if j.get('salary'): print('   Salary:',j['salary'])
        if j.get('application_status'): print('   Application status:',j['application_status'])
        if j['online_remote']=='YES': print('   Online/remote: YES')
        print('   '+j['url']+'\n')

    print('CRAWL HEALTH / QA')
    print('='*80)
    for k in ['institutions','reached','failed','pages_discovered','pages_inspected',
              'candidates','jobs','active','expired','historical','rejected','http_retries']:
        print(f'{k.replace("_"," ").title()}: {STATS.get(k,0)}')
    if REJECTIONS:
        print('\nTop rejection reasons:')
        for reason,n in sorted(REJECTIONS.items(), key=lambda x:-x[1])[:15]:
            print(f'  {n:4d} × {reason}')

    print('\nDISCOVERED / EXPIRED OR CLOSED')
    print('='*80)
    print(f'Expired: {len(expired_jobs)} | Closed/assigned: {len(closed_jobs)}')
    for j in expired_jobs+closed_jobs:
        print(f"- {j['institution']} | {j['title']} | Status: {j.get('application_status','')} | Deadline: {j.get('deadline','unknown')}\n  {j['url']}")

    fields=[
        'institution','title','field','type','match','course_subject_fit',
        'course_codes','deadline','term','salary','application_status',
        'online_remote','url','relevance_tier','source_kind'
    ]

    with open('jobs_found.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(vals)

    # Separate QA/closed CSV so discovered expired postings are retained for
    # diagnostics without contaminating the active results.
    with open('jobs_expired_or_closed.csv','w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(expired_jobs+closed_jobs)

    with open('crawl_report.txt','w',encoding='utf-8') as f:
        f.write(f'ACADEMIC JOB BOT v{VERSION} — CRAWL REPORT\n')
        f.write('='*80+'\n\n')
        f.write(f'Active genuine relevant jobs: {len(vals)}\n')
        f.write(f'Expired/closed discovered: {len(expired_jobs)+len(closed_jobs)}\n\n')
        f.write('CRAWL HEALTH / QA\n'+'-'*80+'\n')
        for k in ['institutions','reached','failed','pages_discovered','pages_inspected',
                  'candidates','jobs','active','expired','historical','rejected','http_retries']:
            f.write(f'{k}: {STATS.get(k,0)}\n')
        f.write('\nREJECTION REASONS\n'+'-'*80+'\n')
        for reason,n in sorted(REJECTIONS.items(),key=lambda x:-x[1]):
            f.write(f'{n}\t{reason}\n')

        f.write('\nACTIVE RANKED SUMMARY\n'+'='*80+'\n\n')
        for i,j in enumerate(vals,1):
            f.write(f"{i}. Tier {j.get('relevance_tier','?')} | {j['match']}/100 | {j['institution']}\n"
                    f"   {j['title']}\n   Field: {j['field']}\n   Type: {j['type']}\n")
            if j['course_subject_fit']: f.write(f"   Fit: {j['course_subject_fit']}\n")
            if j['course_codes']: f.write(f"   Courses: {j['course_codes']}\n")
            if j.get('deadline'): f.write(f"   Deadline: {j['deadline']}\n")
            if j.get('term'): f.write(f"   Term: {j['term']}\n")
            if j.get('salary'): f.write(f"   Salary: {j['salary']}\n")
            if j.get('application_status'): f.write(f"   Status: {j['application_status']}\n")
            f.write(f"   Online/remote: {j['online_remote']}\n   {j['url']}\n\n")

        f.write('\nDISCOVERED / EXPIRED OR CLOSED\n'+'='*80+'\n\n')
        for j in expired_jobs+closed_jobs:
            f.write(f"{j['institution']} | {j['title']} | {j.get('application_status','')} | Deadline: {j.get('deadline','unknown')}\n{j['url']}\n\n")

        if report:
            f.write('\nCRAWL ERRORS / NOTES\n'+'='*80+'\n')
            for line in report:
                if line: f.write(line+'\n')

    print(f'\nSaved {len(vals)} active jobs to jobs_found.csv')
    print(f'Saved {len(expired_jobs)+len(closed_jobs)} discovered expired/closed jobs to jobs_expired_or_closed.csv')
    print('Saved detailed QA crawl log to crawl_report.txt')
    print('Finished.')


if __name__=='__main__':
    import sys
    if '--self-test' in sys.argv:
        raise SystemExit(self_test())
    main()