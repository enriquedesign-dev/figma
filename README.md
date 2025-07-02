# Figma Text API Backend

A lightweight FastAPI backend that integrates with the Figma API to serve JSON files containing text content for mobile applications. The system fetches text nodes from Figma design files and organizes them by Pages → Screens → Texts with positional information.

## Features

- **FastAPI Backend**: High-performance async API server
- **Figma Integration**: Fetches design data directly from Figma API
- **SQLite Database**: Lightweight database for storing JSON text data
- **Automated Sync**: Background synchronization with Figma files
- **RESTful API**: Clean endpoints for mobile app consumption
- **Text Organization**: Structured data as Page → Screen → Text hierarchy
- **Reading Order**: Texts automatically sorted by `axis_y` (top to bottom) for logical flow

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Figma API     │───▶│  Sync Service │───▶│  Database   │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │
                              ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│  Mobile App     │◀───│  FastAPI     │◀───│ JSON Files  │
└─────────────────┘    └──────────────┘    └─────────────┘
```

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Edit .env with your Figma credentials
   FIGMA_ACCESS_TOKEN=your_figma_token
   FIGMA_FILE_KEY=your_figma_file_key
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

## API Endpoints

### Health Check
```
GET /health
```
Returns API health status and configuration check.

### Sync Figma Data
```
POST /api/sync
```
Synchronizes text data from the default Figma file to database.

### Get Complete File Data
```
GET /api/figma/data
```
Returns complete organized text data for the default Figma file.

### Get Pages List
```
GET /api/figma/pages
```
Returns list of pages in the default Figma file.

### Get Page Data
```
GET /api/figma/pages/{page_name}
```
Returns all screens and texts for a specific page from the default Figma file.

### Get Screen Data
```
GET /api/figma/pages/{page_name}/screens/{screen_name}
```
Returns all texts for a specific screen from the default Figma file.

### Get Default File Texts
```
GET /api/figma/texts
```
Returns all texts from the default Figma file (uses `FIGMA_FILE_KEY` from environment variables). This endpoint flattens all texts across all pages and screens for easy consumption by mobile applications.

**Response format:**
```json
{
  "total_texts": 5,
  "pages": {
    "Onboarding": {
      "1-informacion-salarial-default": {
        "01_Title": {
          "text_content": "Información salarial",
          "axis_x": 527.0,
          "axis_y": 84.0,
          "page_id": "0:1",
          "screen_id": "16:425"
        },
        "02_Subtitle": {
          "text_content": "Esto nos permitirá ofrecer mejores beneficios para ti",
          "axis_x": 527.0,
          "axis_y": 129.0,
          "page_id": "0:1",
          "screen_id": "16:425"
        },
        "03_Field label": {
          "text_content": "Tipo de ingreso",
          "axis_x": 519.0,
          "axis_y": 341.0,
          "page_id": "0:1",
          "screen_id": "16:425"
        }
      }
    }
  },
  "last_updated": "2024-01-01T12:00:00"
}
```

## JSON Data Structure

The API returns text data organized in the following structure:

```json
{
  "pages": {
    "Page Name": {
      "page_id": "figma_page_id",
      "screens": {
        "Screen Name": {
          "screen_id": "figma_screen_id",
          "texts": [
            {
              "name": "Text Layer Name",
              "content": "Actual text content",
              "axis_x": 100.0,
              "axis_y": 200.0
            }
          ]
        }
      }
    }
  },
  "last_updated": "2024-01-01T12:00:00",
  "figma_file_key": "file_key"
}
```

## Synchronization

### Manual Sync
Run the standalone sync script:
```bash
python sync_script.py
```

### Automated Sync
Set up a cron job for regular synchronization:
```bash
# Edit crontab
crontab -e

# Add line for hourly sync
0 * * * * cd /path/to/project && python sync_script.py
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FIGMA_ACCESS_TOKEN` | Figma API access token | Yes |
| `FIGMA_FILE_KEY` | Default Figma file key | Yes |
| `DATABASE_URL` | SQLite database path | No |
| `HOST` | API server host | No |
| `PORT` | API server port | No |

### Figma Setup

1. **Get Access Token:**
   - Go to Figma → Settings → Account → Personal Access Tokens
   - Generate new token with appropriate permissions

2. **Get File Key:**
   - Copy from Figma file URL: `https://www.figma.com/file/{FILE_KEY}/...`

