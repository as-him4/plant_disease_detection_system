"""
plant_disease/ml_model/predictor.py
------------------------------------
Handles loading TensorFlow/Keras models and running predictions.
Two-stage pipeline:
1. Leaf detector: Validates if image is a leaf
2. Disease classifier: Identifies disease if leaf is confirmed

FIX: preprocess_image now uses ResNet50's preprocess_input instead of /255.0
"""

import os
import numpy as np
from django.conf import settings
from tf_keras.applications.resnet50 import preprocess_input  

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
    "Corn_(maize)__Common_rust",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Litchi_curl_mite",
    "Litchi_healthy",
    "Litchi_leaf_insect_infestation",
    "Litchi_swooty_mould",
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
    "Tejpatta_healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
    "tejpatta_Algal_leaf_spot"
]

LEAF_CLASS_NAMES = ["Leaf", "Not a leaf"]
LEAF_CONFIDENCE_THRESHOLD = 0.70

DISEASE_RECOMMENDATIONS = {
    "Apple___Apple_scab": {
        "treatment": "Apply fungicides like captan or myclobutanil during growing season",
        "prevention": "Remove fallen leaves, prune for air circulation, choose resistant varieties",
        "organic": "Use copper-based fungicides or neem oil applications"
    },
    "Apple___Black_rot": {
        "treatment": "Remove mummified fruits, apply fungicides at petal fall",
        "prevention": "Prune dead branches, remove infected fruits, maintain tree vigor",
        "organic": "Copper sprays during dormant season, remove all infected material"
    },
    "Apple___Cedar_apple_rust": {
        "treatment": "Apply fungicides every 7-10 days during infection period",
        "prevention": "Remove nearby cedar trees if possible, plant resistant varieties",
        "organic": "Sulfur-based fungicides, remove galls from cedar hosts"
    },
    "Apple___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Continue regular monitoring, maintain good cultural practices",
        "organic": "Maintain soil health with compost, encourage beneficial insects"
    },
    "Blueberry___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Maintain acidic soil pH (4.5-5.5), ensure proper drainage",
        "organic": "Mulch with pine bark, regular pruning for air circulation"
    },
    "Cherry_(including_sour)___Powdery_mildew": {
        "treatment": "Apply sulfur or potassium bicarbonate fungicides",
        "prevention": "Improve air circulation, avoid overhead watering",
        "organic": "Milk spray (1:9 milk to water), neem oil applications"
    },
    "Cherry_(including_sour)___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Regular pruning, balanced fertilization, monitor for pests",
        "organic": "Compost application, beneficial insect habitat"
    },
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "treatment": "Apply strobilurin or triazole fungicides at first sign",
        "prevention": "Crop rotation, tillage to bury residue, resistant hybrids",
        "organic": "Copper-based fungicides, remove infected crop residue"
    },
    "Corn_(maize)__Common_rust": {
        "treatment": "Apply fungicides if severe, usually doesn't need treatment",
        "prevention": "Plant resistant hybrids, balanced fertilization",
        "organic": "Generally self-limiting, maintain plant health"
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "treatment": "Apply fungicides at tasseling if disease present",
        "prevention": "Crop rotation, tillage, resistant hybrids",
        "organic": "Copper sprays, remove infected stalks after harvest"
    },
    "Corn_(maize)___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Continue regular monitoring and good practices",
        "organic": "Maintain soil fertility, crop rotation"
    },
    "Grape___Black_rot": {
        "treatment": "Apply fungicides from bud break to veraison",
        "prevention": "Remove mummies, prune for air flow, trellis management",
        "organic": "Copper and sulfur sprays, canopy management"
    },
    "Grape___Esca_(Black_Measles)": {
        "treatment": "No effective cure - remove infected vines",
        "prevention": "Use clean planting stock, avoid pruning wounds during rain",
        "organic": "Prune during dry weather, disinfect tools between cuts"
    },
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
        "treatment": "Apply mancozeb or ziram fungicides",
        "prevention": "Remove fallen leaves, improve air circulation",
        "organic": "Copper-based sprays, sanitation of leaf litter"
    },
    "Grape___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Regular canopy management, balanced nutrition",
        "organic": "Cover crops, compost applications"
    },
    "Litchi_curl_mite": {
        "treatment": "Prune and destroy heavily infested flushes, apply a recommended miticide or sulfur spray during active infestation",
        "prevention": "Use clean planting material, monitor new flushes regularly, avoid carrying infested nursery stock into orchards",
        "organic": "Use wettable sulfur where suitable, prune affected shoots, encourage natural predators by avoiding unnecessary broad-spectrum sprays"
    },
    "Litchi_healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Maintain regular orchard sanitation, balanced nutrition, and periodic monitoring of new flushes and panicles",
        "organic": "Apply compost or well-rotted manure, mulch to conserve moisture, maintain tree vigor with good cultural care"
    },
    "Litchi_leaf_insect_infestation": {
        "treatment": "Remove badly damaged leaves and apply an appropriate insecticide only when infestation is economically significant",
        "prevention": "Scout young flushes regularly, manage weeds and alternate hosts, keep trees well pruned for inspection and airflow",
        "organic": "Hand-remove affected leaves when feasible, use neem-based products or insecticidal soap on light infestations, conserve beneficial insects"
    },
    "Litchi_swooty_mould": {
        "treatment": "Control honeydew-producing pests such as aphids, scale, or mealybugs, then wash or allow the black coating to weather off the leaves",
        "prevention": "Monitor and manage sap-sucking insects early, prune crowded growth, improve air circulation within the canopy",
        "organic": "Use neem oil or horticultural oil against the insect source and wash leaves with water where practical to reduce the mould layer"
    },
    "Orange___Haunglongbing_(Citrus_greening)": {
        "treatment": "No cure - remove infected trees immediately",
        "prevention": "Control psyllid vectors, use certified disease-free stock",
        "organic": "Reflective mulches to deter psyllids, beneficial insects"
    },
    "Peach___Bacterial_spot": {
        "treatment": "Copper sprays at leaf fall and bud swell",
        "prevention": "Plant resistant varieties, avoid overhead irrigation",
        "organic": "Copper applications, improve soil drainage"
    },
    "Peach___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Regular pruning, pest monitoring, proper nutrition",
        "organic": "Organic mulches, beneficial insect release"
    },
    "Pepper,_bell___Bacterial_spot": {
        "treatment": "Copper-based bactericides, remove infected plants",
        "prevention": "Use certified seed, crop rotation, avoid wet foliage",
        "organic": "Copper sprays, bacteriophage applications"
    },
    "Pepper,_bell___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Proper spacing, drip irrigation, balanced fertilization",
        "organic": "Compost tea, companion planting"
    },
    "Potato___Early_blight": {
        "treatment": "Apply chlorothalonil or mancozeb fungicides",
        "prevention": "Crop rotation, remove infected debris, hill plants",
        "organic": "Copper sprays, baking soda solution"
    },
    "Potato___Late_blight": {
        "treatment": "Apply fungicides immediately at first symptoms",
        "prevention": "Use certified seed, hill plants, avoid overhead watering",
        "organic": "Copper-based fungicides, remove infected plants immediately"
    },
    "Potato___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Continue monitoring, proper hilling and watering",
        "organic": "Compost application, crop rotation"
    },
    "Raspberry___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Annual pruning, good air circulation, weed control",
        "organic": "Mulching, organic fertilizers"
    },
    "Soybean___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Crop rotation, row spacing for air flow",
        "organic": "Cover cropping, inoculation with rhizobia"
    },
    "Squash___Powdery_mildew": {
        "treatment": "Apply sulfur, potassium bicarbonate, or myclobutanil",
        "prevention": "Resistant varieties, good air circulation, avoid shade",
        "organic": "Milk spray, neem oil, baking soda solution"
    },
    "Strawberry___Leaf_scorch": {
        "treatment": "Apply fungicides like captan or thiophanate-methyl",
        "prevention": "Remove old leaves after harvest, proper spacing",
        "organic": "Copper sprays, improve air circulation"
    },
    "Strawberry___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Regular monitoring, proper watering, mulching",
        "organic": "Straw mulch, compost application"
    },
    "Tejpatta_healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Maintain good spacing, prune lightly for airflow, monitor leaves regularly for early pest or spot symptoms",
        "organic": "Use compost-based nutrition, mulch around the root zone, avoid overhead irrigation when possible"
    },
    "Tomato___Bacterial_spot": {
        "treatment": "Copper-based bactericides, remove severely infected plants",
        "prevention": "Use certified seed, crop rotation, avoid overhead watering",
        "organic": "Copper sprays, bacteriophage products"
    },
    "Tomato___Early_blight": {
        "treatment": "Apply chlorothalonil or mancozeb every 7-10 days",
        "prevention": "Stake plants, remove lower leaves, mulch soil",
        "organic": "Copper sprays, compost tea"
    },
    "Tomato___Late_blight": {
        "treatment": "Apply fungicides immediately, may need to remove plants",
        "prevention": "Use resistant varieties, stake plants, avoid overhead water",
        "organic": "Copper-based fungicides, remove infected plants"
    },
    "Tomato___Leaf_Mold": {
        "treatment": "Apply chlorothalonil or copper fungicides",
        "prevention": "Improve ventilation, reduce humidity, space plants",
        "organic": "Copper sprays, improve greenhouse ventilation"
    },
    "Tomato___Septoria_leaf_spot": {
        "treatment": "Apply chlorothalonil or mancozeb fungicides",
        "prevention": "Remove infected leaves, mulch soil, water at base",
        "organic": "Copper sprays, baking soda solution"
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "treatment": "Apply miticides like abamectin or bifenazate",
        "prevention": "Control dust, avoid water stress, introduce predators",
        "organic": "Neem oil, insecticidal soap, release predatory mites"
    },
    "Tomato___Target_Spot": {
        "treatment": "Apply fungicides like chlorothalonil or azoxystrobin",
        "prevention": "Crop rotation, remove infected debris, stake plants",
        "organic": "Copper-based fungicides, improve air circulation"
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "treatment": "No cure - remove infected plants, control whiteflies",
        "prevention": "Use resistant varieties, control whitefly vectors",
        "organic": "Reflective mulches, row covers, beneficial insects"
    },
    "Tomato___Tomato_mosaic_virus": {
        "treatment": "No cure - remove infected plants",
        "prevention": "Use resistant varieties, disinfect tools, control aphids",
        "organic": "Sanitation, remove weed hosts, beneficial insects"
    },
    "Tomato___healthy": {
        "treatment": "No treatment needed - plant is healthy!",
        "prevention": "Continue regular care, monitoring, and proper pruning",
        "organic": "Compost, companion planting, crop rotation"
    },
    "tejpatta_Algal_leaf_spot": {
        "treatment": "Prune and remove severely affected leaves, apply a copper-based fungicide where algal leaf spot is spreading",
        "prevention": "Reduce excess shade and leaf wetness, improve spacing and airflow, avoid prolonged overhead irrigation",
        "organic": "Use permitted copper formulations carefully, improve drainage and sunlight penetration, remove infected fallen leaves"
    }
}

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
    print(f"[PlantDisease] Disease model loaded from: {model_path}")
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
    print(f"[PlantDisease] Leaf model loaded from: {model_path}")
    return _leaf_model


