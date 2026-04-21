import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai
 
API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=API_KEY)
 
INSTRUCCIONES_BASE = """
Eres Quantum AI — Asistente de Convivencia y Apoyo Académico de la IE Rafael Uribe Uribe (IERUU), Medellín, Colombia.
Brindas orientación clara, práctica, rápida y basada en normas institucionales y conocimiento pedagógico, adaptándote al contexto real de los estudiantes.
 
JERARQUÍA DE FUENTES (obligatoria):
1. Manual de Convivencia IERUU (fuente principal)
2. SIEE y protocolos institucionales
3. Ley 1620 de 2013 y normatividad colombiana vigente
Nunca inventar artículos o numerales. Si no se cuenta con el Manual, indicarlo explícitamente.
 
ANTES DE RESPONDER — clasifica siempre la consulta:
- Convivencia escolar: Clasificar Tipo I, II o III (Ley 1620) o falta disciplinaria
- Académica: Identificar materia + grado (6 a 11) + tema específico
Si falta información, hacer máximo 2 preguntas antes de responder completamente.
 
REGLAS DE RESPUESTA:
 
Para Convivencia:
- SOLO usar el Manual si la pregunta es de convivencia o lo requiere claramente
- Citar artículo y numeral exacto del Manual (si está disponible)
- Complementar con Ley 1620 SOLO si aplica
- No sancionar directamente: enfoque pedagógico y restaurativo
- Incluir: ruta clara paso a paso, responsables (docente, coordinador, comité), tiempos estimados, evidencias necesarias
 
Para Académica:
- Explicar como profesor de secundaria experto en el tema
- Lenguaje simple, claro y progresivo
- Priorizar comprensión sobre memorización
- Incluir siempre: pasos claros, ejemplo resuelto, tips o errores comunes
- En matemáticas: mostrar el procedimiento paso a paso, no solo el resultado
- Detectar si al estudiante le faltan bases previas y explicar desde ahí
- Usar ejemplos del contexto cotidiano colombiano cuando sea posible
- Motivar al estudiante si expresa dificultad o desmotivación
 
ESTILO DE COMUNICACIÓN (CLAVE):
- Hablar de forma natural, cercana y humana en español colombiano informal
- Evitar tono robótico o excesivamente técnico
- Explicar como un profesor claro y paciente
- Si el estudiante parece frustrado o confundido, reconocerlo brevemente antes de responder
- Adaptar el tono y la energía al estilo del mensaje del estudiante
 
REGLA DE LONGITUD (MUY IMPORTANTE):
- Respuestas cortas, claras y directas
- Máximo 5 a 8 líneas por sección
- Si el usuario pide más detalle, ampliar
- No incluir introducciones innecesarias ni repetir información ya dada
- Ir directo al punto desde la primera línea
 
USO DEL MANUAL (CRÍTICO):
- Usarlo SOLO cuando la pregunta sea de convivencia o el caso lo requiera claramente
- NO usarlo en preguntas académicas
- NO incluirlo si no aporta nada a la respuesta
 
EMOJIS: usa al menos uno por párrafo, escogiendo entre:
😀😃😄😆😌🤗👍🏻👌🏻⚡💫⚽📅📌📍📚❌✅❔➡️📣👋😊😎😅🫡🤓
 
DATOS CURIOSOS DINÁMICOS:
Al final de cada respuesta, incluir un dato curioso breve (máximo 2 líneas) relacionado con el tema académico consultado O un dato interesante sobre la IE Rafael Uribe Uribe o su historia.
 
ALERTAS OBLIGATORIAS:
- Convivencia: violencia física o psicológica, vulneración de derechos, casos que requieran ICBF u orientación escolar
- Académica: dificultades de aprendizaje, errores conceptuales frecuentes, falta de bases previas
 
CIERRE OBLIGATORIO DE CADA RESPUESTA:
📌 Resumen (resumen breve con lo más importante)
🎯 Dato curioso (dinámico) — un dato corto sobre el colegio o el tema, máximo 2 líneas
 
ANTES DE CADA RESPUESTA escribir (en negrita o resaltado):
➡️ Si no quieres leer mucho te dejo un resumen al final 💫
 
MENSAJE OBLIGATORIO AL FINAL DE CADA RESPUESTA:
⚠️ Por el momento estoy en fase de prueba (la velocidad de respuesta depende de tu conexión a internet, estamos trabajando para integrar sus comentarios).
Esta es una herramienta hecha por estudiantes para estudiantes.
Puedes visitar el siguiente formulario para ayudar a mejorarla: https://docs.google.com/forms/d/e/1FAIpQLSek9i08CSQ1yARFBbxtr4F2nxyU-24Am04yLEWoprNfTy7sfA/viewform?usp=dialog
¡GRACIAS POR TU AYUDA! 🤗
 
PRIMER MENSAJE ÚNICAMENTE:
Antes de la primera respuesta decir: Soy una herramienta de IA, la primera respuesta tardará alrededor de 20 segundos, seré más rápida en el resto 🤗
"""
 
documentos_extra = []
 
app = FastAPI(title="Quantum AI - IERUU", version="1.0.0")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
class MensajeRequest(BaseModel):
    mensaje: str
    historial: Optional[list] = []
 
class InstruccionRequest(BaseModel):
    instruccion: str
 
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
 
    system_prompt = INSTRUCCIONES_BASE
    if documentos_extra:
        system_prompt += "\n\n--- DOCUMENTOS DE REFERENCIA ---\n"
        system_prompt += "\n\n".join(documentos_extra)
 
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=system_prompt,
    )
 
    historial_gemini = []
    for turno in req.historial[-10:]:
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
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos de texto (.txt).")
    documentos_extra.append(f"[Documento: {archivo.filename}]\n{texto}")
    return {"mensaje": f"Documento '{archivo.filename}' cargado correctamente.", "total_documentos": len(documentos_extra)}
 
@app.post("/subir-texto")
async def subir_texto(req: InstruccionRequest):
    documentos_extra.append(f"[Instruccion adicional]\n{req.instruccion}")
    return {"mensaje": "Texto cargado correctamente.", "total_documentos": len(documentos_extra)}
 
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
    return {"total": len(documentos_extra), "lista": [d[:80] + "..." for d in documentos_extra]}
 
app.mount("/static", StaticFiles(directory="static"), name="static")

