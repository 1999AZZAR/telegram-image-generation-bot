# Telegram AI Image Generation Bot - Module Documentation

## Overview

This module implements a comprehensive Telegram bot for AI-powered image generation and manipulation using Stability AI's image generation services. The bot provides a conversational interface for multiple image processing operations including text-to-image generation, image upscaling, reimagining, and outpainting.

The implementation follows a modular architecture with clear separation of concerns across multiple Python modules, enabling maintainable and extensible code organization.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Components](#core-components)
- [API Integration](#api-integration)
- [Configuration](#configuration)
- [Command Implementation](#command-implementation)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Usage Guidelines](#usage-guidelines)
- [Development Notes](#development-notes)

## Architecture

The bot is organized into four main modules with distinct responsibilities:

```
code/
├── main.py          # Application entry point and orchestration
├── routes.py        # Telegram command handlers and conversation flows
├── models.py        # Data structures and configuration classes
├── helper.py        # Business logic and external API integrations
├── list_enggine.py  # Stability AI engine enumeration utility
├── logo.png         # Watermark image asset
└── README.md        # This documentation
```

### Design Principles

- **Separation of Concerns**: Each module has a specific responsibility
- **State Management**: Conversation states managed through finite state machine
- **Error Resilience**: Comprehensive error handling with user-friendly feedback
- **Modular Configuration**: Environment-based configuration for different deployment scenarios

## Core Components

### Main Application (`main.py`)

The main application module serves as the entry point and orchestrates the bot's lifecycle:

#### Key Responsibilities
- Bot initialization and configuration setup
- Conversation handler registration for all supported workflows
- Background job scheduling for session timeout management
- Logging configuration and application monitoring
- Telegram API connection management

#### Conversation Handlers
The application implements multiple conversation handlers for different workflows:

- **Image Generation Handler**: Manages `/imagine` command workflow
- **Image V2 Handler**: Handles `/imaginev2` command with aspect ratio selection
- **Upscaling Handler**: Processes `/upscale` command with method selection
- **Reimagine Handler**: Manages `/reimagine` command workflows
- **Uncrop Handler**: Handles `/uncrop` command for outpainting operations

#### Timeout Management
Implements dual timeout mechanisms:
- **Loop Timeout** (60 seconds): Prevents individual steps from hanging
- **Stall Timeout** (180 seconds): Clears inactive conversations

### Route Handlers (`routes.py`)

This module contains all Telegram command implementations and manages user interaction flows:

#### Command Categories

**Basic Commands**
- `/start`: Initialization and welcome message
- `/help`: Comprehensive command reference
- `/cancel`: Conversation termination

**Administrative Commands**
- `/set_watermark`: Watermark toggle (admin-only)

**Image Processing Commands**
- `/imagine`: Text-to-image generation with style selection
- `/imaginev2`: Enhanced generation with aspect ratio control
- `/upscale`: Image resolution enhancement
- `/reimagine`: Image transformation with new concepts
- `/uncrop`: Image expansion beyond borders

#### Conversation Flow Management

Each command implements a structured conversation flow:

1. **Command Initiation**: Validate user permissions and initialize context
2. **Parameter Collection**: Guide user through required input collection
3. **Validation**: Ensure input meets requirements
4. **Processing**: Execute image operation with progress feedback
5. **Delivery**: Return results or handle errors

### Helper Services (`helper.py`)

Contains core business logic and external service integrations:

#### Authentication Service (`AuthHelper`)
- User access validation against configured allowlists
- Administrative permission checking
- Session-based access control

#### Image Processing Service (`ImageHelper`)
- Stability AI API communication and request formatting
- Image manipulation and format conversion
- Watermark application and management
- File I/O operations for image storage
- Retry logic for network resilience

### Data Models (`models.py`)

Defines structured data representations and configuration:

#### Conversation States
Enumeration of all possible conversation states:
- `WAITING_FOR_PROMPT`: Collecting text descriptions
- `WAITING_FOR_SIZE`: Size/aspect ratio selection
- `WAITING_FOR_STYLE`: Artistic style selection
- `WAITING_FOR_IMAGE`: Reference image collection
- `WAITING_FOR_METHOD`: Processing method selection

#### Configuration Classes
- `ImageConfig`: Image parameters and presets
- `GenerationParams`: Text-to-image request specifications
- `ReimagineParams`: Image transformation parameters
- `UnCropParams`: Outpainting operation specifications

## API Integration

### Stability AI API Endpoints

The bot integrates with multiple Stability AI API endpoints:

#### Text-to-Image Generation
```http
POST /v1/generation/{engine}/text-to-image
```
Parameters: prompt, style_preset, dimensions, output_format

#### Image-to-Image Transformation
```http
POST /v1/generation/{engine}/image-to-image
```
Parameters: image, prompt, strength, style_preset

#### Image Upscaling
```http
POST /v1/generation/{engine}/upscale
```
Parameters: image, prompt, creativity, style_preset

#### Outpainting
```http
POST /v1/generation/{engine}/outpaint
```
Parameters: image, prompt, position, aspect_ratio

### Telegram Bot API

Integration with Telegram's Bot API for user interaction:

#### Message Types Handled
- Text messages for prompts and commands
- Photo uploads for reference images
- Callback queries for interactive selections
- Inline keyboard responses

#### Chat Actions
- `typing`: Indicates bot is processing user input
- `upload_photo`: Signals image upload in progress

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot authentication token | Yes | - |
| `STABILITY_API_KEY` | Stability AI API key | Yes | - |
| `USER_ID` | Comma-separated allowed user IDs | Yes | - |
| `ADMIN_ID` | Comma-separated admin user IDs | Yes | - |
| `WATERMARK_ENABLED` | Enable watermark on generated images | No | `true` |
| `OUTPUT_DIRECTORY` | Directory for generated images | No | `./image` |
| `API_HOST` | Stability AI API base URL | No | `https://api.stability.ai` |

### Image Configuration

#### Size Presets
Predefined aspect ratios for different use cases:
- `landscape`: 832×1216 (horizontal)
- `portrait`: 1216×832 (vertical)
- `square`: 1024×1024 (equal dimensions)
- `panorama`: 640×1536 (ultra-wide)

#### Style Presets
Curated artistic styles organized in categories:
- **Photographic**: `photographic`, `analog-film`, `cinematic`
- **Digital Art**: `digital-art`, `3d-model`, `pixel-art`
- **Illustrative**: `comic-book`, `line-art`, `modeling-compound`

## Command Implementation

### Image Generation Workflow (`/imagine`)

1. **Prompt Collection**: User provides text description
2. **Control Type Selection**: Choose between regular or control-based generation
3. **Reference Image** (optional): Upload image for control-based generation
4. **Size Selection**: Choose from predefined aspect ratios
5. **Style Selection**: Select artistic style preset
6. **Processing**: Generate image using Stability AI API
7. **Delivery**: Return generated image to user

### Enhanced Generation Workflow (`/imaginev2`)

1. **Prompt Collection**: User provides text description
2. **Aspect Ratio Selection**: Choose target dimensions
3. **Reference Image** (optional): Upload for image-to-image generation
4. **Processing**: Generate using enhanced model
5. **Delivery**: Return result

### Upscaling Workflow (`/upscale`)

1. **Method Selection**: Choose upscaling approach
   - **Conservative**: Faithful enlargement with prompt guidance
   - **Creative**: Add new details with style application
   - **Fast**: Quick resolution enhancement
2. **Prompt Input** (Conservative/Creative): Enhancement guidance
3. **Style Selection** (Creative): Artistic style application
4. **Image Upload**: Source image for upscaling
5. **Format Selection**: Output format (JPEG, PNG, WebP)
6. **Processing**: Apply selected upscaling method
7. **Delivery**: Return enhanced image

### Reimagining Workflow (`/reimagine`)

1. **Method Selection**: Choose transformation approach
   - **Image**: Complete structural transformation
   - **Sketch**: Style transfer preserving structure
2. **Image Upload**: Source image for transformation
3. **Style Selection**: Choose artistic style
4. **Prompt Input**: New concept description
5. **Processing**: Apply selected transformation
6. **Delivery**: Return reimagined image

### Outpainting Workflow (`/uncrop`)

1. **Image Upload**: Source image for expansion
2. **Aspect Ratio Selection**: Choose expansion dimensions
3. **Position Selection**: Define original image placement
4. **Prompt Input** (optional): Context for expansion
5. **Processing**: Generate expanded image
6. **Delivery**: Return outpainted result

## Data Models

### ConversationState Enumeration
Defines all possible states in user interaction flows:

```python
class ConversationState(Enum):
    WAITING_FOR_PROMPT = auto()
    WAITING_FOR_CONTROL_TYPE = auto()
    WAITING_FOR_IMAGE = auto()
    WAITING_FOR_SIZE = auto()
    WAITING_FOR_STYLE = auto()
    # ... additional states
```

### Image Configuration Class
Centralized configuration for image parameters:

```python
@dataclass
class ImageConfig:
    SIZE_MAPPING: Dict[str, Tuple[int, int]]
    STYLE_PRESETS: List[List[str]]
    SIZE_PRESETS: List[List[str]]
```

### Operation Parameters
Structured parameter classes for different operations:

- `GenerationParams`: Text-to-image specifications
- `ReimagineParams`: Image transformation settings
- `UnCropParams`: Outpainting configuration

## Error Handling

### Error Categories
- **Authentication Errors**: Invalid user permissions
- **API Errors**: Stability AI service failures
- **Network Errors**: Connectivity issues
- **Validation Errors**: Invalid user input
- **Timeout Errors**: Conversation inactivity

### Recovery Mechanisms
- **Automatic Retry**: Network failures with exponential backoff
- **Graceful Degradation**: Continue operation despite non-critical failures
- **User Guidance**: Clear error messages with recovery instructions
- **Session Cleanup**: Automatic conversation reset on critical errors

### Logging Strategy
- **Structured Logging**: Consistent format across all components
- **Error Context**: Detailed error information for debugging
- **Performance Monitoring**: API call timing and success rates
- **User Activity Tracking**: Command usage analytics

## Usage Guidelines

### Best Practices for Image Generation

#### Prompt Engineering
- Use specific, descriptive language
- Include style and composition details
- Specify lighting and mood
- Reference artistic techniques or artists

#### Image Quality Optimization
- Choose appropriate aspect ratios for content type
- Select styles that complement the subject matter
- Use higher resolution for detailed subjects
- Consider composition when using reference images

### Operational Guidelines

#### Performance Considerations
- Large images increase processing time
- Complex prompts may require more API calls
- Network latency affects response times
- API rate limits apply to usage

#### Resource Management
- Generated images are stored temporarily
- Automatic cleanup prevents disk space issues
- Session timeouts prevent resource waste
- Memory usage scales with image size

## Development Notes

### Code Organization
- **Type Hints**: Comprehensive type annotations throughout
- **Documentation**: Inline docstrings for all public methods
- **Error Handling**: Consistent exception management patterns
- **Testing**: Unit tests for core functionality

### Extensibility
- **Modular Design**: Easy addition of new image operations
- **Configuration-Driven**: New parameters via environment variables
- **Plugin Architecture**: Command handlers can be extended independently
- **API Abstraction**: Stability AI integration can be replaced

### Maintenance Considerations
- **Dependency Management**: Regular updates to Python packages
- **API Compatibility**: Monitor Stability AI API changes
- **Security Updates**: Regular security patch application
- **Performance Monitoring**: Track API usage and response times

---

This documentation provides a comprehensive overview of the Telegram AI image generation bot implementation. For specific implementation details, refer to the inline code documentation and comments within each module.
