import { useState, useEffect } from 'react'
import { Upload, Image, Box, Download, Loader2, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Workspace {
  id: string
  workflow_id: string
  images: Array<{
    id: string
    url: string
    type: 'uploaded' | 'generated'
    filename?: string
    prompt?: string
  }>
  models: Array<{
    id: string
    stl_url: string
    obj_url: string
    glb_url: string
    preview_url: string
  }>
}

interface Job {
  id: string
  type: 'image_generation' | 'model_generation'
  status: 'processing' | 'completed' | 'failed'
  result?: any
}

function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  const [prompt, setPrompt] = useState('')
  const [styleTemplate, setStyleTemplate] = useState('')
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Record<string, Job>>({})
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    initializeWorkspace()
  }, [])

  const initializeWorkspace = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/workspace`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_id: 'gemini_hunyuan3d' })
      })
      const data = await response.json()
      
      const workspaceResponse = await fetch(`${API_BASE_URL}/api/workspace/${data.workspace_id}`)
      const workspaceData = await workspaceResponse.json()
      setWorkspace(workspaceData)
    } catch (error) {
      console.error('Failed to initialize workspace:', error)
    }
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !workspace) return

    setIsLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('workspace_id', workspace.id)

      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const updatedWorkspace = await fetch(`${API_BASE_URL}/api/workspace/${workspace.id}`)
        const workspaceData = await updatedWorkspace.json()
        setWorkspace(workspaceData)
        setCurrentStep(2)
      }
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleImageGeneration = async () => {
    if (!workspace || !prompt) return

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/generate/image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          workspace_id: workspace.id,
          style_template: styleTemplate,
          num_images: 1
        })
      })
      
      const data = await response.json()
      if (data.job_id) {
        pollJobStatus(data.job_id)
      }
    } catch (error) {
      console.error('Image generation failed:', error)
      setIsLoading(false)
    }
  }

  const handle3DModelGeneration = async () => {
    if (!workspace || !selectedImage) return

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/generate/model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspace.id,
          image_url: selectedImage
        })
      })
      
      const data = await response.json()
      if (data.job_id) {
        pollJobStatus(data.job_id)
      }
    } catch (error) {
      console.error('3D model generation failed:', error)
      setIsLoading(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`)
        const job = await response.json()
        
        setJobs(prev => ({ ...prev, [jobId]: job }))
        
        if (job.status === 'completed') {
          const updatedWorkspace = await fetch(`${API_BASE_URL}/api/workspace/${workspace?.id}`)
          const workspaceData = await updatedWorkspace.json()
          setWorkspace(workspaceData)
          setIsLoading(false)
          
          if (job.type === 'image_generation') {
            setCurrentStep(2)
          } else if (job.type === 'model_generation') {
            setCurrentStep(3)
          }
        } else if (job.status === 'processing') {
          setTimeout(poll, 2000)
        } else {
          setIsLoading(false)
        }
      } catch (error) {
        console.error('Job polling failed:', error)
        setIsLoading(false)
      }
    }
    poll()
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Box className="w-8 h-8 text-blue-400" />
            <h1 className="text-2xl font-bold">PrintVerse Clone</h1>
            <Badge variant="secondary" className="ml-2">Gemini + Hunyuan3D</Badge>
          </div>
          
          <div className="flex items-center gap-8 mb-6">
            <div className={`flex items-center gap-2 ${currentStep >= 1 ? 'text-blue-400' : 'text-gray-500'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep >= 1 ? 'bg-blue-400 text-black' : 'bg-gray-700'}`}>1</div>
              <span>Upload Image / Input Prompt</span>
            </div>
            <div className={`flex items-center gap-2 ${currentStep >= 2 ? 'text-blue-400' : 'text-gray-500'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep >= 2 ? 'bg-blue-400 text-black' : 'bg-gray-700'}`}>2</div>
              <span>Generate 3D Model</span>
            </div>
            <div className={`flex items-center gap-2 ${currentStep >= 3 ? 'text-blue-400' : 'text-gray-500'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep >= 3 ? 'bg-blue-400 text-black' : 'bg-gray-700'}`}>3</div>
              <span>Download Model</span>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Image className="w-5 h-5" />
                Image Generation
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Creation Style Template</label>
                <Select value={styleTemplate} onValueChange={setStyleTemplate}>
                  <SelectTrigger className="bg-gray-700 border-gray-600">
                    <SelectValue placeholder="Please select" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="realistic">Realistic</SelectItem>
                    <SelectItem value="cartoon">Cartoon</SelectItem>
                    <SelectItem value="anime">Anime</SelectItem>
                    <SelectItem value="abstract">Abstract</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Text Prompt</label>
                <Textarea
                  placeholder="Describe what you want to generate..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  className="bg-gray-700 border-gray-600 min-h-20"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Upload Image</label>
                <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center">
                  <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-400 mb-4">Drag and drop images here, or click to upload from anywhere</p>
                  <Input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                  />
                  <Button asChild variant="outline" className="border-gray-600">
                    <label htmlFor="file-upload" className="cursor-pointer">
                      Choose File
                    </label>
                  </Button>
                </div>
              </div>

              <Button 
                onClick={handleImageGeneration}
                disabled={!prompt || isLoading}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>

              <div className="text-sm text-gray-400">
                Select Number of Images: 1
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle>3D Effect Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-700 rounded-lg p-8 text-center min-h-64 flex flex-col items-center justify-center">
                {workspace?.images.length ? (
                  <div className="space-y-4">
                    {workspace.images.map((image) => (
                      <div key={image.id} className="relative">
                        <img
                          src={`${API_BASE_URL}${image.url}`}
                          alt="Generated"
                          className={`max-w-full h-auto rounded cursor-pointer border-2 ${
                            selectedImage === image.url ? 'border-blue-400' : 'border-transparent'
                          }`}
                          onClick={() => setSelectedImage(image.url)}
                        />
                        {image.type === 'generated' && (
                          <Badge className="absolute top-2 right-2 bg-green-600">Generated</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <>
                    <Box className="w-16 h-16 text-gray-500 mb-4" />
                    <p className="text-gray-400">Waiting for 3D effect preview generation</p>
                    <p className="text-sm text-gray-500">Complete the settings on the left and click the "Generate" button</p>
                  </>
                )}
              </div>

              <Button
                onClick={handle3DModelGeneration}
                disabled={!selectedImage || isLoading}
                className="w-full mt-4 bg-blue-600 hover:bg-blue-700"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    Generate 3D Model • 250 Credits
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-gray-800 border-gray-700">
            <CardHeader>
              <CardTitle>3D Model Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-700 rounded-lg p-8 text-center min-h-64 flex flex-col items-center justify-center">
                {workspace?.models.length ? (
                  <div className="space-y-4">
                    {workspace.models.map((model) => (
                      <div key={model.id} className="space-y-4">
                        <img
                          src={`${API_BASE_URL}${model.preview_url}`}
                          alt="3D Model Preview"
                          className="max-w-full h-auto rounded"
                        />
                        <div className="space-y-2">
                          <Button asChild variant="outline" className="w-full">
                            <a href={`${API_BASE_URL}${model.stl_url}`} download>
                              <Download className="w-4 h-4 mr-2" />
                              Download STL Model
                            </a>
                          </Button>
                          <Button asChild variant="outline" className="w-full">
                            <a href={`${API_BASE_URL}${model.obj_url}`} download>
                              <Download className="w-4 h-4 mr-2" />
                              Download OBJ Model
                            </a>
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <>
                    <Box className="w-16 h-16 text-gray-500 mb-4" />
                    <p className="text-gray-400">Waiting for 3D model generation</p>
                    <p className="text-sm text-gray-500">Complete the first two steps and click "Generate 3D Model" button</p>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default App
