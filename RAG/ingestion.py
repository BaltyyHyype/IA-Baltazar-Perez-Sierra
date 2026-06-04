import os
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 

from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

DATA_PATH = "corpus" 
DB_PATH = "./db"

print("1. Cargando documentos PDF con PyMuPDF...")

loader = DirectoryLoader(DATA_PATH, glob="**/*.pdf", loader_cls=PyMuPDFLoader)
documentos = loader.load()
print(f"   Se cargaron {len(documentos)} páginas/documentos.")

print("2. Partiendo el texto en fragmentos (Chunks)...")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_documents(documentos)

print("3. Generando Embeddings Multilingües...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

print("4. Guardando en la Base de Datos...")
vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=DB_PATH)

print("¡Base de datos creada exitosamente en " + DB_PATH + "!")