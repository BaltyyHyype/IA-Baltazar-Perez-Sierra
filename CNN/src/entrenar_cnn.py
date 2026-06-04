import tensorflow as tf
from tensorflow.keras import layers, models
import os




BATCH_SIZE = 16       

IMG_SIZE = (96, 96)   

EPOCHS = 25           

DATASET_DIR = "dataset" 




# 80
print("Cargando imágenes de entrenamiento...")
train_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="training",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE
)


# 20
print("Cargando imágenes de validación...")
val_dataset = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=0.2,
    subset="validation",
    seed=123,
    image_size=IMG_SIZE,
    batch_size=BATCH_SIZE
)


# listas
clases = train_dataset.class_names
print(f"\nClases detectadas para entrenar: {clases}")




AUTOTUNE = tf.data.AUTOTUNE
train_dataset = train_dataset.cache().shuffle(1000).prefetch(buffer_size=AUTOTUNE)
val_dataset = val_dataset.cache().prefetch(buffer_size=AUTOTUNE)



data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal", input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3)),
    layers.RandomTranslation(height_factor=0.1, width_factor=0.1),              
    layers.RandomRotation(0.1),                                                 
    layers.RandomZoom(0.1),                                                     
    layers.RandomContrast(0.3),                                                 
    layers.RandomBrightness(0.3),                                               
])


modelo = models.Sequential([


    data_augmentation,
    layers.Rescaling(1./255),
    layers.GaussianNoise(0.1), 
    

    layers.Conv2D(32, (3, 3), padding='same'),
    layers.LeakyReLU(alpha=0.1),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), padding='same'),
    layers.LeakyReLU(alpha=0.1),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(128, (3, 3), padding='same'),
    layers.LeakyReLU(alpha=0.1),
    layers.MaxPooling2D((2, 2)),
    
    
    
    layers.Flatten(), 

    layers.Dense(128), # info de las capas x pesos
    
    layers.LeakyReLU(alpha=0.1),
    
    
    layers.Dropout(0.5), 
    layers.Dense(len(clases), activation='softmax') 
])




modelo.compile(optimizer='adam',
               loss='sparse_categorical_crossentropy',
               metrics=['accuracy'])

modelo.summary()



freno_automatico = tf.keras.callbacks.EarlyStopping(
    monitor='val_loss', 
    patience=4, 
    restore_best_weights=True
)


if not os.path.exists("modelos"):
    os.makedirs("modelos")

guardado_seguro = tf.keras.callbacks.ModelCheckpoint(
    filepath="modelos/modelo_animales.keras",
    monitor='val_accuracy',
    save_best_only=True,
    verbose=1
)

print("\nIniciando el entrenamiento del modelo...")
history = modelo.fit(
    train_dataset,
    validation_data=val_dataset,
    epochs=EPOCHS,
    callbacks=[freno_automatico, guardado_seguro] 
)

print("\n¡Entrenamiento completado exitosamente y modelo guardado de forma segura")