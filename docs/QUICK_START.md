# Quick Start - UrduPlanner Web Frontend

## 5-Minute Setup

```bash
# 1. Navigate to project
cd /Users/muhammadomerfarooq/Desktop/GitHub\ Repository/UrduPlanner

# 2. Install dependencies (first time only)
python -m pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 4. Run server
python app.py

# 5. Open browser
# http://127.0.0.1:5001
```

## Common Issues

**Port 5001 in use?**

```bash
# Change port in app.py run section
```

**Groq API key missing or invalid?**

```bash
echo "GROQ_API_KEY=your_key_here" >> .env
```

**Tesseract not installed?**

```bash
brew install tesseract tesseract-lang
```

## Helpful Links

- [Flask Docs](https://flask.palletsprojects.com/)
- [Groq](https://console.groq.com)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
