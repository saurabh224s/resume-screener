from flask import Flask, request, jsonify, render_template
import os
import json
import smtplib
import anthropic
import pdfplumber
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

client = anthropic.Anthropic()

# ── Email config (set via env vars) ──────────────────────────────────────────
SMTP_HOST     = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER     = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM     = os.environ.get('SMTP_FROM', SMTP_USER)


def extract_text_from_pdf(filepath):
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        text = f"[Error reading PDF: {str(e)}]"
    return text.strip()


def analyze_resume(resume_text, job_description, filename):
    prompt = f"""You are an expert HR recruiter and resume analyst. Analyze this resume against the job description and return ONLY a JSON object.

JOB DESCRIPTION:
{job_description}

RESUME ({filename}):
{resume_text[:3000]}

Return ONLY this JSON (no markdown, no explanation):
{{
  "name": "candidate full name or 'Unknown'",
  "match_score": <integer 0-100>,
  "experience_years": <integer or 0>,
  "top_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "missing_skills": ["missing1", "missing2", "missing3"],
  "summary": "2-3 sentence evaluation of this candidate for the role",
  "recommendation": "Shortlist" or "Maybe" or "Reject"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def send_shortlist_email(to_email, hr_name, job_title, results):
    """Send a formatted shortlist summary email to HR."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return False, "SMTP credentials not configured"

    shortlisted = [r for r in results if r.get('recommendation') == 'Shortlist']
    maybe       = [r for r in results if r.get('recommendation') == 'Maybe']
    rejected    = [r for r in results if r.get('recommendation') == 'Reject']
    date_str    = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # ── Build HTML rows ───────────────────────────────────────────────────────
    def rows(candidates, color, label):
        if not candidates:
            return ""
        html = ""
        for c in candidates:
            skills = ", ".join(c.get('top_skills', [])[:4]) or "—"
            html += f"""
            <tr>
              <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;">
                <strong style="color:#1a1a2e;">{c['name']}</strong><br>
                <span style="font-size:12px;color:#888;">{c['filename']}</span>
              </td>
              <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;text-align:center;">
                <span style="background:{color};color:white;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600;">{c['match_score']}</span>
              </td>
              <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;">
                <span style="background:#f0f0ff;color:#6c63ff;padding:3px 10px;border-radius:20px;font-size:12px;">{label}</span>
              </td>
              <td style="padding:12px 16px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#555;">{skills}</td>
            </tr>"""
        return html

    all_rows = (
        rows(shortlisted, "#4ade80", "Shortlist") +
        rows(maybe,       "#fbbf24", "Maybe") +
        rows(rejected,    "#f87171", "Reject")
    )

    html_body = f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;background:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

  <!-- Header -->
  <tr><td style="background:linear-gradient(135deg,#6c63ff,#a78bfa);padding:36px 40px;">
    <h1 style="margin:0;color:white;font-size:24px;font-weight:800;">🧠 HireIQ Resume Report</h1>
    <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);font-size:14px;">Generated on {date_str}</p>
  </td></tr>

  <!-- Greeting -->
  <tr><td style="padding:32px 40px 0;">
    <p style="color:#333;font-size:16px;margin:0;">Hi {hr_name or 'there'},</p>
    <p style="color:#555;font-size:15px;line-height:1.6;">
      Your AI resume screening for <strong style="color:#6c63ff;">{job_title or 'the role'}</strong> is complete.
      Here's the ranked summary of all {len(results)} candidate(s).
    </p>
  </td></tr>

  <!-- Stats row -->
  <tr><td style="padding:20px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td align="center" style="background:#f0fff4;border-radius:12px;padding:16px;">
          <div style="font-size:28px;font-weight:800;color:#4ade80;">{len(shortlisted)}</div>
          <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Shortlisted</div>
        </td>
        <td width="12"></td>
        <td align="center" style="background:#fffbeb;border-radius:12px;padding:16px;">
          <div style="font-size:28px;font-weight:800;color:#fbbf24;">{len(maybe)}</div>
          <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Maybe</div>
        </td>
        <td width="12"></td>
        <td align="center" style="background:#fff1f1;border-radius:12px;padding:16px;">
          <div style="font-size:28px;font-weight:800;color:#f87171;">{len(rejected)}</div>
          <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Rejected</div>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- Table -->
  <tr><td style="padding:0 40px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #f0f0f0;border-radius:12px;overflow:hidden;">
      <tr style="background:#fafafa;">
        <th style="padding:12px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Candidate</th>
        <th style="padding:12px 16px;text-align:center;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Score</th>
        <th style="padding:12px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Status</th>
        <th style="padding:12px 16px;text-align:left;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:0.5px;">Top Skills</th>
      </tr>
      {all_rows}
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:#fafafa;padding:24px 40px;border-top:1px solid #f0f0f0;text-align:center;">
    <p style="margin:0;font-size:12px;color:#aaa;">Powered by HireIQ · FlowZint AI Hackathon 2026</p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"HireIQ Report: {len(results)} resumes screened for '{job_title or 'the role'}'"
        msg['From']    = SMTP_FROM
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    job_description = request.form.get('job_description', '').strip()
    job_title       = request.form.get('job_title', '').strip()
    hr_name         = request.form.get('hr_name', '').strip()
    notify_email    = request.form.get('notify_email', '').strip()
    files           = request.files.getlist('resumes')

    if not job_description:
        return jsonify({'error': 'Job description is required'}), 400
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'At least one resume is required'}), 400

    results = []
    for file in files:
        if file and file.filename.endswith('.pdf'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            resume_text = extract_text_from_pdf(filepath)
            os.remove(filepath)

            try:
                result = analyze_resume(resume_text, job_description, file.filename)
                result['filename'] = file.filename
                results.append(result)
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'name': 'Parse Error',
                    'match_score': 0,
                    'experience_years': 0,
                    'top_skills': [],
                    'missing_skills': [],
                    'summary': f'Could not analyze this resume: {str(e)}',
                    'recommendation': 'Reject'
                })

    results.sort(key=lambda x: x.get('match_score', 0), reverse=True)

    email_status = None
    if notify_email:
        success, msg = send_shortlist_email(notify_email, hr_name, job_title, results)
        email_status = {'sent': success, 'message': msg}

    return jsonify({'results': results, 'email_status': email_status})


if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True, port=5000)
