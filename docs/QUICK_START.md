# Quick Start - UrduPlanner Web Frontend

## 5-Minute Setup

```bash
# 1. Navigate to project
cd /Users/muhammadomerfarooq/Desktop/omer/UrduPlanner

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Start Ollama and pull model (first time only)
ollama serve
# in another terminal:
ollama pull mistral:7b

# 4. Configure environment
cp .env.example .env
# Optional: edit OLLAMA_BASE_URL if not using localhost

# 5. Run server
python app.py

# 6. Open browser
# http://127.0.0.1:5001
```

## Common Issues

**Port 5001 in use?**

```bash
# Change port in app.py run section
```

**Ollama not running or model missing?**

```bash
ollama serve
ollama pull mistral:7b
```

**Tesseract not installed?**

```bash
brew install tesseract tesseract-lang
```

## Helpful Links

- [Flask Docs](https://flask.palletsprojects.com/)
- [Ollama](https://ollama.ai)
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
