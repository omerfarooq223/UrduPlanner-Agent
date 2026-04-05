# 🚀 Running UrduPlanner Web Frontend

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
```bash
cp .env.example .env
# Edit .env and add your OLLAMA_BASE_URL
export OLLAMA_BASE_URL=your_key_here
```

### 3. Start the Web Server
```bash
python app.py
```

The application will be available at **http://127.0.0.1:5001**

## What's New (v3.0 - Web Frontend)

### Features
✨ **Beautiful Web Interface** - Modern, responsive design with orange and white theme
📱 **Drag & Drop** - Easily upload files by dragging them to the upload boxes
🎯 **Step-by-Step Workflow** - Clear, intuitive process: Upload → Validate → Fill Form → Generate → Download
📊 **Real-time Progress** - Visual progress indicator while generating your lesson plan
⚡ **Instant Download** - Download your generated lesson plan directly from the browser
🎨 **Mobile Friendly** - Works great on desktop, tablet, and mobile devices

### File Structure
```
UrduPlanner/
├── app.py                 # Flask web server
├── main.py                # Original CLI (still available)
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Main webpage
└── static/
    ├── style.css          # Styling (Orange & White theme)
    └── script.js          # Frontend logic
```

## Browser Compatibility

✅ Chrome/Edge (Latest)
✅ Firefox (Latest)
✅ Safari (Latest)
✅ Mobile browsers

## Troubleshooting

### Port Already in Use
If port 5001 is already in use, modify the `PORT` value in `.env` or export it before running:
```bash
echo "PORT=5002" >> .env
```

Or set it for the current terminal session:
```bash
export PORT=5002
```

You can also hardcode a port in `app.py` if needed:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change to 5001 or any available port
```

### CORS Issues
The Flask-CORS extension handles cross-origin requests automatically.

### File Upload Size Issues
Maximum file size is 50 MB. Edit `app.py` to increase:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
```

## Using the Web Interface

### Step 1: Upload Files
- **Template File**: Word document (.docx) with your lesson plan layout
- **Textbook PDF**: PDF of the textbook to extract content from

You can drag and drop files or click to browse.

### Step 2: Validate
Click "Validate Files" to ensure both files are valid.

### Step 3: Enter Details
- **Week Number**: Which week of the academic year
- **Date Range**: When this week runs (e.g., "9 March to 13 March")
- **Page Range**: Pages to extract (supports: `99-108`, `1, 3, 5-10`, etc.)
- **Subject**: Subject name (e.g., Urdu, Islamiyat, English)

### Step 4: Generate
Click "Generate Lesson Plan" and wait for processing.

### Step 5: Download
Once complete, download your ready-to-print lesson plan!

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve main page |
| `/api/validate-files` | POST | Validate uploaded files |
| `/api/generate-plan` | POST | Generate lesson plan |
| `/api/download/<filename>` | GET | Download generated file |

## Development Mode

The Flask app runs in debug mode by default. This means:
- Changes to Python code will auto-reload
- Detailed error messages are displayed
- Browser debug toolbar is available

To disable debug mode for production:
```python
app.run(debug=False, host='0.0.0.0', port=5001)
```

## Performance Tips

- Use a modern computer with at least 4GB RAM
- Large PDFs (500+ pages) may take longer to process
- Keep your OLLAMA_BASE_URL private
- Don't share the upload folder contents

## Support

For issues, check:
1. Are all dependencies installed? (`pip list`)
2. Is OLLAMA_BASE_URL set? (`echo $OLLAMA_BASE_URL`)
3. Are Tesseract and Urdu language pack installed?
4. Check logs in the `logs/` directory

## Still Want to Use CLI?

The original CLI is still available:
```bash
python main.py
```

---

**UrduPlanner v3.0** - Web Frontend Edition
