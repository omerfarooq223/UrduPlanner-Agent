# UrduPlanner Web Frontend - Complete Guide

## 📋 What's Been Added

Your UrduPlanner project now has a **beautiful, modern web interface** replacing the CLI. Here's what's new:

### New Files Created
- **`app.py`** - Flask web application (backend API)
- **`templates/index.html`** - Main webpage
- **`static/style.css`** - Styling with orange & white theme
- **`static/script.js`** - Frontend interactivity
- **`FRONTEND.md`** - Quick start guide

### Updated Files
- **`requirements.txt`** - Added Flask, Flask-CORS, Werkzeug

---

## 🎨 Design Features

### Color Scheme
- **Primary Orange**: `#FF9500` - Buttons, highlights, accents
- **White**: `#FFFFFF` - Clean backgrounds
- **Gradients**: Beautiful orange-to-white transitions
- **Shadows**: Professional depth and layering

### UI Components
✅ Drag-and-drop file upload boxes
✅ Real-time file validation
✅ Multi-step wizard workflow
✅ Beautiful form inputs
✅ Smooth animations and transitions
✅ Progress bars with percentage
✅ Responsive mobile design
✅ Accessibility features

---

## 🚀 How to Start

### Prerequisites
- Python 3.10+
- Tesseract OCR with Urdu language support
- GROQ API key (free from https://console.groq.com)

### Installation

1. **Navigate to project folder**
   ```bash
   cd /Users/muhammadomerfarooq/Desktop/omer/UrduPlanner
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your GROQ_API_KEY
   nano .env
   ```

4. **Run the web server**
   ```bash
   python app.py
   ```

5. **Open in browser**
   - Go to: **http://127.0.0.1:5001**

---

## 💻 User Workflow

### Step 1️⃣: Upload Files
![](https://via.placeholder.com/400x200?text=Upload+Screen)

- **Word Template**: Your lesson plan template (.docx)
- **Textbook PDF**: The textbook to extract content from (.pdf)
- Drag files in or click to browse
- Click **"Validate Files"** when ready

### Step 2️⃣: Enter Details
After validation, fill in:
- **Week Number**: e.g., `8`
- **Date Range**: e.g., `9 March to 13 March`
- **Page Range**: e.g., `99-108` or `1, 3, 5-10`
- **Subject**: e.g., `Urdu`, `Islamiyat`, `English`

### Step 3️⃣: Generate
Click **"Generate Lesson Plan"** - watch the progress bar as:
1. 📄 Content is extracted from PDF
2. 🔧 Garbled text is repaired
3. 🤖 LLM generates lessons
4. 📋 Template is filled with content

### Step 4️⃣: Download
Once complete, download your `.docx` file directly!

---

## 📱 Responsive Design

Works perfectly on:
- 💻 **Desktop** (1920px and up)
- 📱 **Tablet** (768px - 1024px)
- 📱 **Mobile** (375px - 480px)

All sections adapt beautifully to screen size.

---

## 🔧 API Reference

### POST `/api/validate-files`
Validates uploaded files and returns page count.
```json
{
  "template": File,
  "textbook": File
}
```
Response:
```json
{
  "success": true,
  "template_path": "/path/to/template",
  "textbook_path": "/path/to/textbook", 
  "max_pages": 150
}
```

### POST `/api/generate-plan`
Generates the lesson plan with provided details.
```json
{
  "week": "8",
  "dates": "9 March to 13 March",
  "pages": "99-108",
  "subject": "Urdu",
  "template_path": "/path/to/template",
  "textbook_path": "/path/to/textbook"
}
```

Response:
```json
{
  "success": true,
  "output_file": "urdu_planner_w8_20240405_123456.docx",
  "message": "Lesson plan generated successfully!"
}
```

### GET `/api/download/<filename>`
Downloads the generated lesson plan file.

---

## 🎯 Feature Highlights

### ✨ Beautiful UI/UX
- Modern gradient header
- Smooth animations and transitions
- Clear visual hierarchy
- Professional color scheme

### 🔒 File Security
- Files are temporarily stored and can be cleaned up
- Secure filename handling
- Maximum file size: 50 MB (configurable)
- CORS protection enabled

### 📊 Progress Tracking
- Real-time progress updates
- Visual progress bar
- Status messages for each step
- Estimated time indicators

### ⚡ Performance
- Fast file validation
- Concurrent processing of lessons
- Optimized frontend with minimal JavaScript
- Responsive UI that feels instant

### 📱 Mobile-First
- Touch-friendly buttons
- Optimized spacing on small screens
- Readable fonts on all devices
- Simplified forms for mobile

---

## 🛠️ Customization

### Change Port Number
Edit the last line of `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change 5000 to 5001
```

### Modify Colors
Edit `static/style.css`:
```css
--primary-orange: #FF9500;    /* Main color */
--dark-orange: #E68A00;       /* Darker variant */
--light-orange: #FFB84D;      /* Lighter variant */
```

### Increase File Size Limit
Edit `app.py`:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB instead of 50 MB
```

### Custom Branding
Edit `templates/index.html`:
```html
<h1 class="logo">📚 Your App Name</h1>
```

---

## 🐛 Troubleshooting

### Issue: Port 5001 already in use
```bash
# Find what's using port 5001
lsof -i :5001

# Kill the process
kill -9 <PID>

# Or use a different port (see Customization above)
```

### Issue: "GROQ_API_KEY not found"
```bash
# Make sure .env file exists and has:
echo "GROQ_API_KEY=your_actual_key" > .env

# Verify it's set
echo $GROQ_API_KEY
```

### Issue: Tesseract not found
```bash
# macOS
brew install tesseract
brew install tesseract-lang  # Get Urdu language data

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-urd
```

### Issue: File upload fails
- Check file size (max 50 MB)
- Ensure file format (.docx and .pdf only)
- Try a different file
- Check browser console for errors (F12)

### Issue: Generation fails with error
- Check the `logs/` folder for detailed error logs
- Ensure your GROQ_API_KEY is valid
- Verify your PDF isn't corrupt
- Try with a smaller page range

---

## 📈 Architecture

```
Frontend (Browser)
    ↓ HTTP Requests
Flask App (app.py)
    ↓
PDF Extractor → OCR Repair → LLM Generation → Template Parser
    ↓ Returns Results
Browser Downloads File
```

---

## 🔄 Still Have CLI?

The original CLI is still available:
```bash
python main.py
```

Both web interface and CLI share the same backend modules, so they work interchangeably!

---

## 📚 File Layout

```
UrduPlanner/
├── 📄 app.py                    # Flask web server (NEW!)
├── 📄 main.py                   # Original CLI (still works)
├── 📄 config.py                 # Configuration
├── 📄 requirements.txt           # Dependencies (updated)
├── 📄 FRONTEND.md               # Quick start
├── 📄 README.md                 # Original docs
├── 📁 templates/
│   └── 📄 index.html            # Main page (NEW!)
├── 📁 static/
│   ├── 📄 style.css             # Styling with orange theme (NEW!)
│   └── 📄 script.js             # Frontend logic (NEW!)
├── 📁 skills/                   # Core processing modules
│   ├── content_generator/
│   ├── pdf_extractor/
│   ├── rtl_fixer/
│   └── template_engine/
└── 📁 logs/                      # Processing logs
```

---

## 🎓 Learning Resources

- Flask documentation: https://flask.palletsprojects.com/
- HTML/CSS/JS tutorials: https://developer.mozilla.org/
- Your own code: Start with `app.py` to understand the backend flow

---

## 📞 Support

Having issues? Here's what to check:

1. **Python installed?** → `python --version`
2. **Dependencies installed?** → `pip list | grep Flask`
3. **Environment set?** → `echo $GROQ_API_KEY`
4. **Tesseract installed?** → `tesseract --version`
5. **Port available?** → `lsof -i :5001`
6. **Check logs** → `logs/` folder

---

**Version**: 3.0 (Web Frontend)
**Last Updated**: April 5, 2026
**Theme**: Orange & White
**Status**: ✅ Ready to use!
