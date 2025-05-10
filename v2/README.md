# AI Image Generation Telegram Bot

## 📌 Overview
This Telegram bot provides advanced AI-powered image generation and manipulation using Stability AI's API. It supports text-to-image, upscaling (with creative, conservative, and fast modes), reimagining, and outpainting (uncropping), with robust feedback and error handling.

## ✨ Key Features

### 🎨 Image Generation
- Create AI-generated artwork from text prompts (`/imagine`)
- New generation model with aspect ratio and optional image input (`/imaginev2`)
- Control-based generation using reference images

### 🔄 Image Transformation
- Reimagine existing images with new concepts (`/reimagine`)
- Two methods: "Image" (structural transformation) and "Sketch" (style transfer)

### 📈 Image Enhancement
- Upscale images with three methods:
  - **Conservative**: Maintains original details, prompt-guided
  - **Creative**: Adds new details based on prompt and style, requires prompt, style, and image
  - **Fast**: Quick upscaling with minimal changes, requires only image

### 🖼️ Outpainting (Uncrop)
- Expand images beyond their original borders (`/uncrop`)
- Control the position of the original image in the expanded result
- 9 position options + automatic positioning

### ⚙️ Admin Features
- Watermark toggle for generated images (`/set_watermark`)
- Restricted access controls

## 🛠 Technical Architecture
```
├── main.py       # Bot initialization and conversation handlers
├── routes.py     # All bot commands and conversation logic
├── models.py     # Data classes and enums
├── helper.py     # Core image processing and API interactions
└── .env          # Configuration file
```

## 🔧 Setup Instructions

### Prerequisites
- Python 3.9+
- Telegram bot token
- Stability AI API key
- Python virtual environment (recommended)

### Installation
1. Clone the repository
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` file:
   ```ini
   TELEGRAM_BOT_TOKEN=your_bot_token
   STABILITY_API_KEY=your_stability_key
   USER_ID=comma_separated_user_ids
   ADMIN_ID=comma_separated_admin_ids
   WATERMARK_ENABLED=true
   ```

### Running the Bot
```bash
python main.py
```

## 🤖 Command Reference

### Basic Commands
| Command         | Description                                      |
|----------------|--------------------------------------------------|
| `/start`       | Welcome message and bot introduction              |
| `/help`        | Detailed command reference and tips               |
| `/set_watermark` | Toggle watermarking (Admins only)               |
| `/cancel`      | Cancel the current operation                      |

### Image Generation
**/imagine**
- Flow: Prompt → Generation type (Regular/Control-Based) → (Optional: Reference image) → Size → Style → Processing
- After style selection, the bot shows "🎨 Generating your image…" and delivers the result asynchronously.
- Usage: `/imagine`

**/imaginev2**
- Flow: Prompt → Aspect ratio → (Optional: Image upload) → Processing
- Usage: `/imaginev2`

### Image Upscaling
**/upscale**
- Flow:
  1. Select upscaling method (Conservative, Creative, Fast)
  2. If Conservative/Creative: Enter a prompt
  3. If Creative: Select a style preset
  4. Upload the image to upscale
  5. Select output format (webp, jpeg, png)
  6. Processing and result delivery
- Usage: `/upscale`

### Image Reimagining
**/reimagine**
- Flow: Select method (Image/Sketch) → Upload image → Select style → Enter prompt → Processing
- Usage: `/reimagine`

### Outpainting (Uncrop)
**/uncrop**
- Flow: Upload image → Select aspect ratio → Select position → (Optional: Prompt) → Processing
- Usage: `/uncrop`

## ⚙️ Configuration Options

### Environment Variables
| Variable             | Description                        | Default |
|----------------------|------------------------------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token            | -       |
| `STABILITY_API_KEY`  | Stability AI API key               | -       |
| `USER_ID`            | Comma-separated allowed user IDs    | -       |
| `ADMIN_ID`           | Comma-separated admin user IDs      | -       |
| `WATERMARK_ENABLED`  | Enable/disable watermark           | `true`  |

### Image Configuration
- **Size Presets**: Defined in `ImageConfig` class
- **Style Presets**: Multiple artistic styles available
- **Aspect Ratios**: Various common ratios supported

## 🚀 Advanced Features

### Position Control in Outpainting
- 9 fixed positions: Corners, edges, and center
- Auto positioning: Automatically centers the image based on aspect ratio

### Watermark System
- Toggleable via `/set_watermark` (admin only)
- Applies semi-transparent watermark at bottom-left

## 📊 Error Handling & Feedback
- Comprehensive error logging
- User-friendly error messages for all failures
- Automatic timeout handling (3 minutes inactivity)
- Conversation state tracking
- **Faster feedback:**
  - Bot sends "typing…" or "processing…" actions during long operations
  - Progress updates if an operation takes longer than 10 seconds
- **Retry logic:**
  - All network/API requests are retried up to 3 times with exponential backoff for transient errors

## 📦 File Structure Details
- `main.py`: Bot initialization, conversation handler setup, timeout management, logging
- `routes.py`: All Telegram command handlers, conversation state management, user interaction flows
- `models.py`: Enum for conversation steps, image config, parameter dataclasses
- `helper.py`: User authentication, image processing (generation, upscaling, reimagine, outpainting, watermark)

## 🌟 Tips for Best Results
1. **For generation**: Use detailed, specific prompts
2. **For upscaling**:
   - Use "creative" mode for adding new details (prompt, style, and image required)
   - "conservative" for faithful enlargement (prompt and image required)
   - "fast" for quick upscaling (image only)
3. **For outpainting**:
   - Use position control to guide expansion
   - Provide prompts for better context awareness
4. **For reimagining**:
   - "Image" method works best for complete transformations
   - "Sketch" method preserves more original structure

## 📬 Support
For issues or feature requests, please open an issue in the repository.
