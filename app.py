import os
from dotenv import load_dotenv
load_dotenv()
import re
import streamlit as st

st.set_page_config(page_title="Humanizador Académico", page_icon="✍️", layout="wide")

st.title("✍️ Humanizador Académico")
st.caption("MVP para naturalizar textos preservando significado, citas y terminología técnica.")

DEFAULT_SYSTEM = """Eres un editor académico. Tu tarea es mejorar la naturalidad y claridad del texto sin cambiar su significado.

REGLAS OBLIGATORIAS:
1. No inventes autores, años, referencias, DOI, datos, resultados ni ejemplos.
2. Conserva exactamente cifras, porcentajes, nombres propios, leyes, normas, variables, dimensiones,
   indicadores, instrumentos, nombres de instituciones y términos técnicos.
3. Conserva las citas APA y su información bibliográfica.
4. No agregues ideas nuevas ni elimines ideas sustantivas.
5. Reduce repeticiones, fórmulas genéricas y estructuras sintácticas monótonas.
6. Mantén un tono académico natural, propio de un estudiante de maestría.
7. Evita lenguaje excesivamente sofisticado o artificial.
8. Prioriza cambios puntuales de estructura, conectores, precisión y fluidez.
9. Si una afirmación parece insuficientemente sustentada, no la completes: mantenla y márcala como [REVISAR].
10. Devuelve primero el texto revisado y luego una lista breve de cambios realizados.
"""

def protect_tokens(text):
    tokens = []
    patterns = [
        r'https?://\S+',
        r'\bdoi:\s*\S+',
        r'\b\d+(?:[.,]\d+)?\s*%',
        r'\b(?:ISO|D\.S\.|D\.Leg\.|Ley)\s*[\w./:-]+',
        r'\([^()\n]{2,100}?\b(?:19|20)\d{2}\)',
    ]
    for pattern in patterns:
        for match in list(re.finditer(pattern, text, flags=re.I)):
            token = f"[[PROTEGIDO_{len(tokens)}]]"
            tokens.append((token, match.group(0)))
            text = text.replace(match.group(0), token, 1)
    return text, tokens

def restore_tokens(text, tokens):
    for token, original in tokens:
        text = text.replace(token, original)
    return text

def analyze(text):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    words = re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ'-]+\b", text, flags=re.UNICODE)
    connectors = re.findall(
        r"\b(en este sentido|asimismo|por otra parte|de igual manera|en ese sentido|por tanto|por consiguiente|sin embargo|además|finalmente)\b",
        text, flags=re.I
    )
    generic = re.findall(
        r"\b(cabe señalar que|es importante mencionar que|la presente investigación|en ese sentido|de acuerdo con lo anteriormente mencionado)\b",
        text, flags=re.I
    )
    avg = round(len(words) / len(sentences), 1) if sentences else 0
    return {
        "Palabras": len(words),
        "Oraciones": len(sentences),
        "Promedio palabras/oración": avg,
        "Conectores detectados": len(connectors),
        "Fórmulas repetitivas detectadas": len(generic),
    }

def local_rewrite(text):
    # Fallback transparente: edición mecánica mínima, sin afirmar que es una IA.
    replacements = [
        (r"\bla presente investigación tiene como objetivo\b", "el estudio busca"),
        (r"\ben ese sentido,\s*", "en este contexto, "),
        (r"\bcabe señalar que\s*", ""),
        (r"\bes importante mencionar que\s*", ""),
        (r"\bde acuerdo con lo anteriormente mencionado,\s*", "a partir de lo señalado, "),
    ]
    out = text
    for pattern, repl in replacements:
        out = re.sub(pattern, repl, out, flags=re.I)
    return out.strip()

def call_gemini(text, style, intensity):
    try:
        import google.generativeai as genai
    except Exception as e:
        return None, "google.generativeai."

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None, "No se encontró GEMINI_API_KEY. Puedes usar el modo local o configurar una clave."

    genai.configure(api_key=key)
    protected, tokens = protect_tokens(text)

    user_prompt = f"""Perfil: {style}
Intensidad de edición: {intensity}

Texto a revisar:
---INICIO---
{protected}
---FIN---

Reescribe respetando estrictamente las reglas. Devuelve:
1) TEXTO REVISADO
2) CAMBIOS REALIZADOS
3) ELEMENTOS QUE REQUIEREN REVISIÓN DEL AUTOR (solo si corresponde).
"""
    try:
      model = genai.GenerativeModel("gemini-3.8-flash", system_instruction=DEFAULT_SYSTEM)
      response=model.generate_content(user_prompt) 
   
      result = response.text
      result = restore_tokens(result, tokens)
      return result, None
    except Exception as e:
      return None, f"Error del proveedor de IA: {e}"

with st.sidebar:
    st.header("Configuración")
    style = st.selectbox(
        "Perfil",
        ["Académico natural", "Tesis de maestría", "Formal institucional", "Claro y directo"]
    )
    intensity = st.select_slider(
        "Intensidad de edición",
        options=["Puntual", "Moderada", "Alta"],
        value="Puntual"
    )
    engine = st.radio("Motor", ["IA (API)", "Local (sin API)"])
    st.divider()
    st.info("El modo local aplica reglas limitadas. El modo IA permite una reformulación contextual.")

left, right = st.columns(2)

with left:
    st.subheader("Texto original")
    text = st.text_area(
        "Pega aquí tu texto",
        height=430,
        placeholder="Pega un párrafo o varios párrafos de tu tesis..."
    )

    if text:
        metrics = analyze(text)
        st.write("**Análisis preliminar**")
        st.json(metrics)

with right:
    st.subheader("Texto revisado")
    result_placeholder = st.empty()

    if st.button("✨ Analizar y humanizar", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("Ingresa primero un texto.")
        else:
            with st.spinner("Revisando el texto..."):
                if engine == "IA (API)":
                    result, error = call_gemini(text, style, intensity)
                    if error:
                        st.error(error)
                        result = None
                else:
                    result = local_rewrite(text)

                if result:
                    result_placeholder.text_area(
                        "Resultado",
                        value=result,
                        height=430,
                        key="resultado"
                    )

st.divider()
st.subheader("Criterio de uso")
st.write(
    "La aplicación está diseñada para editar y naturalizar la redacción, no para garantizar "
    "resultados frente a detectores de IA. El autor debe revisar el resultado y conservar la "
    "responsabilidad sobre sus afirmaciones, fuentes y conclusiones.")
