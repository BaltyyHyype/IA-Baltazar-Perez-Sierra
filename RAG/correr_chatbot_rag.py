import os
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama

print("Cargando motor RAG y Base de Datos...")

ruta_bd = "./db" 

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
vectorstore = Chroma(persist_directory=ruta_bd, embedding_function=embeddings)

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

print("Despertando al Tutor en Ollama...")
llm = Ollama(
    model="llama3.2",
    temperature=0.1,       
    num_predict=1024,
    stop=["Usuario:", "###", "\n\n\n", "Usuario,"]
)



print("SISTEMA DE ANÁLISIS LISTO.")
print("Escribe 'salir', 'exit' o 'quit' para terminar.")


memoria_chat = []

while True:
    pregunta = input("\nTú: ")
    
    if pregunta.lower() in ['salir', 'exit', 'quit']:
        print("\nApagando sistema... ¡Hasta la próxima!")
        break

    if not pregunta.strip():
        continue

    print(f"   Analizando dataset")
    docs = retriever.invoke(pregunta)
    contexto = "\n\n".join([f"ARCHIVO: {os.path.basename(doc.metadata.get('source', 'desconocido'))}\nTEXTO: {doc.page_content}" for doc in docs])    

    historial_texto = "\n".join(memoria_chat[-2:]) if memoria_chat else "Ninguno (esta es la primera pregunta)."


    prompt_magico = f"""### Rol:
Analista de Datos de Seguridad Pública.

### Instrucciones:
- Analiza la pregunta del usuario consultando el contexto proporcionado.
- Si hay datos contradictorios entre documentos, señálalos.
- **Formato obligatorio de salida:**
  [ANÁLISIS]: (Tu respuesta académica técnica aquí)
  [CITA]: (Indica el nombre del archivo sin la extension)  
  [NIVEL DE CERTEZA]: (Alta/Media/Baja)

### Contexto:
{contexto}

### Historial de Chat:
{historial_texto}

### Pregunta Actual:
{pregunta}

### Respuesta:
"""
    
    print("\nCHATBOT: ", end="")
    respuesta_completa = llm.invoke(prompt_magico)
    print(respuesta_completa)
        
    print("\n" + "-" * 60)

    # 5. Guardamos en memoria
    interaccion = f"Usuario: {pregunta}\nTutor: {respuesta_completa}"
    memoria_chat.append(interaccion)