## Usage Examples

### Mobile App Integration

```javascript
// Option 1: Get all texts from default file (easiest)
const response = await fetch('/api/figma/texts');
const data = await response.json();

console.log(`Found ${data.total_texts} texts`);

// Navigate the nested structure (texts are ordered by axis_y - top to bottom)
Object.entries(data.pages).forEach(([pageName, screens]) => {
  Object.entries(screens).forEach(([screenName, texts]) => {
    console.log(`\n📱 ${screenName} reading order:`);
    // Sort by numbered keys to maintain reading order
    Object.entries(texts)
      .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
      .forEach(([textKey, textData], index) => {
        console.log(`${index + 1}. ${textKey}: "${textData.text_content}" (y=${textData.axis_y})`);
      });
  });
});

// Or access specific text directly using numbered keys
const title = data.pages['Onboarding']['1-informacion-salarial-default']['01_Title'];
console.log(title.text_content); // "Información salarial"

// Note: If there are duplicate text names within the same screen, 
// they are automatically numbered (e.g., "Field label", "Field label_1", "Field label_2")
const secondFieldLabel = data.pages['Onboarding']['1-informacion-salarial-default']['03_Field label_1'];
console.log(secondFieldLabel.text_content); // "Ingreso fijo mensual"

// Option 2: Get data for a specific page
const pageResponse = await fetch('/api/figma/pages/HomePage');
const pageData = await pageResponse.json();

// Access screen texts
const loginScreenTexts = pageData.page.screens['Login Screen'].texts;
loginScreenTexts.forEach(text => {
  console.log(`${text.name}: ${text.content}`);
});
```

### Sync Before App Build

```bash
# In your CI/CD pipeline
python sync_script.py  # Uses FIGMA_FILE_KEY from environment
python main.py &
# Run your tests/build process

# Or via API
curl -X POST http://localhost:8000/api/sync
```

## Development

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FIGMA_ACCESS_TOKEN="your_token"
export FIGMA_FILE_KEY="your_file_key"

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Database Schema

The system uses two main tables:

- **figma_pages**: Stores complete page JSON data
- **figma_texts**: Stores individual text entries for fast querying

## Deployment

### Production Setup

1. **Use environment variables for configuration**
2. **Set up reverse proxy (nginx)**
3. **Configure automated sync via cron**
4. **Monitor API health endpoint**

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

## Performance

- **Lightweight**: SQLite database, minimal dependencies
- **Fast**: Async FastAPI with efficient queries
- **Small**: ~50MB total footprint including dependencies
- **Scalable**: Stateless API design for horizontal scaling

## Troubleshooting

### Common Issues

1. **"Import could not be resolved"**: Install dependencies with `pip install -r requirements.txt`
2. **"No data found"**: Run sync first with `POST /api/sync` or `python sync_script.py`
3. **"Figma API error"**: Check access token and file permissions in .env file
4. **"Database error"**: Ensure write permissions for SQLite file
5. **"FIGMA_FILE_KEY not set"**: Ensure your .env file has the correct Figma file key

### Logs

Check application logs for detailed error information:
```bash
python main.py 2>&1 | tee app.log
```

## Background / Daemon Mode (nohup)

If you need the API to keep running after you close your SSH session or terminal window, start it in **daemon mode** using the helper script `start_api_nohup.sh`:

```bash
# One-time: make the script executable
chmod +x start_api_nohup.sh

# Launch the backend in the background
./start_api_nohup.sh start

# Verify that it is running
./start_api_nohup.sh status

# Follow the live output
tail -f figma_api.out

# Gracefully stop the background server (optional)
./start_api_nohup.sh stop
```

The script wraps `run_server.sh` with `nohup`, redirects all output to `figma_api.out`, and stores the process ID in `figma_api.pid` so that subsequent `status`, `stop`, or `restart` commands work reliably.