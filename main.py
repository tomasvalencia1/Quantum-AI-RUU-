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
        model_name="gemini-2.5-flash",
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
 
# ──────────────────────────────────────────
#  Documentos curriculares permanentes IERUU
# ──────────────────────────────────────────
DOCUMENTOS_PERMANENTES = """
=== MALLA CURRICULAR QUÍMICA 2025 – IE RAFAEL URIBE URIBE ===
 
GRADO 6° – QUÍMICA
Período 1: Propiedades fisicoquímicas (solubilidad, viscosidad, densidad, puntos de ebullición y fusión). Influencia de temperatura y presión. Técnicas de separación de mezclas.
Período 2: Variaciones de T y P en cambio de fase y disolución. Diseño de experimentos sencillos.
Período 3: Selección de técnicas de separación en procesos industriales y científicos. Sostenibilidad.
 
GRADO 7° – QUÍMICA
Período 1: Sistema periódico. Clasificación de elementos: metales, no metales, metaloides. Grupos y períodos.
Período 2: Propiedades de elementos y formación de compuestos químicos según posición en tabla periódica.
Período 3: Relación grupos/períodos con propiedades químicas. Experimentos de formación de compuestos.
 
GRADO 8° – QUÍMICA
Período 1: Reacciones químicas. Recombinación atómica. Enlaces iónicos y covalentes.
Período 2: Conservación de la masa. Balanceo de ecuaciones químicas sencillas.
Período 3: Cambios energéticos en reacciones de síntesis y descomposición. Impacto ambiental.
 
GRADO 9° – QUÍMICA
Período 1: Acidez y basicidad. Propiedades de ácidos y bases. Indicadores químicos.
Período 2: Reacciones ácido-base. Relación con procesos biológicos (digestión, pH corporal).
Período 3: Escala de pH. Medición de pH en muestras. Prácticas responsables.
 
GRADO 10° – QUÍMICA (3h/semana)
Período 1: Mecanismos de reacción: óxido-reducción, descomposición, neutralización, precipitación. Configuración electrónica y tabla periódica.
Período 2: Ley de conservación de masa y carga. Balanceo avanzado. Relaciones molares entre reactivos y productos.
Período 3: Formación de compuestos inorgánicos. Nomenclatura IUPAC: óxidos, ácidos, hidróxidos, sales.
 
GRADO 11° – QUÍMICA (3h/semana)
Período 1: Configuración electrónica. Formación de compuestos inorgánicos (repaso y profundización de 10°).
Período 2: Química orgánica. Mecanismos: óxido-reducción, homólisis, heterólisis, pericíclicas. Alcoholes, fenoles, cetonas, aldehídos.
Período 3: Factores energéticos en reacciones orgánicas (exotérmico/endotérmico). Nomenclatura IUPAC orgánica. Procesos sostenibles.
 
=== MALLA CURRICULAR ECONOMÍA Y CIENCIAS POLÍTICAS 2025 – IE RAFAEL URIBE URIBE ===
 
GRADO 10° – ECONOMÍA Y CIENCIAS POLÍTICAS (2h/semana)
Período 1 – Relaciones con la historia y culturas: Hitos históricos de sistemas económicos y políticos. Influencia histórica en decisiones políticas y económicas de las sociedades.
Período 2 – Relaciones Ético-Políticas: Vínculos entre economía, ambiente y política. Impacto de actividades económicas en el medio ambiente. Mapas conceptuales.
Período 3 – Relaciones espaciales y ambientales: Fundamentos ético-políticos de sistemas democráticos. Participación ciudadana. Simulación de procesos democráticos.
 
GRADO 11° – ECONOMÍA Y CIENCIAS POLÍTICAS (2h/semana)
Período 1 – Relaciones con la historia y culturas: Sistemas políticos y económicos globales. Influencia en transformaciones culturales. Análisis comparativo de economías mundiales.
Período 2 – Relaciones Ético-Políticas: Políticas públicas y desarrollo sostenible. Proyectos de mitigación ambiental. Pensamiento crítico y sistémico.
Período 3 – Relaciones espaciales y ambientales: Responsabilidad ciudadana en democracia. Justicia social y derechos humanos. Debates escolares.
 
Institución: IE Rafael Uribe Uribe | Núcleo 930 – Comuna 12 | Medellín
Lema: "Innovación, liderazgo y ciudadanía"
"""
 
# Inyectar documentos permanentes al inicio de documentos_extra
documentos_extra.insert(0, DOCUMENTOS_PERMANENTES)
 
