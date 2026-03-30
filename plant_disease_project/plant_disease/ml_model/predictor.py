"""
plant_disease/ml_model/predictor.py
------------------------------------
Handles loading TensorFlow/Keras models and running predictions.
Two-stage pipeline:
1. Leaf detector: Validates if image is a leaf
2. Disease classifier: Identifies disease if leaf is confirmed
"""

import os
import numpy as np
from django.conf import settings

MODEL_READY = True
LEAF_MODEL_READY = True

IMAGE_SIZE = (224, 224)

CLASS_NAMES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy"
]

LEAF_CLASS_NAMES = ["Leaf", "Not a leaf"]
LEAF_CONFIDENCE_THRESHOLD = 0.70

_model = None
_leaf_model = None


def _get_tf():
    try:
        import tensorflow as tf
        return tf
    except Exception as exc:
        raise RuntimeError(
            "TensorFlow import failed. Ensure tensorflow is installed."
        ) from exc


def load_model():
    """Load and cache the disease classification model."""
    global _model
    if _model is not None:
        return _model

    model_path = str(settings.ML_MODEL_PATH)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at: {model_path}"
        )

    tf = _get_tf()
    _model = tf.keras.models.load_model(model_path)
    return _model


def load_leaf_model():
    """Load and cache the leaf detection model."""
    global _leaf_model
    if _leaf_model is not None:
        return _leaf_model

    model_path = str(settings.LEAF_MODEL_PATH)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Leaf model file not found at: {model_path}"
        )

    tf = _get_tf()
    _leaf_model = tf.keras.models.load_model(model_path)
    return _leaf_model


def predict_leaf(image_path):
    """
    Run leaf/not-leaf classification.
    
    Returns dict with is_leaf boolean and metadata.
    """
    if not LEAF_MODEL_READY:
        return {
            'is_leaf': False,
            'leaf_label': 'Leaf model not ready',
            'leaf_confidence': 0.0,
            'leaf_scores': {name: 0.0 for name in LEAF_CLASS_NAMES},
            'status': 'stub',
            'error': 'Leaf model not ready'
        }

    try:
        leaf_model = load_leaf_model()
    except FileNotFoundError:
        return {
            'is_leaf': False,
            'leaf_label': 'Leaf model missing',
            'leaf_confidence': 0.0,
            'leaf_scores': {name: 0.0 for name in LEAF_CLASS_NAMES},
            'status': 'stub',
            'error': 'Leaf model file not found'
        }

    try:
        img_array = preprocess_image(image_path)
        leaf_preds = leaf_model.predict(img_array, verbose=0)[0]

        if len(leaf_preds) != len(LEAF_CLASS_NAMES):
            raise ValueError(
                f"Leaf model output ({len(leaf_preds)}) doesn't match expected classes ({len(LEAF_CLASS_NAMES)})"
            )

        leaf_top_idx = int(np.argmax(leaf_preds))
        leaf_label = LEAF_CLASS_NAMES[leaf_top_idx]
        leaf_confidence = float(leaf_preds[leaf_top_idx])
        leaf_scores = {LEAF_CLASS_NAMES[i]: float(leaf_preds[i]) for i in range(len(LEAF_CLASS_NAMES))}

        is_leaf = (leaf_top_idx == 0 and leaf_confidence >= LEAF_CONFIDENCE_THRESHOLD)

        return {
            'is_leaf': is_leaf,
            'leaf_label': leaf_label,
            'leaf_confidence': leaf_confidence,
            'leaf_scores': leaf_scores,
            'status': 'completed',
        }
    except Exception as e:
        return {
            'is_leaf': False,
            'leaf_label': f'Error: {str(e)}',
            'leaf_confidence': 0.0,
            'leaf_scores': {name: 0.0 for name in LEAF_CLASS_NAMES},
            'status': 'stub',
            'error': f'Leaf prediction failed: {str(e)}'
        }


def preprocess_image(image_path):
    """
    Load and preprocess an image for model input.
    
    Returns:
        np.ndarray: Image with shape (1, H, W, 3), normalized to [0, 1]
    """
    tf = _get_tf()
    img = tf.keras.utils.load_img(image_path, target_size=IMAGE_SIZE)
    img_array = tf.keras.utils.img_to_array(img)
    img_array = img_array / 255.0
    return np.expand_dims(img_array, axis=0)


def predict(image_path):
    """
    Two-stage prediction pipeline:
    1. Validate image is a leaf
    2. If leaf, classify disease
    
    Returns:
        dict: Prediction results with disease/leaf classification
    """
    if not MODEL_READY:
        return {
            'disease_name': 'Model not ready yet',
            'confidence': 0.0,
            'all_scores': {name: 0.0 for name in CLASS_NAMES},
            'status': 'stub',
        }

    leaf_result = predict_leaf(image_path)

    if leaf_result.get('status') == 'stub':
        return {
            'disease_name': 'Not a leaf',
            'confidence': 0.0,
            'all_scores': {name: 0.0 for name in CLASS_NAMES},
            'status': 'completed',
            'is_leaf': False,
            'leaf_label': leaf_result.get('leaf_label', 'Unknown'),
            'leaf_confidence': leaf_result.get('leaf_confidence', 0.0),
            'leaf_error': leaf_result.get('error'),
        }

    if not leaf_result.get('is_leaf', False):
        return {
            'disease_name': 'Not a leaf',
            'confidence': leaf_result.get('leaf_confidence', 0.0),
            'all_scores': leaf_result.get('leaf_scores', {}),
            'status': 'completed',
            'is_leaf': False,
            'leaf_label': leaf_result.get('leaf_label'),
            'leaf_confidence': leaf_result.get('leaf_confidence'),
        }

    model = load_model()
    img_array = preprocess_image(image_path)
    predictions = model.predict(img_array)[0]

    if len(predictions) != len(CLASS_NAMES):
        raise ValueError(
            f"Model predictions ({len(predictions)}) don't match CLASS_NAMES ({len(CLASS_NAMES)}). "
            "Update CLASS_NAMES to match your model's output classes."
        )

    top_idx = int(np.argmax(predictions))
    confidence = float(predictions[top_idx])
    all_scores = {CLASS_NAMES[i]: float(predictions[i]) for i in range(len(CLASS_NAMES))}

    return {
        'disease_name': CLASS_NAMES[top_idx],
        'confidence': confidence,
        'all_scores': all_scores,
        'status': 'completed',
    }
