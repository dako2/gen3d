# PrintVerse Clone with Hunyuan3D-2 Integration

A comprehensive 3D model generation platform that integrates Google Gemini for image generation and Hunyuan3D-2 for high-quality 3D model creation.

## Features

- **Text-to-Image Generation**: Uses Google Gemini (Nano Banana) for high-quality image generation from text prompts
- **Image-to-3D Conversion**: Leverages Hunyuan3D-2 for converting images to detailed 3D models
- **Multiple Export Formats**: Supports STL, OBJ, and GLB file formats for 3D printing and modeling
- **Real-time Processing**: Async job processing with real-time status updates
- **Modern UI**: Clean, dark-themed interface matching PrintVerse design

## Architecture

### Workflow
1. **Step 1**: User enters text prompt → Gemini generates high-quality image
2. **Step 2**: Generated image → Hunyuan3D-2 converts to 3D model with texture
3. **Step 3**: User downloads STL/OBJ/GLB files for 3D printing or modeling

### Technology Stack
- **Backend**: FastAPI with async processing
- **Frontend**: React + TypeScript + Tailwind CSS + shadcn/ui
- **AI Models**: 
  - Google Gemini 2.0 Flash (Nano Banana) for image generation
  - Hunyuan3D-2 DiT + Paint pipelines for 3D model generation
- **3D Processing**: Trimesh, PyMeshLab, pygltflib

## Installation

### Prerequisites
- Python 3.12+
- Node.js 18+
- CUDA-compatible GPU (recommended for Hunyuan3D-2)
- Google API key for Gemini

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
poetry install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your Google API key
```

4. Start the development server:
```bash
poetry run fastapi dev app/main.py
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Google API Key for Gemini integration
GOOGLE_API_KEY=your_google_api_key_here

# Hunyuan3D Model Configuration
HUNYUAN3D_CACHE_DIR=./models
HUNYUAN3D_DEVICE=auto

# FastAPI Configuration
DEBUG=True
```

### Model Downloads

Hunyuan3D-2 models will be automatically downloaded on first use:
- `tencent/Hunyuan3D-2-DiT` (~2GB)
- `tencent/Hunyuan3D-2-Paint` (~1.5GB)

## API Endpoints

### Core Endpoints
- `POST /api/workspace` - Create new workspace
- `GET /api/workspace/{workspace_id}` - Get workspace details
- `POST /api/upload` - Upload image files
- `POST /api/generate/image` - Generate images with Gemini
- `POST /api/generate/model` - Generate 3D models with Hunyuan3D-2
- `GET /api/jobs/{job_id}` - Check job status
- `GET /api/model/providers` - Get available AI model providers

### File Serving
- `GET /api/files/{file_id}` - Serve uploaded files
- `GET /api/generated/image/{image_id}` - Serve generated images
- `GET /api/generated/model/{filename}` - Download 3D model files
- `GET /api/generated/preview/{filename}` - Get 3D model previews

## Usage

1. **Start the Application**:
   - Backend: `poetry run fastapi dev app/main.py` (port 8000)
   - Frontend: `npm run dev` (port 5173)

2. **Generate 3D Models**:
   - Enter a descriptive text prompt
   - Wait for image generation (5-10 seconds)
   - Select the generated image
   - Wait for 3D model generation (2-5 minutes)
   - Download STL, OBJ, or GLB files

3. **Upload Images**:
   - Upload your own images for 3D conversion
   - Supported formats: PNG, JPG, JPEG
   - Images are automatically processed for optimal 3D generation

## Performance Notes

- **GPU Acceleration**: Hunyuan3D-2 benefits significantly from CUDA-compatible GPUs
- **Memory Requirements**: Minimum 8GB RAM, 16GB+ recommended
- **Processing Times**: 
  - Image generation: 5-10 seconds
  - 3D model generation: 2-5 minutes (depending on hardware)
- **Model Loading**: First-time model loading may take 1-2 minutes

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**:
   - Reduce batch size or use CPU mode
   - Set `HUNYUAN3D_DEVICE=cpu` in .env

2. **Model Download Failures**:
   - Check internet connection
   - Ensure sufficient disk space (5GB+)
   - Clear Hugging Face cache if needed

3. **API Key Issues**:
   - Verify Google API key is valid
   - Check API quotas and billing

## Development

### Project Structure
```
├── backend/
│   ├── app/
│   │   └── main.py          # FastAPI application
│   ├── pyproject.toml       # Python dependencies
│   └── .env                 # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   └── components/      # UI components
│   ├── package.json         # Node.js dependencies
│   └── .env                 # Frontend configuration
└── README.md
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project integrates multiple AI models with different licenses:
- Hunyuan3D-2: Tencent Hunyuan Non-Commercial License
- Google Gemini: Google AI Terms of Service
- Application code: MIT License

## Acknowledgments

- [Tencent Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) for 3D generation
- [Google Gemini](https://ai.google.dev/) for image generation
- [PrintVerse.ai](https://printverse.ai/) for design inspiration
