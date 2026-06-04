import tensorflow as tf
import numpy as np
import cv2
import gradio as gr
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

CLASES = ['Arañas', 'Ballenas', 'Changos', 'Pájaros', 'Ranas']
RUTA_MODELO = "modelos/modelo_animales.keras"

print("Cargando modelo...")
try:
    modelo = tf.keras.models.load_model(RUTA_MODELO)
except Exception as e:
    print(f"Error al cargar el modelo: {e}")
    exit()


def clasificar_animal(imagen):
    if imagen is None:
        return {"Sube una imagen": 0.0}

    img_redimensionada = cv2.resize(imagen, (96, 96))
    img_array = np.expand_dims(img_redimensionada, axis=0)
    predicciones = modelo.predict(img_array, verbose=0)[0]
    resultados = {CLASES[i]: float(predicciones[i]) for i in range(len(CLASES))}
    
    return resultados




print("Iniciando aplicación web con diseño personalizado...")


with gr.Blocks(theme=gr.themes.Default(primary_hue="teal"), title="Detección de Especies") as interfaz:
    

    gr.Markdown(
        """
        # Detección de Especies CNN
        Selecciona o arrastra una fotografía para clasificar el animal correspondiente.
        """
    )
    

    with gr.Row():
        

        with gr.Column(scale=1):
            input_img = gr.Image(label="Imagen de entrada")

            btn_clasificar = gr.Button("⚡ Analizar Especie", variant="primary")
            

        with gr.Column(scale=1):
            output_lbl = gr.Label(num_top_classes=5, label="Resultados de la red")



    btn_clasificar.click(
        fn=clasificar_animal, 
        inputs=input_img, 
        outputs=output_lbl
    )
    

    input_img.change(
        fn=clasificar_animal, 
        inputs=input_img, 
        outputs=output_lbl
    )


if __name__ == "__main__":
    interfaz.launch(share=False)