# Telegram AI Image Generation Bot

A comprehensive Telegram bot that provides advanced AI-powered image generation capabilities using Stability AI's state-of-the-art image generation models. The bot supports multiple image manipulation techniques including text-to-image generation, image reimagining, upscaling, and outpainting operations.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Commands](#commands)
- [Project Structure](#project-structure)
- [API Integration](#api-integration)
- [Security and Access Control](#security-and-access-control)
- [Error Handling and Logging](#error-handling-and-logging)
- [Development](#development)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Overview

This Telegram bot serves as an interface between users and Stability AI's image generation services, enabling users to create, modify, and enhance images through natural language commands and interactive conversations. The bot implements a sophisticated state management system to handle complex multi-step workflows while maintaining user context and providing real-time feedback.

The application is built using Python and leverages the `python-telegram-bot` framework for Telegram integration, with comprehensive image processing capabilities powered by the Pillow library.

## Features

### Core Image Generation
- **Text-to-Image Generation**: Create images from detailed text descriptions
- **Style Presets**: Access to curated artistic styles including photographic, digital art, anime, and more
- **Size Options**: Multiple aspect ratios from square to panoramic formats
- **Advanced Prompting**: Support for complex, multi-concept prompts

### Image Manipulation
- **Image Reimagining**: Transform existing images with new concepts and styles
- **Intelligent Upscaling**: Enhance image resolution while preserving quality
- **Outpainting/Uncropping**: Expand images beyond their original boundaries
- **Control-Based Generation**: Use reference images for guided generation
- **Object Erasing**: Remove unwanted objects from images using masks
- **Search and Replace**: Find and replace objects or elements in images
- **Inpainting**: Fill masked areas with AI-generated content

### Enhanced User Experience
- **Interactive Conversations**: Step-by-step guided workflows with inline keyboards
- **Real-time Progress Updates**: Chat action indicators during processing
- **Timeout Management**: Automatic session cleanup and inactivity handling
- **Error Recovery**: Robust error handling with user-friendly messages
- **Global Language Support**: Automatic translation of prompts to English for international users

### Administrative Features
- **Access Control**: Configurable user and admin permissions
- **Watermark Management**: Optional watermarking for generated images
- **Usage Monitoring**: Comprehensive logging and monitoring capabilities

## Architecture

### Core Components

#### TelegramBot Class (`main.py`)
The main application class responsible for:
- Bot initialization and configuration
- Handler registration and routing
- Conversation state management
- Background job scheduling for timeouts
- Logging setup and application lifecycle

#### TelegramRoutes Class (`routes.py`)
Handles all Telegram command processing and user interactions:
- Command routing and validation
- Conversation flow management
- Message parsing and response formatting
- Error handling and user feedback

#### ImageHelper Class (`helper.py`)
Manages all image processing operations:
- Stability AI API integration
- Image generation and manipulation
- File I/O and format conversion
- Watermark application
- Retry logic for API calls

#### AuthHelper Class (`helper.py`)
Provides authentication and authorization services:
- User access validation
- Administrative permission checking
- Environment-based configuration

#### Data Models (`models.py`)
Defines structured data representations:
- Conversation states and transitions
- Image configuration parameters
- Generation request specifications
- API response handling

### State Management
The bot implements a finite state machine with the following conversation states:
- `WAITING_FOR_PROMPT`: Collecting image generation prompts
- `WAITING_FOR_SIZE`: Size/aspect ratio selection
- `WAITING_FOR_STYLE`: Artistic style selection
- `WAITING_FOR_IMAGE`: Reference image collection
- `WAITING_FOR_CONTROL_TYPE`: Control method selection
- `WAITING_FOR_UPSCALE_METHOD`: Upscaling technique selection
- `WAITING_FOR_FORMAT`: Output format selection
- `WAITING_FOR_METHOD`: Processing method selection

## Prerequisites

### System Requirements
- **Python**: Version 3.11 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 500MB free space for generated images and logs

### External Dependencies
- **Stability AI API**: Valid API key with sufficient credits
- **Telegram Bot API**: Bot token from BotFather
- **Internet Connection**: Stable connection for API calls

### Python Libraries
- `python-telegram-bot==21.7`: Telegram bot framework
- `requests==2.32.3`: HTTP client for API calls
- `python-dotenv==1.0.1`: Environment variable management
- `Pillow==11.0.0`: Image processing library
- `colorlog`: Enhanced logging with colors
- `Flask==3.1.0`: Web framework (for future API extensions)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd telegram-image-generation-bot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python -c "import telegram; import PIL; print('Dependencies installed successfully')"
```

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

```env
# Required: Stability AI API Configuration
STABILITY_API_KEY=your_stability_api_key_here
API_HOST=https://api.stability.ai

# Required: Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Access Control (comma-separated user IDs, use '*' for unrestricted access)
USER_ID=user_id_1,user_id_2,user_id_3
ADMIN_ID=admin_user_id_1,admin_user_id_2

# Optional: Watermark Configuration
WATERMARK_ENABLED=true

# Optional: Output Directory
OUTPUT_DIRECTORY=./image
```

### API Keys Setup

#### Stability AI API Key
1. Visit [Stability AI Platform](https://platform.stability.ai/)
2. Create an account and obtain your API key
3. Add the key to your `.env` file

#### Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command to create a new bot
3. Copy the provided token to your `.env` file

### User Access Control
- Set `USER_ID="*"` to allow all users
- Specify comma-separated Telegram user IDs for restricted access
- Admin users have additional privileges for configuration management

## Usage

### Starting the Bot
```bash
cd code/
python main.py
```

The bot will initialize logging, connect to Telegram, and begin polling for messages.

### Basic Workflow
1. **Start**: User sends `/start` command
2. **Authentication**: Bot validates user permissions
3. **Command Selection**: User chooses desired operation
4. **Parameter Collection**: Bot guides user through required inputs
5. **Processing**: Bot communicates with Stability AI API
6. **Delivery**: Generated/modified image sent to user

## Commands

### User Commands

#### `/start`
- Initializes bot interaction
- Displays welcome message and available commands
- Verifies user authorization

#### `/help`
- Shows comprehensive command reference
- Lists available features and usage instructions

#### `/imagine`
- Initiates text-to-image generation workflow
- Guides through prompt, size, and style selection
- Supports advanced prompting techniques

#### `/imaginev2`
- Uses next-generation image generation model
- Enhanced prompt understanding and image quality
- Supports aspect ratio selection

#### `/reimagine`
- Transforms existing images with new concepts
- Accepts image uploads and modification prompts
- Maintains original composition while applying changes

#### `/upscale`
- Enhances image resolution and quality
- Multiple upscaling algorithms available
- Preserves image details and reduces artifacts

#### `/uncrop`
- Expands images beyond original boundaries
- Intelligent content generation for extensions
- Customizable aspect ratio changes

#### `/erase`
- Removes objects from images using mask images
- Requires original image and black/white mask
- White areas in mask indicate objects to erase

#### `/search_replace`
- Finds and replaces objects or elements in images
- Uses text descriptions for search and replacement
- Maintains image composition while swapping elements

#### `/inpaint`
- Fills masked areas with AI-generated content
- Requires original image, mask, and generation prompt
- White areas in mask indicate regions to fill

### Administrative Commands

#### `/set_watermark`
- Toggle watermark application on generated images
- Requires admin privileges
- Persists setting across bot restarts

#### `/cancel`
- Terminates active conversation
- Clears user session data
- Returns to command selection state

## Project Structure

```
telegram-image-generation-bot/
├── code/
│   ├── main.py                 # Main application entry point
│   ├── routes.py               # Telegram command handlers and routing
│   ├── helper.py               # Image processing and API integration utilities
│   ├── models.py               # Data models and configuration classes
│   ├── list_enggine.py         # Stability AI engine enumeration utility
│   ├── logo.png                # Bot logo/watermark image
│   └── README.md               # Module-specific documentation
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation (this file)
```

### File Descriptions

#### `main.py`
- **Purpose**: Application entry point and main orchestration
- **Key Classes**: `TelegramBot` - Main application controller
- **Responsibilities**:
  - Bot initialization and configuration
  - Handler registration and conversation management
  - Background job scheduling
  - Logging configuration

#### `routes.py`
- **Purpose**: Telegram interaction handling
- **Key Classes**: `TelegramRoutes` - Command processing and routing
- **Responsibilities**:
  - Command validation and routing
  - Conversation state management
  - User input processing and validation
  - Response formatting and delivery

#### `helper.py`
- **Purpose**: Core business logic and external integrations
- **Key Classes**:
  - `ImageHelper` - Image processing and API communication
  - `AuthHelper` - User authentication and authorization
- **Responsibilities**:
  - Stability AI API integration
  - Image manipulation and processing
  - Authentication logic
  - File I/O operations

#### `models.py`
- **Purpose**: Data structure definitions
- **Key Classes**:
  - `ConversationState` - State machine enumeration
  - `ImageConfig` - Image generation parameters
  - `GenerationParams` - Request specifications
- **Responsibilities**:
  - Type definitions for API interactions
  - Configuration data structures
  - Parameter validation schemas

## API Integration

### Stability AI API
The bot integrates with Stability AI's REST API endpoints:

#### Core Endpoints Used
- **Text-to-Image**: `POST /v1/generation/{engine}/text-to-image`
- **Image-to-Image**: `POST /v1/generation/{engine}/image-to-image`
- **Upscaling**: `POST /v1/generation/{engine}/upscale`
- **Outpainting**: `POST /v1/generation/{engine}/outpaint`
- **Object Erase**: `POST /v2beta/stable-image/edit/erase`
- **Search & Replace**: `POST /v2beta/stable-image/edit/search-and-replace`
- **Inpainting**: `POST /v2beta/stable-image/edit/inpaint`

#### Request Parameters
- **Engine Selection**: Dynamic engine selection based on operation type
- **Prompt Engineering**: Advanced prompt processing and enhancement
- **Image Parameters**: Resolution, aspect ratio, and quality settings
- **Style Presets**: Curated artistic style configurations

#### Response Handling
- **Binary Image Data**: Direct image stream processing
- **Metadata Extraction**: Generation parameters and timestamps
- **Error Code Management**: Comprehensive error handling for API failures

### Telegram Bot API
Integration with Telegram's Bot API for user interaction:

#### Key Features Used
- **Message Handling**: Text, photo, and callback query processing
- **Inline Keyboards**: Interactive button interfaces for selections
- **Chat Actions**: User feedback during processing
- **File Upload/Download**: Image transmission and storage

## Security and Access Control

### Authentication Mechanisms
- **User ID Validation**: Telegram user ID verification against allowlists
- **Admin Privileges**: Elevated permissions for configuration management
- **Session Management**: Automatic session cleanup and timeout handling

### Data Protection
- **Environment Variables**: Sensitive configuration stored securely
- **File Permissions**: Restricted access to generated content
- **Input Validation**: Comprehensive user input sanitization
- **Rate Limiting**: Built-in protection against API abuse

### Privacy Considerations
- **Data Minimization**: Only necessary user data stored temporarily
- **Session Cleanup**: Automatic removal of conversation data
- **No Personal Data Persistence**: User interactions not logged permanently

## Error Handling and Logging

### Logging Configuration
- **Structured Logging**: Consistent log format across all components
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Colored Output**: Enhanced console readability with colorlog
- **Third-party Suppression**: Reduced noise from external libraries

### Error Recovery
- **Graceful Degradation**: Continued operation despite individual failures
- **User Feedback**: Clear error messages with recovery instructions
- **Automatic Retry**: Network failure recovery with exponential backoff
- **Conversation Reset**: Session cleanup on critical errors

### Monitoring
- **Performance Tracking**: API call timing and success rates
- **Usage Statistics**: Command usage and user activity metrics
- **Health Checks**: System status monitoring and alerts

## Development

### Code Organization
- **Modular Design**: Separated concerns across multiple files
- **Type Hints**: Comprehensive Python type annotations
- **Documentation**: Inline docstrings and code comments
- **Error Handling**: Consistent exception management patterns

### Testing
```bash
# Run basic functionality tests
python -m pytest tests/

# Test API connectivity
python code/list_enggine.py
```

### Code Quality
- **PEP 8 Compliance**: Standard Python formatting
- **Linting**: Regular code quality checks
- **Version Control**: Git-based development workflow
- **Documentation**: Comprehensive README and inline documentation

## Deployment

### Production Setup
1. **Server Provisioning**: Dedicated server with Python 3.11+
2. **Environment Configuration**: Production `.env` file setup
3. **Process Management**: Systemd or Docker containerization
4. **Monitoring**: Log aggregation and alerting setup

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "code/main.py"]
```

### Systemd Service
```ini
[Unit]
Description=Telegram Image Generation Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
ExecStart=/path/to/venv/bin/python code/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues

#### Bot Not Responding
- Verify Telegram bot token validity
- Check internet connectivity
- Review bot logs for error messages

#### API Errors
- Confirm Stability AI API key validity
- Check API credit balance
- Verify API endpoint availability

#### Permission Issues
- Validate user ID configuration
- Check file system permissions
- Review environment variable loading

#### Image Generation Failures
- Verify image format compatibility
- Check file size limits
- Review prompt content guidelines

### Debug Mode
Enable detailed logging by setting log level to DEBUG in the configuration.

### Log Analysis
- Review application logs for error patterns
- Monitor API response times and success rates
- Track user interaction flows

## Contributing

### Development Guidelines
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards
- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Add type hints for all function parameters
- Write unit tests for new features

### Testing Requirements
- Maintain test coverage above 80%
- Include integration tests for API interactions
- Test error conditions and edge cases

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

### Documentation
- Comprehensive in-code documentation
- API reference in docstrings
- Usage examples and tutorials

### Community Support
- GitHub Issues for bug reports
- Pull Request discussions for feature requests
- Community forum for general questions

### Professional Support
- Enterprise deployment assistance
- Custom feature development
- Performance optimization consulting

---

For additional information or support, please refer to the project documentation or create an issue on the GitHub repository.

---
