import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path
import os

# Apagamos los mensajes de log molestos de TensorFlow en la consola
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Buscamos tu modelo recién entrenado
DIR_ACTUAL = Path(__file__).parent
MODEL_DIR = DIR_ACTUAL / "rnn-keras-autocomplete"

try:
    model = tf.keras.models.load_model(MODEL_DIR / "model.keras")
    meta = json.loads((MODEL_DIR / "meta.json").read_text(encoding="utf-8"))
    
    BLOCK_SIZE = meta["block_size"]
    chars = meta["chars"]
    stoi = {ch: i for i, ch in enumerate(chars)}
    itos = {i: ch for i, ch in enumerate(chars)}
except Exception as e:
    print(json.dumps({"error": f"No jaló el modelo: {str(e)}"}), flush=True)
    sys.exit(1)

def encode(s):
    return [stoi[c] for c in s if c in stoi]

def decode(ids):
    return "".join(itos[i] for i in ids)

def complete(prompt, max_new, temperature):
    ids = encode(prompt)
    if not ids: ids = [0]
    rng = np.random.default_rng(42)

    for _ in range(max_new):
        x = np.array(ids[-BLOCK_SIZE:], dtype=np.int64)
        if x.shape[0] < BLOCK_SIZE:
            pad = np.full(BLOCK_SIZE - x.shape[0], ids[0], dtype=np.int64)
            x = np.concatenate([pad, x])

        logits = model(x.reshape(1, BLOCK_SIZE), training=False).numpy()[0, -1, :]
        logits = logits / max(temperature, 1e-6)
        logits = logits - logits.max()
        probs = np.exp(logits)
        probs = probs / probs.sum()
        ids.append(int(rng.choice(len(probs), p=probs)))

    return decode(ids)

# Bucle infinito para escuchar los comandos de VS Code
for line in sys.stdin:
    try:
        req = json.loads(line)
        msg_id = req.get("_id")
        method = req.get("method")

        if method == "complete":
            prefix = req.get("prefix", "")
            max_new = req.get("max_new", 60)
            temp = req.get("temperature", 0.75)
            
            texto_generado = complete(prefix, max_new, temp)
            print(json.dumps({"_id": msg_id, "ok": True, "text": texto_generado}), flush=True)

        elif method == "suggest":
            prefix = req.get("prefix", "")
            n = req.get("n", 5)
            
            sugerencias = []
            for i in range(n):
                texto = complete(prefix, 60, 0.65 + 0.05 * i)
                linea = (prefix + texto[len(prefix):].split("\n")[0])[:100]
                if linea not in sugerencias:
                    sugerencias.append(linea)
            
            print(json.dumps({"_id": msg_id, "ok": True, "items": sugerencias}), flush=True)

    except Exception as e:
        if "msg_id" in locals():
            print(json.dumps({"_id": msg_id, "ok": False, "error": str(e)}), flush=True)