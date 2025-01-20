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
        
        # Convert to RGB (3 channels)
        image = image.convert('RGB')
        
        # Resize to consistent size
        image = image.resize(self.image_size)
        
        # Convert to numpy array and normalize
        img_array = np.array(image)
        img_array = img_array.astype('float32') / 255.0
        
        return img_array
    
    def create_model(self):
        """Create the multi-output model using advanced techniques"""
        # Input layer (3 channels for RGB)
        inputs = tf.keras.layers.Input(shape=(*self.image_size, 3))
        
        # Enhanced data augmentation
        x = tf.keras.layers.RandomRotation(0.3)(inputs)
        x = tf.keras.layers.RandomZoom(0.2)(x)
        x = tf.keras.layers.RandomTranslation(0.2, 0.2)(x)
        x = tf.keras.layers.RandomContrast(0.3)(x)
        
        # Initial convolution block with stronger regularization
        x = tf.keras.layers.Conv2D(32, 3, padding='same', kernel_regularizer=tf.keras.regularizers.l2(0.01))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.SpatialDropout2D(0.2)(x)
        x = tf.keras.layers.MaxPooling2D()(x)
        
        # Simplified architecture with stronger regularization
        for filters in [64, 128]:
            x = tf.keras.layers.Conv2D(filters, 3, padding='same', 
                                     kernel_regularizer=tf.keras.regularizers.l2(0.01))(x)
            x = tf.keras.layers.BatchNormalization()(x)
            x = tf.keras.layers.Activation('relu')(x)
            x = tf.keras.layers.SpatialDropout2D(0.3)(x)
            x = tf.keras.layers.MaxPooling2D()(x)
        
        # Global pooling and feature extraction
        x = tf.keras.layers.GlobalAveragePooling2D()(x)
        
        # Dense layers with strong regularization
        x = tf.keras.layers.Dense(256, kernel_regularizer=tf.keras.regularizers.l2(0.01))(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation('relu')(x)
        x = tf.keras.layers.Dropout(0.5)(x)
        
        # Create output branches with adjusted weights
        outputs = []
        loss_dict = {}
        metrics_dict = {}
        loss_weights_dict = {}
        
        sorted_steps = sorted(self.typing_steps.values(), key=lambda x: x.order)
        for step in sorted_steps:
            output_name = f'output_{step.id}'
            
            # Specific branch for each output
            branch = tf.keras.layers.Dense(128, kernel_regularizer=tf.keras.regularizers.l2(0.01))(x)
            branch = tf.keras.layers.BatchNormalization()(branch)
            branch = tf.keras.layers.Activation('relu')(branch)
            branch = tf.keras.layers.Dropout(0.4)(branch)
            
            # Output layer
            output = tf.keras.layers.Dense(
                len(step.options),
                activation='softmax',
                name=output_name
            )(branch)
            outputs.append(output)
            
            # Adjust loss weights based on step type
            weight = 2.0 if step.id == 'cutout' else 1.0
            loss_dict[output_name] = 'sparse_categorical_crossentropy'
            metrics_dict[output_name] = 'accuracy'
            loss_weights_dict[output_name] = weight / np.sqrt(len(step.options))
        
        # Create and compile model with custom optimizer
        self.model = tf.keras.Model(inputs=inputs, outputs=outputs)
        
        # Custom learning rate schedule
        initial_learning_rate = 0.001
        decay_steps = 1000
        decay_rate = 0.9
        learning_rate_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
            initial_learning_rate, decay_steps, decay_rate
        )
        
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(
                learning_rate=learning_rate_schedule,
                weight_decay=1e-4
            ),
            loss=loss_dict,
            metrics=metrics_dict,
            loss_weights=loss_weights_dict
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
                
                # For each file, we'll create multiple training examples if there are multiple cutouts
                cutout_index = 1
                while True:
                    X.append(img_array)
                    
                    # Process labels for each step
                    sorted_steps = sorted(self.typing_steps.items(), key=lambda x: x[1].order)
                    for step_idx, (step_id, step) in enumerate(sorted_steps):
                        if step_id == "cutout":
                            # Get the appropriate cutout value based on index
                            cutout_key = f"cutout_{cutout_index}" if cutout_index > 1 else "cutout"
                            current_value = data['results'].get(cutout_key, step.options[0]['value'])
                        elif step_id == "additional_cutout":
                            # Get the appropriate additional cutout value
                            additional_key = f"additional_cutout_{cutout_index}"
                            current_value = data['results'].get(additional_key, "Nee")
                        else:
                            # For other steps, get value normally
                            current_value = data['results'].get(step_id, step.options[0]['value'])
                        
                        # Find index of the value in options
                        option_values = [opt['value'] for opt in sorted(step.options, key=lambda x: x['order'])]
                        label_idx = option_values.index(current_value)
                        Y[step_idx].append(label_idx)
                    
                    # Check if we should process another cutout
                    additional_key = f"additional_cutout_{cutout_index}"
                    if data['results'].get(additional_key) == "Ja":
                        cutout_index += 1
                    else:
                        break
            
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                continue
        
        # Convert to numpy arrays
        X = np.array(X)
        Y = [np.array(y) for y in Y]
        
        return X, Y
    
    def train(self, X, Y, validation_split=0.2, epochs=100, batch_size=32):
        """Train the model with enhanced techniques"""
        if self.model is None:
            self.create_model()
        
        # Callbacks with adjusted parameters
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=20,
                restore_best_weights=True,
                mode='min'
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.8,
                patience=10,
                min_lr=0.00001,
                mode='min',
                verbose=1
            ),
            tf.keras.callbacks.ModelCheckpoint(
                'best_model.keras',
                monitor='val_loss',
                save_best_only=True,
                mode='min'
            )
        ]
        
        # Train with larger batch size
        history = self.model.fit(
            X,
            Y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=min(batch_size * 2, len(X)),  # Increased batch size
            callbacks=callbacks,
            verbose=1
        )
        
        # Load best weights
        self.model.load_weights('best_model.keras')
        
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
            
            cutout_index = 1
            for step_idx, (step_id, step) in enumerate(sorted_steps):
                # Get predicted class index
                pred_probs = predictions[step_idx][0]
                pred_idx = np.argmax(pred_probs)
                
                # Get corresponding option value
                option_values = [opt['value'] for opt in sorted(step.options, key=lambda x: x['order'])]
                selected_value = option_values[pred_idx]
                
                if step_id == "cutout":
                    # For cutouts, use indexed keys
                    cutout_key = f"cutout_{cutout_index}" if cutout_index > 1 else "cutout"
                    results[cutout_key] = selected_value
                    print(f"Debug: Step {step.name} {cutout_index} - Predicted {selected_value} (confidence: {pred_probs[pred_idx]:.2%})")
                elif step_id == "additional_cutout":
                    # For additional cutout question, use indexed keys
                    additional_key = f"additional_cutout_{cutout_index}"
                    results[additional_key] = selected_value
                    print(f"Debug: Step {step.name} {cutout_index} - Predicted {selected_value} (confidence: {pred_probs[pred_idx]:.2%})")
                    
                    # If we predict another cutout, increment the index
                    if selected_value == "Ja":
                        cutout_index += 1
                else:
                    # For other steps, use normal keys
                    results[step_id] = selected_value
                    print(f"Debug: Step {step.name} - Predicted {selected_value} (confidence: {pred_probs[pred_idx]:.2%})")
            
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