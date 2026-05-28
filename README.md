# HireIQ — AI Resume Screener
### FlowZint AI Hackathon 2026 | Open Innovation Category

An AI-powered automation system that screens, scores, and ranks resumes against a job description — with email notifications.

---

## 🚀 Features
- Upload multiple PDF resumes at once
- AI scores each resume 0–100 against the job description
- Ranked results: matched skills, missing skills, experience summary
- Shortlist / Maybe / Reject recommendation per candidate
- **Email report** sent to HR after every analysis
- Deploy to cloud in 5 minutes via Render.com

---

## 🛠️ Run Locally

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables
```bash
# Required
export ANTHROPIC_API_KEY=your_key_here   # https://console.anthropic.com

# Optional — for email reports
export SMTP_USER=your_gmail@gmail.com
export SMTP_PASSWORD=your_app_password   # Gmail App Password (not your login password)
export SMTP_FROM=your_gmail@gmail.com
```

### 3. Run
```bash
python app.py
# Open http://localhost:5000
```

---

## ☁️ Deploy to Render.com (Free Hosting)

1. Push this project to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` and configures everything
5. Add environment variables in the Render dashboard:
   - `ANTHROPIC_API_KEY` → your Anthropic key
   - `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` → your Gmail credentials
6. Click **Deploy** — your app will be live at `https://your-app.onrender.com`

> **Gmail App Password:** Go to Google Account → Security → 2-Step Verification → App Passwords → Generate one for "Mail"

---

## 📁 Project Structure
```
resume-screener/
├── app.py              # Flask backend + Claude AI + Email logic
├── requirements.txt    # Dependencies (flask, anthropic, pdfplumber, gunicorn)
├── render.yaml         # Render.com deployment config
├── pitch.html          # Hackathon submission pitch page
├── README.md           # This file
├── uploads/            # Temp PDF storage (auto-cleaned after each analysis)
└── templates/
    └── index.html      # Frontend UI
```

---

## 🧠 How It Works
1. User uploads PDFs + pastes job description
2. Flask extracts text from each PDF using `pdfplumber`
3. Each resume → Claude AI with job description → structured JSON response
4. Results sorted by score and rendered in ranked UI
5. Optional: formatted HTML email report sent to HR via SMTP

---

## 🏆 Hackathon Info
- **Event:** FlowZint AI Hackathon 2026
- **Category:** Open Innovation
- **Submission Portal:** https://flowzint.in/2026/ai/hackothon
- **Deadline:** 4th July 2026
