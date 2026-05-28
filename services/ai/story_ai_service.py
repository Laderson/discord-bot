import os
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")


# =========================
# MEJORAR HISTORIA
# =========================
async def improve_story(story: str):

    prompt = f"""
Corrige ortografía, puntuación y coherencia del siguiente texto.

IMPORTANTE:
- NO expliques lo que hiciste. 
- NO agregues introducciones. 
- NO agregues conclusiones. 
- NO escribas frases como "aquí tienes el texto corregido". 
- SOLO devuelve el texto final corregido. 
- Mantén el mismo significado.
- NO inventes contenido nuevo.
- NO agregues personajes.
- NO cambies eventos.
- NO alteres el significado.
- Mantén exactamente la misma historia.
- Hazlo por parrafos, para mejorar la fluidez, pero sin cambiar nada del contenido.
- Solo mejora gramática, puntuación y fluidez.

Texto:

{story}
"""

    response = model.generate_content(prompt)

    return response.text
