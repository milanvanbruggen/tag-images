import tensorflow as tf
import numpy as np
from PIL import Image
import io
from cairosvg import svg2png
import cv2
import os

class SVGTypingModel:
    def __init__(self, typing_steps, image_size=(224, 224)):
        self.typing_steps = typing_steps
        self.image_size = image_size
        self.model = None
    
    def convert_svg_to_image(self, svg_content):
        """Convert SVG content to a normalized image array"""
        # Convert SVG to PNG
        png_data = svg2png(bytestring=svg_content)
        
        # Convert PNG to PIL Image
        image = Image.open(io.BytesIO(png_data))
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Resize to consistent size
        image = image.resize(self.image_size)
        
        # Convert to numpy array and normalize
        img_array = np.array(image)
        img_array = img_array.astype('float32') / 255.0
        
        # Add channel dimension
        img_array = np.expand_dims(img_array, axis=-1)
        
        return img_array
    
    def create_model(self):
        """Create the multi-output model"""
        # Input layer
        inputs = tf.keras.layers.Input(shape=(*self.image_size, 1))
        
        # Convolutional base (using ResNet-like blocks)
        x = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        
        # First ResNet block
        shortcut = x
        x = tf.keras.layers.Conv2D(32, 3, padding='same', activation='relu')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Conv2D(32, 3, padding='same')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Add()([shortcut, x])
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.MaxPooling2D()(x)
        
        # Second ResNet block
        shortcut = tf.keras.layers.Conv2D(64, 1, padding='same')(x)
        x = tf.keras.layers.Conv2D(64, 3, padding='same', activation='relu')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Conv2D(64, 3, padding='same')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Add()([shortcut, x])
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.MaxPooling2D()(x)
        
        # Global features
        x = tf.keras.layers.GlobalAveragePooling2D()(x)
        x = tf.keras.layers.Dense(256, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.01))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dropout(0.5)(x)
        
        # Create output branches for each typing step
        outputs = []
        for step in sorted(self.typing_steps.values(), key=lambda x: x.order):
            branch = tf.keras.layers.Dense(128, activation='relu')(x)
            branch = tf.keras.layers.BatchNormalization()(branch)
            branch = tf.keras.layers.Dropout(0.3)(branch)
            outputs.append(tf.keras.layers.Dense(
                len(step.options),
                activation='softmax',
                name=f'output_{step.id}'
            )(branch))
        
        # Create model
        self.model = tf.keras.Model(inputs=inputs, outputs=outputs)
        
        # Compile model with metrics for each output
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss=['sparse_categorical_crossentropy' for _ in outputs],
            metrics=[['accuracy'] for _ in outputs],
            loss_weights=[1.0 for _ in outputs]  # Equal weight for all outputs
        )
        
        return self.model
    
    def prepare_data(self, typed_files):
        """Prepare training data from typed files"""
        X = []  # Images
        Y = []  # Labels for each step
        
        # Initialize Y lists for each step
        for _ in self.typing_steps:
            Y.append([])
        
        # Process each file
        for filename, data in typed_files.items():
            try:
                # Read and convert SVG
                with open(filename, 'r') as f:
                    svg_content = f.read()
                img_array = self.convert_svg_to_image(svg_content)
                X.append(img_array)
                
                # Process labels for each step
                sorted_steps = sorted(self.typing_steps.items(), key=lambda x: x[1].order)
                for step_idx, (step_id, step) in enumerate(sorted_steps):
                    # Get current value or default to first option
                    current_value = data['results'].get(step_id, step.options[0]['value'])
                    
                    # Find index of the value in options
                    option_values = [opt['value'] for opt in sorted(step.options, key=lambda x: x['order'])]
                    label_idx = option_values.index(current_value)
                    Y[step_idx].append(label_idx)
            
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        # Convert to numpy arrays
        X = np.array(X)
        Y = [np.array(y) for y in Y]
        
        return X, Y
    
    def train(self, X, Y, validation_split=0.2, epochs=50, batch_size=32):
        """Train the model"""
        if self.model is None:
            self.create_model()
        
        # Train the model
        history = self.model.fit(
            X, Y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=min(batch_size, len(X)),  # Ensure batch size doesn't exceed dataset size
            callbacks=[
                tf.keras.callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True
                ),
                tf.keras.callbacks.ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.2,
                    patience=5,
                    min_lr=0.0001
                )
            ]
        )
        
        return history
    
    def predict(self, svg_content):
        """Predict typing for a new SVG"""
        if self.model is None:
            print("Debug: Model not loaded")
            raise ValueError("Model not trained yet")
        
        try:
            # Convert SVG to image array
            print("Debug: Converting SVG to image")
            img_array = self.convert_svg_to_image(svg_content)
            print(f"Debug: Image array shape: {img_array.shape}")
            
            # Add batch dimension and make prediction
            img_batch = np.expand_dims(img_array, axis=0)
            print(f"Debug: Batch shape: {img_batch.shape}")
            
            print("Debug: Making prediction")
            predictions = self.model.predict(img_batch, verbose=0)
            print(f"Debug: Got {len(predictions)} predictions")
            
            # Process predictions
            results = {}
            sorted_steps = sorted(self.typing_steps.items(), key=lambda x: x[1].order)
            
            for step_idx, (step_id, step) in enumerate(sorted_steps):
                # Get predicted class index
                pred_probs = predictions[step_idx][0]
                pred_idx = np.argmax(pred_probs)
                
                # Get corresponding option value
                option_values = [opt['value'] for opt in sorted(step.options, key=lambda x: x['order'])]
                selected_value = option_values[pred_idx]
                print(f"Debug: Step {step.name} - Predicted {selected_value} (confidence: {pred_probs[pred_idx]:.2%})")
                results[step_id] = selected_value
            
            return results
            
        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}  # Return empty dict on error
    
    def save_model(self, filepath):
        """Save the trained model"""
        if self.model is not None:
            # Remove any extension and add .keras
            filepath = os.path.splitext(filepath)[0] + '.keras'
            print(f"Debug: Saving model to {filepath}")
            self.model.save(filepath)
            print("Debug: Model saved successfully")
    
    def load_model(self, filepath):
        """Load a trained model"""
        print(f"Debug: Loading model from {filepath}")
        self.model = tf.keras.models.load_model(filepath)
        print("Debug: Model loaded successfully") 