# Tecnología e Informática - agregada como documento adicional
DOCUMENTOS_PERMANENTES += """
 
=== MALLA CURRICULAR TECNOLOGÍA E INFORMÁTICA 2025 – IE RAFAEL URIBE URIBE ===
 
GRADO 1° – Tecnología e Informática (2h/semana)
P1: Naturaleza de la tecnología. Artefactos y necesidades cotidianas. Respeto por la evolución tecnológica.
P2: Materiales en artefactos. Función de cada artefacto. Clasificación según finalidad. Seguridad personal.
P3: Componentes de artefactos. Elección del artefacto adecuado. Uso racional y cuidado de herramientas.
 
GRADO 2° – Tecnología e Informática (2h/semana)
P1: Historia de la tecnología. Clasificación de artefactos por características físicas, uso y procedencia. Emprendimiento.
P2: Evolución de artefactos. Computadora como herramienta de comunicación. Trabajo en equipo.
P3: Innovación en artefactos. Detección de fallas simples. Trabajo colaborativo.
 
GRADO 3° – Tecnología e Informática (2h/semana)
P1: Artefactos en el entorno escolar. Manejo de herramientas tecnológicas. Normas de clase.
P2: Funcionamiento de artefactos. Uso responsable de tecnología. Solución de problemas cotidianos.
P3: Tecnología como ayuda cotidiana. Clasificación por función. Cambios tecnológicos en la sociedad.
 
GRADO 4° – Tecnología e Informática (2h/semana)
P1: Diferencia productos tecnológicos vs naturales. TIC para comunicación, aprendizaje e investigación. Ventajas/desventajas de soluciones tecnológicas.
P2: Artefactos con tecnología de información. Herramientas manuales: medición, trazado, corte. Diseño de maquetas.
P3: Fuentes y tipos de energía. Representación de productos tecnológicos con esquemas y dibujos. Impacto social y ambiental.
 
GRADO 5° – Tecnología e Informática (2h/semana)
P1: Fuentes y tipos de energía. TIC para aprendizaje y búsqueda de información. Uso mesurado de energía.
P2: Criterios de calidad en artefactos. Descripción mediante esquemas y dibujos. Construcción de objetos.
P3: Instituciones e innovaciones para el desarrollo del país. Construcción de maquetas y material reciclable.
 
GRADO 6° – Tecnología e Informática (2h/semana)
P1: Principios de ciencia aplicados a tecnología. Evaluación crítica de productos tecnológicos. Impacto ambiental de la tecnología. Reciclaje de desechos tecnológicos.
P2: Innovaciones e inventos trascendentales. Criterios para selección de soluciones: eficiencia, seguridad, costo, impacto. Preservación del ambiente.
P3: Relación tecnología-informática con factores históricos. Herramientas y equipos seguros. Derechos de acceso a bienes tecnológicos.
 
GRADO 7° – Tecnología e Informática (2h/semana)
P1: Sistemas tecnológicos: principios, conceptos, componentes. Contenidos digitales. Solución de problemas cotidianos. Uso racional de recursos.
P2: Innovaciones históricas. TIC para procesar y comunicar información. Ventajas/desventajas de tecnología y naturaleza.
P3: Evolución de técnicas, herramientas y materiales. Algoritmos básicos: secuenciación, condición, repetición. Uso ético de tecnología.
 
GRADO 8° – Tecnología e Informática (2h/semana)
P1: Relación tecnología con otras disciplinas. Herramientas colaborativas con principios éticos, estéticos y legales. Interpretación de diseños e innovaciones.
P2: Inventos, innovaciones y desarrollo tecnológico. Mantenimiento preventivo de productos tecnológicos. Detección de fallas en sistemas.
P3: Evolución del conocimiento y tecnología. Uso eficiente de herramientas en otras disciplinas. Patentes, derechos de autor y desarrollo tecnológico. Impacto ambiental de sobreexplotación de recursos.
 
GRADO 9° – Tecnología e Informática (2h/semana)
P1: Diferencia entre ciencia, técnica e ingeniería. Clasificación de productos tecnológicos por problemáticas. Detección de fallas y propuesta de soluciones.
P2: Principios que hacen posible la tecnología. Selección argumentada de productos tecnológicos. Patentes y derechos de autor. Ética en el diseño tecnológico.
P3: Diseño de nuevos productos tecnológicos. Herramientas digitales emergentes e inteligencia artificial. Influencia de la tecnología en cambios sociales y culturales.
 
GRADO 10° – Tecnología e Informática (2h/semana)
P1: Tecnología como cúmulo de conocimientos históricos. Aplicaciones de tecnología según contexto. Gestión de soluciones eficientes. Impactos positivos y negativos de la tecnología.
P2: Evolución tecnológica e informática en la sociedad. Normas de seguridad industrial. Mantenimiento correctivo de productos. Diseño de soluciones con informática.
P3: Licencias de artefactos digitales y analógicos. Herramientas informáticas para búsqueda y organización. Soluciones tecnológicas comunitarias. Cultura informática, respeto e inclusión.
 
GRADO 11° – Tecnología e Informática (2h/semana)
P1: Transferencia tecnológica exitosa. Propuestas innovadoras. Función correcta de medios tecnológicos con ética. Reciclaje de desechos tecnológicos.
P2: Incidencia del conocimiento tecnológico en sistemas futuros. Diseño y prueba de prototipos. Antropometría y ergonomía en soluciones. Protocolos de seguridad y ética digital.
P3: Diferencia entre prospecto, diseño y maqueta. Propuestas de innovación tecnológica. Debates sobre buen uso y manejo ético de TIC. Fomento de cultura tecnológica responsable.
"""