def preprocess_image(image_path):
    """
    Load and preprocess an image for ResNet50 input.

    IMPORTANT: ResNet50 was trained with preprocess_input which scales
    pixels from [0, 255] to [-1, 1]. Using /255.0 gives wrong results.

    Args:
        image_path: path to image file on disk

    Returns:
        np.ndarray: shape (1, 224, 224, 3) scaled to [-1, 1]
    """
    tf = _get_tf()

    # Load and resize image
    img = tf.keras.utils.load_img(image_path, target_size=IMAGE_SIZE)

    # Convert to array — values in [0, 255]
    img_array = tf.keras.utils.img_to_array(img)

    # Add batch dimension — shape becomes (1, 224, 224, 3)
    img_array = np.expand_dims(img_array, axis=0)

    # ✅ ResNet50 preprocessing — scales [0,255] → [-1, 1]
    # This MUST match what was used during training
    img_array = preprocess_input(img_array)

    return img_array


def predict_leaf(image_path):
    """
    Run leaf / not-leaf classification.

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
                f"Leaf model output ({len(leaf_preds)}) doesn't match "
                f"expected classes ({len(LEAF_CLASS_NAMES)})"
            )

        leaf_top_idx   = int(np.argmax(leaf_preds))
        leaf_label     = LEAF_CLASS_NAMES[leaf_top_idx]
        leaf_confidence = float(leaf_preds[leaf_top_idx])
        leaf_scores    = {
            LEAF_CLASS_NAMES[i]: float(leaf_preds[i])
            for i in range(len(LEAF_CLASS_NAMES))
        }

        is_leaf = (
            leaf_top_idx == 0 and
            leaf_confidence >= LEAF_CONFIDENCE_THRESHOLD
        )

        return {
            'is_leaf'         : is_leaf,
            'leaf_label'      : leaf_label,
            'leaf_confidence' : leaf_confidence,
            'leaf_scores'     : leaf_scores,
            'status'          : 'completed',
        }

    except Exception as e:
        return {
            'is_leaf'         : False,
            'leaf_label'      : f'Error: {str(e)}',
            'leaf_confidence' : 0.0,
            'leaf_scores'     : {name: 0.0 for name in LEAF_CLASS_NAMES},
            'status'          : 'stub',
            'error'           : f'Leaf prediction failed: {str(e)}'
        }


def predict(image_path):
    """
    Two-stage prediction pipeline:
    1. Validate image is a leaf
    2. If leaf, classify disease

    Args:
        image_path: path to uploaded image file on disk

    Returns:
        dict: Full prediction result including disease name,
              confidence, recommendations, and leaf detection info
    """
    if not MODEL_READY:
        return {
            'disease_name' : 'Model not ready yet',
            'confidence'   : 0.0,
            'all_scores'   : {name: 0.0 for name in CLASS_NAMES},
            'status'       : 'stub',
        }

    # ── Stage 1: Leaf detection ──
    leaf_result = predict_leaf(image_path)

    if leaf_result.get('status') == 'stub':
        return {
            'disease_name'    : 'Unable to process image',
            'confidence'      : 0.0,
            'all_scores'      : {name: 0.0 for name in CLASS_NAMES},
            'status'          : 'error',
            'is_leaf'         : None,
            'leaf_label'      : leaf_result.get('leaf_label', 'Unknown'),
            'leaf_confidence' : leaf_result.get('leaf_confidence', 0.0),
            'error'           : leaf_result.get('error', 'Leaf model unavailable'),
            'leaf_error'      : leaf_result.get('error'),
        }

    if not leaf_result.get('is_leaf', False):
        return {
            'disease_name'    : 'Not a leaf',
            'confidence'      : leaf_result.get('leaf_confidence', 0.0),
            'all_scores'      : leaf_result.get('leaf_scores', {}),
            'status'          : 'completed',
            'is_leaf'         : False,
            'leaf_label'      : leaf_result.get('leaf_label'),
            'leaf_confidence' : leaf_result.get('leaf_confidence'),
        }

    # ── Stage 2: Disease classification ──
    model      = load_model()
    img_array  = preprocess_image(image_path)   # ✅ uses preprocess_input
    predictions = model.predict(img_array, verbose=0)[0]

    if len(predictions) != len(CLASS_NAMES):
        raise ValueError(
            f"Model output size ({len(predictions)}) does not match "
            f"CLASS_NAMES length ({len(CLASS_NAMES)}). "
            "Run the class name verification cell in Kaggle and update CLASS_NAMES."
        )

    # Top prediction
    top_idx      = int(np.argmax(predictions))
    confidence   = float(predictions[top_idx])
    disease_name = CLASS_NAMES[top_idx]

    # All scores dict
    all_scores = {
        CLASS_NAMES[i]: float(predictions[i])
        for i in range(len(CLASS_NAMES))
    }

    # Top 5 debug log
    print(f"[PlantDisease] DEBUG — Top 5 predictions:")
    for idx in np.argsort(predictions)[::-1][:5]:
        print(f"  {CLASS_NAMES[idx]:<55} {predictions[idx]:.4f}")
    print(f"[PlantDisease] Selected: {disease_name} ({confidence:.4f})")

    # Recommendation
    recommendation = DISEASE_RECOMMENDATIONS.get(disease_name, {
        'treatment'  : 'Consult with a plant pathologist for specific treatment recommendations',
        'prevention' : 'Maintain good garden hygiene and monitor plants regularly',
        'organic'    : 'Consider organic farming practices and consult local extension services'
    })

    # Parse plant name and condition
    parts     = disease_name.split('___')
    plant     = parts[0].replace('_', ' ').strip()
    condition = parts[1].replace('_', ' ').strip() if len(parts) > 1 else 'Unknown'
    is_healthy = 'healthy' in disease_name.lower()

    return {
        'disease_name'    : disease_name,
        'confidence'      : confidence,
        'all_scores'      : all_scores,
        'status'          : 'completed',
        'is_leaf'         : True,
        'leaf_label'      : leaf_result.get('leaf_label'),
        'leaf_confidence' : leaf_result.get('leaf_confidence'),
        'plant'           : plant,
        'condition'       : condition,
        'is_healthy'      : is_healthy,
        'recommendation'  : recommendation,
    }