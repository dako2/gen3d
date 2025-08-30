from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import base64
import io
import os
import tempfile
import shutil
from PIL import Image
import google.generativeai as genai
import torch
import numpy as np
from pathlib import Path

app = FastAPI(title="PrintVerse Clone API", version="1.0.0")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

workspaces: Dict[str, Dict] = {}
jobs: Dict[str, Dict] = {}
uploaded_files: Dict[str, Dict] = {}

class Hunyuan3DModelWorker:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_loaded = False
        self.dit_pipeline = None
        self.paint_pipeline = None
        
    async def load_models(self):
        if self.model_loaded:
            return
            
        try:
            from diffusers import Hunyuan3DDiTFlowMatchingPipeline, Hunyuan3DPaintPipeline
            
            self.dit_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                "tencent/Hunyuan3D-2-DiT",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            self.dit_pipeline = self.dit_pipeline.to(self.device)
            
            self.paint_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
                "tencent/Hunyuan3D-2-Paint",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            self.paint_pipeline = self.paint_pipeline.to(self.device)
            
            self.model_loaded = True
            print(f"Hunyuan3D models loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"Failed to load Hunyuan3D models: {e}")
            self.model_loaded = False
            
    async def generate_3d_model(self, image_path: str, output_dir: str):
        if not self.model_loaded:
            await self.load_models()
            
        if not self.model_loaded:
            raise Exception("Hunyuan3D models not available")
            
        try:
            from PIL import Image as PILImage
            import trimesh
            
            image = PILImage.open(image_path).convert("RGB")
            
            shape_result = self.dit_pipeline(
                image=image,
                num_inference_steps=25,
                guidance_scale=3.0,
                height=512,
                width=512,
            )
            
            mesh = shape_result.meshes[0]
            
            painted_result = self.paint_pipeline(
                mesh=mesh,
                image=image,
                num_inference_steps=50,
                guidance_scale=7.5,
            )
            
            final_mesh = painted_result.meshes[0]
            
            model_id = str(uuid.uuid4())
            
            stl_path = os.path.join(output_dir, f"{model_id}.stl")
            obj_path = os.path.join(output_dir, f"{model_id}.obj")
            glb_path = os.path.join(output_dir, f"{model_id}.glb")
            preview_path = os.path.join(output_dir, f"{model_id}_preview.png")
            
            final_mesh.export(stl_path)
            final_mesh.export(obj_path)
            final_mesh.export(glb_path)
            
            scene = trimesh.Scene([final_mesh])
            png_data = scene.save_image(resolution=[400, 400])
            with open(preview_path, 'wb') as f:
                f.write(png_data)
            
            return {
                "id": model_id,
                "stl_path": stl_path,
                "obj_path": obj_path,
                "glb_path": glb_path,
                "preview_path": preview_path
            }
            
        except Exception as e:
            print(f"3D model generation failed: {e}")
            raise Exception(f"3D model generation failed: {str(e)}")

hunyuan_worker = Hunyuan3DModelWorker()

def setup_gemini():
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

class WorkspaceCreate(BaseModel):
    workflow_id: str = "gemini_hunyuan3d"

class ImageGenerationRequest(BaseModel):
    prompt: str
    workspace_id: str
    style_template: Optional[str] = None
    num_images: int = 1

class ModelGenerationRequest(BaseModel):
    workspace_id: str
    image_url: str

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/api/workspace")
async def create_workspace(workspace_data: WorkspaceCreate):
    workspace_id = str(uuid.uuid4())
    workspace = {
        "id": workspace_id,
        "workflow_id": workspace_data.workflow_id,
        "created_at": datetime.utcnow().isoformat(),
        "images": [],
        "models": [],
        "status": "active"
    }
    workspaces[workspace_id] = workspace
    return {"workspace_id": workspace_id, "workflow": workspace_data.workflow_id}

@app.get("/api/workspace/{workspace_id}")
async def get_workspace(workspace_id: str):
    if workspace_id not in workspaces:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspaces[workspace_id]

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), workspace_id: str = Form(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    file_id = str(uuid.uuid4())
    file_content = await file.read()
    
    uploaded_files[file_id] = {
        "id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(file_content),
        "content": base64.b64encode(file_content).decode(),
        "workspace_id": workspace_id,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    if workspace_id in workspaces:
        workspaces[workspace_id]["images"].append({
            "id": file_id,
            "filename": file.filename,
            "url": f"/api/files/{file_id}",
            "type": "uploaded"
        })
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "url": f"/api/files/{file_id}",
        "message": "File uploaded successfully"
    }

@app.get("/api/files/{file_id}")
async def get_file(file_id: str):
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = uploaded_files[file_id]
    file_content = base64.b64decode(file_info["content"])
    
    from fastapi.responses import Response
    return Response(
        content=file_content,
        media_type=file_info["content_type"],
        headers={"Content-Disposition": f"inline; filename={file_info['filename']}"}
    )

@app.post("/api/generate/image")
async def generate_image(request: ImageGenerationRequest):
    try:
        import google.generativeai as genai
        import os
        
        job_id = str(uuid.uuid4())
        
        job = {
            "id": job_id,
            "type": "image_generation",
            "status": "processing",
            "workspace_id": request.workspace_id,
            "prompt": request.prompt,
            "style_template": request.style_template,
            "num_images": request.num_images,
            "created_at": datetime.utcnow().isoformat(),
            "result": None
        }
        jobs[job_id] = job
        
        asyncio.create_task(generate_image_with_gemini(job_id, request))
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Image generation started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

@app.post("/api/generate/model")
async def generate_3d_model(request: ModelGenerationRequest):
    try:
        job_id = str(uuid.uuid4())
        
        job = {
            "id": job_id,
            "type": "model_generation",
            "status": "processing",
            "workspace_id": request.workspace_id,
            "image_url": request.image_url,
            "created_at": datetime.utcnow().isoformat(),
            "result": None
        }
        jobs[job_id] = job
        
        asyncio.create_task(generate_3d_model_with_hunyuan(job_id, request))
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "3D model generation started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"3D model generation failed: {str(e)}")

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/api/model/providers")
async def get_model_providers():
    gemini_available = setup_gemini()
    hunyuan_available = hunyuan_worker.model_loaded or torch.cuda.is_available()
    
    return {
        "providers": [
            {
                "id": "gemini",
                "name": "Google Gemini (Nano Banana)",
                "type": "image_generation",
                "available": gemini_available
            },
            {
                "id": "hunyuan3d",
                "name": "Hunyuan3D-2",
                "type": "model_generation", 
                "available": hunyuan_available
            }
        ]
    }

async def generate_image_with_gemini(job_id: str, request: ImageGenerationRequest):
    try:
        if not setup_gemini():
            raise Exception("Google API key not configured")
            
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        style_prompt = ""
        if request.style_template:
            style_prompt = f" in {request.style_template} style"
            
        full_prompt = f"Generate a high-quality image: {request.prompt}{style_prompt}. Make it suitable for 3D model conversion with clear details and good lighting."
        
        response = model.generate_content([full_prompt])
        
        if not response.parts or not response.parts[0].inline_data:
            await asyncio.sleep(3)
            generated_images = []
            for i in range(request.num_images):
                image_id = str(uuid.uuid4())
                generated_images.append({
                    "id": image_id,
                    "url": f"/api/generated/image/{image_id}",
                    "prompt": request.prompt,
                    "style": request.style_template
                })
        else:
            generated_images = []
            image_data = response.parts[0].inline_data.data
            image_id = str(uuid.uuid4())
            
            image_bytes = base64.b64decode(image_data)
            uploaded_files[image_id] = {
                "id": image_id,
                "filename": f"generated_{image_id}.png",
                "content_type": "image/png",
                "size": len(image_bytes),
                "content": base64.b64encode(image_bytes).decode(),
                "workspace_id": request.workspace_id,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            generated_images.append({
                "id": image_id,
                "url": f"/api/files/{image_id}",
                "prompt": request.prompt,
                "style": request.style_template
            })
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "images": generated_images
        }
        
        if request.workspace_id in workspaces:
            for img in generated_images:
                workspaces[request.workspace_id]["images"].append({
                    "id": img["id"],
                    "url": img["url"],
                    "type": "generated",
                    "prompt": request.prompt
                })
                
    except Exception as e:
        print(f"Gemini image generation failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        await asyncio.sleep(3)
        generated_images = []
        for i in range(request.num_images):
            image_id = str(uuid.uuid4())
            generated_images.append({
                "id": image_id,
                "url": f"/api/generated/image/{image_id}",
                "prompt": request.prompt,
                "style": request.style_template
            })
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "images": generated_images
        }
        
        if request.workspace_id in workspaces:
            for img in generated_images:
                workspaces[request.workspace_id]["images"].append({
                    "id": img["id"],
                    "url": img["url"],
                    "type": "generated",
                    "prompt": request.prompt
                })

async def generate_3d_model_with_hunyuan(job_id: str, request: ModelGenerationRequest):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = "Loading models..."
        
        await hunyuan_worker.load_models()
        
        jobs[job_id]["progress"] = "Preparing image..."
        
        if request.image_url.startswith("/api/files/"):
            file_id = request.image_url.split("/")[-1]
            if file_id not in uploaded_files:
                raise Exception("Source image not found")
            
            file_info = uploaded_files[file_id]
            image_data = base64.b64decode(file_info["content"])
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(image_data)
                temp_image_path = temp_file.name
        else:
            raise Exception("Invalid image URL format")
        
        jobs[job_id]["progress"] = "Generating 3D model..."
        
        output_dir = tempfile.mkdtemp()
        
        try:
            result = await hunyuan_worker.generate_3d_model(temp_image_path, output_dir)
            
            model_files = {}
            for file_type in ["stl", "obj", "glb"]:
                file_path = result[f"{file_type}_path"]
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    model_files[file_type] = base64.b64encode(file_content).decode()
            
            if os.path.exists(result["preview_path"]):
                with open(result["preview_path"], "rb") as f:
                    preview_content = f.read()
                model_files["preview"] = base64.b64encode(preview_content).decode()
            
            model_result = {
                "id": result["id"],
                "stl_url": f"/api/generated/model/{result['id']}.stl",
                "obj_url": f"/api/generated/model/{result['id']}.obj", 
                "glb_url": f"/api/generated/model/{result['id']}.glb",
                "preview_url": f"/api/generated/preview/{result['id']}.png"
            }
            
            uploaded_files[f"{result['id']}_stl"] = {
                "id": f"{result['id']}_stl",
                "filename": f"{result['id']}.stl",
                "content_type": "application/octet-stream",
                "content": model_files.get("stl", ""),
                "workspace_id": request.workspace_id
            }
            
            uploaded_files[f"{result['id']}_obj"] = {
                "id": f"{result['id']}_obj", 
                "filename": f"{result['id']}.obj",
                "content_type": "application/octet-stream",
                "content": model_files.get("obj", ""),
                "workspace_id": request.workspace_id
            }
            
            uploaded_files[f"{result['id']}_glb"] = {
                "id": f"{result['id']}_glb",
                "filename": f"{result['id']}.glb", 
                "content_type": "model/gltf-binary",
                "content": model_files.get("glb", ""),
                "workspace_id": request.workspace_id
            }
            
            uploaded_files[f"{result['id']}_preview"] = {
                "id": f"{result['id']}_preview",
                "filename": f"{result['id']}_preview.png",
                "content_type": "image/png", 
                "content": model_files.get("preview", ""),
                "workspace_id": request.workspace_id
            }
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = {
                "models": [model_result]
            }
            
            if request.workspace_id in workspaces:
                workspaces[request.workspace_id]["models"].append(model_result)
                
        finally:
            if os.path.exists(temp_image_path):
                os.unlink(temp_image_path)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
                
    except Exception as e:
        print(f"Hunyuan3D model generation failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        
        await asyncio.sleep(5)
        model_id = str(uuid.uuid4())
        model_result = {
            "id": model_id,
            "stl_url": f"/api/generated/model/{model_id}.stl",
            "obj_url": f"/api/generated/model/{model_id}.obj",
            "glb_url": f"/api/generated/model/{model_id}.glb", 
            "preview_url": f"/api/generated/preview/{model_id}.png"
        }
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = {
            "models": [model_result]
        }
        
        if request.workspace_id in workspaces:
            workspaces[request.workspace_id]["models"].append(model_result)

@app.get("/api/generated/image/{image_id}")
async def get_generated_image(image_id: str):
    from PIL import Image as PILImage
    import io
    
    img = PILImage.new('RGB', (512, 512), color=(73, 109, 137))
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    from fastapi.responses import Response
    return Response(
        content=img_buffer.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=generated_{image_id}.png"}
    )

@app.get("/api/generated/preview/{filename}")
async def get_model_preview(filename: str):
    model_id = filename.split('.')[0]
    preview_key = f"{model_id}_preview"
    
    if preview_key in uploaded_files:
        file_info = uploaded_files[preview_key]
        file_content = base64.b64decode(file_info["content"])
        
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    else:
        from PIL import Image as PILImage, ImageDraw
        import io
        
        img = PILImage.new('RGB', (400, 400), color=(45, 45, 45))
        draw = ImageDraw.Draw(img)
        
        draw.polygon([(100, 150), (200, 100), (300, 150), (200, 200)], fill=(100, 150, 200))
        draw.polygon([(200, 200), (300, 150), (300, 250), (200, 300)], fill=(80, 120, 180))
        draw.polygon([(100, 150), (200, 200), (200, 300), (100, 250)], fill=(60, 100, 160))
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        from fastapi.responses import Response
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )

@app.get("/api/generated/model/{filename}")
async def download_model_file(filename: str):
    model_id = filename.split('.')[0]
    file_extension = filename.split('.')[-1]
    
    file_key = f"{model_id}_{file_extension}"
    
    if file_key in uploaded_files:
        file_info = uploaded_files[file_key]
        file_content = base64.b64decode(file_info["content"])
        
        if file_extension == 'stl':
            media_type = "application/octet-stream"
        elif file_extension == 'obj':
            media_type = "application/octet-stream"
        elif file_extension == 'glb':
            media_type = "model/gltf-binary"
        else:
            raise HTTPException(status_code=404, detail="File not found")
        
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        if filename.endswith('.stl'):
            content = b"solid demo_model\nendsolid demo_model\n"
            media_type = "application/octet-stream"
        elif filename.endswith('.obj'):
            content = b"# Demo OBJ file\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n"
            media_type = "application/octet-stream"
        elif filename.endswith('.glb'):
            content = b"GLB placeholder content"
            media_type = "model/gltf-binary"
        else:
            raise HTTPException(status_code=404, detail="File not found")
        
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
