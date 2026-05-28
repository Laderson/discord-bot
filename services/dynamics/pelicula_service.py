import random
import unicodedata

QUESTIONS = [
    # =========================
    # 🎬 CLÁSICOS (TEXT)
    # =========================
    {"type": "text", "question": "Siempre nos quedará París", "answer": "casablanca"},
    {"type": "text", "question": "Francamente querida, me importa un bledo", "answer": "lo que el viento se llevo"},
    {"type": "text", "question": "Estoy cantando bajo la lluvia", "answer": "cantando bajo la lluvia"},
    {"type": "text", "question": "Un día sin risa es un día perdido", "answer": "luces de la ciudad"},
    {"type": "text", "question": "El amor significa no tener que decir lo siento", "answer": "historia de amor"},
    {"type": "text", "question": "Los hombres y mujeres no pueden ser amigos", "answer": "cuando harry encontro a sally"},
    {"type": "text", "question": "Gran error. Enorme.", "answer": "mujer bonita"},
    {"type": "text", "question": "El amor está en todas partes", "answer": "realmente amor"},
    {"type": "text", "question": "Los tiempos son difíciles para los soñadores", "answer": "amelie"},

    # =========================
    # 😱 TERROR (MIX)
    # =========================
    {"type": "image", "question": "https://media.tenor.com/53mmk5yopQkAAAAM/the-shining-creepy.gif", "answer": "el resplandor"},  # Here’s Johnny
    {"type": "text", "question": "El poder de Cristo te obliga", "answer": "el exorcista"},
    {"type": "text", "question": "A veces es mejor estar muerto", "answer": "psicosis"},
    {"type": "image", "question": "https://m.media-amazon.com/images/S/pv-target-images/60b1a6d04f3c275f79a0862369af646667b7e585c753c5de5ca0bdd8af44c350.jpg", "answer": "el aro"},
    {"type": "text", "question": "Veo gente muerta", "answer": "el sexto sentido"},
    {"type": "image", "question": "https://amcnetworks.es/wp-content/uploads/2024/01/SAW.jpg", "answer": "saw"},
    {"type": "image", "question": "https://hips.hearstapps.com/hmg-prod/images/scream-art-6903c970e7ad9.jpg?crop=0.6666666666666667xw:1xh;center,top&resize=1200:*", "answer": "scream"},
    {"type": "image", "question": "https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUydDY0OGgzZ3JteTZ6bmg0aGM0MmtqMDZ2Mjg0cnZ3bGYxdXpnb2Y5ZSZlcD12MV9naWZzX3NlYXJjaCZjdD1n/nlgexSdFTWT9S/giphy.gif", "answer": "halloween"},

    # =========================
    # 🚀 SCI-FI / MONSTRUOS
    # =========================
    {"type": "image", "question": "https://hips.hearstapps.com/hmg-prod/images/alien-romulus-xenomorfo-66bcb22ecc1ba.jpg?crop=1.00xw:0.757xh;0,0.152xh&resize=980:*", "answer": "alien"},
    {"type": "text", "question": "Vamos a necesitar un barco más grande", "answer": "tiburon"},
    {"type": "image", "question": "https://upload.wikimedia.org/wikipedia/commons/6/67/Predator_%282020225730%29.jpg", "answer": "depredador"},

    # =========================
    # 🧟 ZOMBIES
    # =========================
    {"type": "text", "question": "Hora del doble tap", "answer": "zombieland"},
    {"type": "text", "question": "El mundo está en guerra", "answer": "guerra mundial z"},

    # =========================
    # 💥 ACCIÓN (MIX)
    # =========================
    {"type": "image", "question": "https://media.revistagq.com/photos/5dbab1e1d19dec0008a41e77/16:9/w_1280,c_limit/terminator%20portada.jpg", "answer": "terminator"},
    {"type": "text", "question": "Hasta la vista, baby", "answer": "terminator 2"},
    {"type": "image", "question": "https://media.wired.com/photos/5c9ba67d1e34481170ef2bcd/1%3A1/w_1561%2Ch_1561%2Cc_limit/Culture_Matrix_RedPillBluePill-1047403844.jpg", "answer": "matrix"},
    {"type": "image", "question": "https://i.ebayimg.com/images/g/~S0AAOSwEW9aVY8J/s-l1200.jpg", "answer": "el caballero oscuro"},
    {"type": "image", "question": "https://wallpapers.com/images/featured/imagenes-de-john-wick-jeaidqurrfx52d3u.jpg", "answer": "john wick"},
    {"type": "text", "question": "La familia es lo primero", "answer": "rapidos y furiosos 5"},

    # =========================
    # 😎 EXTRA
    # =========================
    {"type": "text", "question": "Somos los chicos malos", "answer": "bad boys"},
    {"type": "text", "question": "Nadie se queda atrás", "answer": "los indestructibles 4"},

    # =========================
    # 🧙 BONUS
    # =========================
    {"type": "image", "question": "https://m.media-amazon.com/images/I/61YJR4MAl1L._AC_UY1000_.jpg", "answer": "harry potter"},
]

# -----------------------------
# UTILIDADES
# -----------------------------
def normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text)\
        .encode("ascii", "ignore")\
        .decode()\
        .lower()\
        .strip()

# -----------------------------
# POOL (NO REPETIR)
# -----------------------------
def get_questions_pool():
    """Devuelve una copia de las preguntas mezcladas"""
    pool = QUESTIONS.copy()
    random.shuffle(pool)
    return pool

def get_next_question(pool: list):
    if not pool:
        return None
    return pool.pop(0)

# -----------------------------
# VALIDACIÓN
# -----------------------------
def is_correct_answer(user_answer: str, correct_answer: str) -> bool:
    return normalize(user_answer) == normalize(correct_answer)