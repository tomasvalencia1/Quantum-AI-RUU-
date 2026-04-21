import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai

# ──────────────────────────────────────────
#  Configuración
# ──────────────────────────────────────────
API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)

INSTRUCCIONES_BASE = """
Eres Quantum AI, el asistente de estudio inteligente del Instituto de Educación Rafael Uribe Uribe (IERUU) de Medellín, Colombia.

Tu misión es ayudar a los estudiantes de bachillerato a comprender y aprender todas las materias del currículo:
ciencias naturales, matemáticas, filosofía, historia, inglés, química, geometría, español, y más.

Reglas de comportamiento:
- Habla siempre en español colombiano, informal y cercano (tutéame al estudiante).
- Explica con ejemplos concretos y cotidianos. Nada de respuestas robóticas.
- Si el estudiante no entiende, busca otra forma de explicar.
- Motiva al estudiante cuando lo necesite, pero sin exagerar.
- Si te preguntan algo fuera del ámbito académico, redirige amablemente.
- Sé honesto si no sabes algo.
- Usa emojis con moderación para hacer las respuestas más amigables.
- Respuestas cortas y claras primero; amplía solo si el estudiante pide más detalle.
- Recuerda el protocolo de convivencia de la institución: respeto, honestidad y responsabilidad.
"""

# Documentos cargados en memoria (persisten mientras el servidor esté activo)
documentos_extra = []

app = FastAPI(title="Quantum AI – IERUU", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────
#  Modelos de datos
# ──────────────────────────────────────────
class MensajeRequest(BaseModel):
    mensaje: str
    historial: Optional[list] = []

class InstruccionRequest(BaseModel):
    instruccion: str

# ──────────────────────────────────────────
#  Rutas de la API
# ──────────────────────────────────────────

@app.get("/")
def raiz():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"estado": "activo", "documentos_cargados": len(documentos_extra)}

@app.post("/chat")
async def chat(req: MensajeRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurada")

    # Construir system prompt con instrucciones base + documentos subidos
    system_prompt = INSTRUCCIONES_BASE
    if documentos_extra:
        system_prompt += "\n\n--- DOCUMENTOS DE REFERENCIA ---\n"
        system_prompt += "\n\n".join(documentos_extra)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=system_prompt,
    )

    # Convertir historial al formato de Gemini
    historial_gemini = []
    for turno in req.historial[-10:]:  # Solo últimos 10 turnos para no gastar tokens
        historial_gemini.append({
            "role": turno.get("rol", "user"),
            "parts": [turno.get("texto", "")]
        })

    chat_session = model.start_chat(history=historial_gemini)

    try:
        respuesta = chat_session.send_message(req.mensaje)
        return {
            "respuesta": respuesta.text,
            "tokens_usados": respuesta.usage_metadata.total_token_count if hasattr(respuesta, 'usage_metadata') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de Gemini: {str(e)}")


@app.post("/subir-documento")
async def subir_documento(archivo: UploadFile = File(...)):
    contenido_bytes = await archivo.read()
    try:
        texto = contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos de texto (.txt). Para PDFs usa /subir-texto.")

    documentos_extra.append(f"[Documento: {archivo.filename}]\n{texto}")
    return {
        "mensaje": f"Documento '{archivo.filename}' cargado correctamente.",
        "total_documentos": len(documentos_extra)
    }


@app.post("/subir-texto")
async def subir_texto(req: InstruccionRequest):
    documentos_extra.append(f"[Instrucción/Documento adicional]\n{req.instruccion}")
    return {
        "mensaje": "Texto cargado correctamente.",
        "total_documentos": len(documentos_extra)
    }


@app.post("/actualizar-instrucciones")
async def actualizar_instrucciones(req: InstruccionRequest):
    global INSTRUCCIONES_BASE
    INSTRUCCIONES_BASE = req.instruccion
    return {"mensaje": "Instrucciones actualizadas correctamente."}


@app.delete("/limpiar-documentos")
async def limpiar_documentos():
    documentos_extra.clear()
    return {"mensaje": "Todos los documentos fueron eliminados."}


@app.get("/estado-documentos")
async def estado_documentos():
    return {
        "total": len(documentos_extra),
        "lista": [d[:80] + "..." for d in documentos_extra]
    }


# Archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")
