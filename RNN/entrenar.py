import json
from pathlib import Path
import numpy as np
import tensorflow as tf


tf.keras.utils.set_random_seed(42)



ruta_dataset = Path("funciones.c")
if not ruta_dataset.is_file():
    raise FileNotFoundError("no se encontro funciones.c")

CORPUS = ruta_dataset.read_text(encoding="utf-8")
print(f"Corpus cargado: {len(CORPUS)} caracteres a entrenar.")



# prp trad
chars = sorted(set(CORPUS))
stoi = {ch: i for i, ch in enumerate(chars)}
VOCAB_SIZE = len(chars)

def encode(s: str) -> list[int]:
    return [stoi[c] for c in s if c in stoi]

SEQ = np.array(encode(CORPUS), dtype=np.int64)




#arm blc 
BLOCK_SIZE = 64
X_rows, Y_rows = [], []
for i in range(0, len(SEQ) - BLOCK_SIZE):
    X_rows.append(SEQ[i : i + BLOCK_SIZE])
    Y_rows.append(SEQ[i + 1 : i + 1 + BLOCK_SIZE])
X = np.stack(X_rows)
Y = np.stack(Y_rows)




EMBED_DIM = 64

HIDDEN = 128

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(BLOCK_SIZE,)),
    tf.keras.layers.Embedding(VOCAB_SIZE, EMBED_DIM),
    tf.keras.layers.SimpleRNN(HIDDEN, activation="tanh", return_sequences=True),
    tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(VOCAB_SIZE)),
])


model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
)




print("Arrancando el entrenamiento, dale un minutito...")
model.fit(X, Y, epochs=120, batch_size=32, verbose=1)



DEPLOY_DIR = Path("rnn-keras-autocomplete")
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

model.save(DEPLOY_DIR / "model.keras")
(DEPLOY_DIR / "meta.json").write_text(
    json.dumps({"block_size": BLOCK_SIZE, "chars": chars}, ensure_ascii=False),
    encoding="utf-8"
)

print(f"\nLISTO El modelo se guardó en: {DEPLOY_DIR.resolve()}")