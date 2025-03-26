# AI Image Generation Bot - Documentation

## 📌 Overview

This Telegram bot provides advanced AI-powered image generation and manipulation capabilities using Stability AI's API. It offers multiple features including text-to-image generation, image upscaling, reimagining existing images, and outpainting (uncropping).

## ✨ Key Features

### 🎨 Image Generation
- Create AI-generated artwork from text prompts (`/imagine`)
- New generation model with more control (`/imaginev2`)
- Control-based generation using reference images

### 🔄 Image Transformation
- Reimagine existing images with new concepts (`/reimagine`)
- Two methods: "Image" (structural transformation) and "Sketch" (style transfer)

### 📈 Image Enhancement
- Upscale images with three methods:
  - **Conservative**: Maintains original details
  - **Creative**: Adds new details based on prompt
  - **Fast**: Quick upscaling with minimal changes

### 🖼️ Outpainting (Uncrop)
- Expand images beyond their original borders (`/uncrop`)
- Control the position of original image in the expanded result
- 9 position options + automatic positioning

### ⚙️ Admin Features
- Watermark toggle for generated images (`/set_watermark`)
- Restricted access controls

## 🛠 Technical Architecture

```
├── main.py              # Bot initialization and conversation handlers
├── routes.py            # All bot commands and conversation logic
├── models.py            # Data classes and enums
├── helper.py            # Core image processing and API interactions
└── .env                 # Configuration file
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
   source venv/bin/activate  # Linux/Mac)
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
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot introduction |
| `/help` | Detailed command reference and tips |

### Image Generation
| Command | Flow |
|---------|------|
| `/imagine` | Prompt → Generation Type → (Image if control-based) → Size → Style → Generate |
| `/imaginev2` | Prompt → Aspect Ratio → (Optional Image) → Generate |

### Image Transformation
| Command | Flow |
|---------|------|
| `/reimagine` | Method (Image/Sketch) → Upload Image → Style → Prompt → Transform |
| `/upscale` | Method → (Prompt if creative/conservative) → Upload Image → Format → Upscale |

### Outpainting (Uncrop)
| Command | Flow |
|---------|------|
| `/uncrop` | Upload Image → Aspect Ratio → Position → (Optional Prompt) → Outpaint |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/set_watermark` | Toggle watermark on/off (Admin only) |

## 🔄 Workflow Details

### Image Generation Flow (`/imagine`)
1. User provides text prompt
2. Chooses between regular or control-based generation
3. For control-based: uploads reference image
4. Selects image size from presets
5. Chooses style preset
6. Receives generated image

### Uncrop/Outpaint Flow (`/uncrop`)
1. User uploads image to expand
2. Selects target aspect ratio
3. Chooses position of original image in expanded result:
   - 9 position options (top-left, top, top-right, etc.)
   - "Auto/Original" for automatic centering
   - Can skip to use auto positioning
4. (Optional) Provides guidance prompt
5. Receives outpainted image

## ⚙️ Configuration Options

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | - |
| `STABILITY_API_KEY` | Stability AI API key | - |
| `USER_ID` | Comma-separated allowed user IDs | - |
| `ADMIN_ID` | Comma-separated admin user IDs | - |
| `WATERMARK_ENABLED` | Enable/disable watermark | `true` |

### Image Configuration
- **Size Presets**: Defined in `ImageConfig` class
- **Style Presets**: Multiple artistic styles available
- **Aspect Ratios**: Various common ratios supported

## 🚀 Advanced Features

### Position Control in Outpainting
When using `/uncrop`, you can precisely control where the original image appears in the expanded result:
- **9 fixed positions**: Corners, edges, and center
- **Auto positioning**: Automatically centers the image based on aspect ratio
- **Visualization**:
  ```
  Top Left    | Top    | Top Right
  -------------------------------
  Left        | Middle | Right
  -------------------------------
  Bottom Left | Bottom | Bottom Right
  ```

### Watermark System
- Toggleable via `/set_watermark` (admin only)
- Applies semi-transparent watermark at bottom-left
- Configurable via `WATERMARK_ENABLED` in `.env`

## 📊 Error Handling
- Comprehensive error logging
- User-friendly error messages
- Automatic timeout handling (3 minutes inactivity)
- Conversation state tracking

## 📦 File Structure Details

### `main.py`
- Bot initialization
- Conversation handler setup
- Timeout management
- Logging configuration

### `routes.py`
- All Telegram command handlers
- Conversation state management
- User interaction flows

### `models.py`
- `ConversationState`: Enum for tracking conversation steps
- `ImageConfig`: Size and style presets
- Parameter dataclasses for each operation type

### `helper.py`
- `AuthHelper`: User authentication
- `ImageHelper`: Core image processing using Stability AI API
  - Image generation
  - Upscaling
  - Reimagining
  - Outpainting
  - Watermark handling

## 📈 Performance Considerations
- Automatic image resizing for API limits
- Async file downloads
- Progress indicators for long operations
- Cached configurations

## 🌟 Tips for Best Results
1. **For generation**: Use detailed, specific prompts
2. **For upscaling**:
   - Use "creative" mode for adding new details
   - "conservative" for faithful enlargement
3. **For outpainting**:
   - Use position control to guide expansion
   - Provide prompts for better context awareness
4. **For reimagining**:
   - "Image" method works best for complete transformations
   - "Sketch" method preserves more original structure

## 📬 Support
For issues or feature requests, please open an issue in the repository.
