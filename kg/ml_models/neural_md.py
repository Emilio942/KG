"""
Neural MD Simulation Model for ISV Module
Fast neural network-based molecular dynamics simulation
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import logging
from pathlib import Path

@dataclass
class ReceptorInteraction:
    """Receptor interaction data"""
    receptor_type: str
    binding_affinity: float
    confidence: float
    interaction_type: str

@dataclass
class TasteProfile:
    """Complete taste profile"""
    sweet: float
    sour: float
    salty: float
    bitter: float
    umami: float
    aromatic_profile: Dict[str, float]
    texture_profile: Dict[str, float]
    confidence: float

class ReceptorInteractionNet(nn.Module):
    """Neural network for receptor-molecule interactions"""
    
    def __init__(self, molecule_features: int = 32, hidden_dim: int = 128):
        super().__init__()
        
        # Taste receptor networks
        self.sweet_net = nn.Sequential(
            nn.Linear(molecule_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.ReLU(),
            nn.Linear(hidden_dim//2, 1),
            nn.Sigmoid()
        )
        
        self.bitter_net = nn.Sequential(
            nn.Linear(molecule_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.ReLU(),
            nn.Linear(hidden_dim//2, 1),
            nn.Sigmoid()
        )
        
        self.sour_net = nn.Sequential(
            nn.Linear(molecule_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.ReLU(),
            nn.Linear(hidden_dim//2, 1),
            nn.Sigmoid()
        )
        
        self.salty_net = nn.Sequential(
            nn.Linear(molecule_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.ReLU(),
            nn.Linear(hidden_dim//2, 1),
            nn.Sigmoid()
        )
        
        self.umami_net = nn.Sequential(
            nn.Linear(molecule_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim//2),
            nn.ReLU(),
            nn.Linear(hidden_dim//2, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        """Forward pass through all receptor networks"""
        sweet = self.sweet_net(x)
        bitter = self.bitter_net(x)
        sour = self.sour_net(x)
        salty = self.salty_net(x)
        umami = self.umami_net(x)
        
        return {
            'sweet': sweet,
            'bitter': bitter,
            'sour': sour,
            'salty': salty,
            'umami': umami
        }

class AromaProfileNet(nn.Module):
    """Neural network for aromatic profile prediction"""
    
    def __init__(self, molecule_features: int = 32, aroma_classes: int = 12):
        super().__init__()
        
        self.feature_extractor = nn.Sequential(
            nn.Linear(molecule_features, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        self.aroma_classifier = nn.Sequential(
            nn.Linear(32, aroma_classes),
            nn.Softmax(dim=1)
        )
        
    def forward(self, x):
        features = self.feature_extractor(x)
        aroma_scores = self.aroma_classifier(features)
        return aroma_scores

class TextureProfileNet(nn.Module):
    """Neural network for texture profile prediction"""
    
    def __init__(self, molecule_features: int = 32):
        super().__init__()
        
        self.net = nn.Sequential(
            nn.Linear(molecule_features, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 2),  # viscosity, crystallinity
            nn.Sigmoid()
        )
        
    def forward(self, x):
        return self.net(x)

class NeuralMDSimulator:
    """
    Neural MD Simulator
    Fast neural network-based molecular dynamics simulation
    """
    
    def __init__(self, models_dir: str = "models/neural_md"):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.models_dir = Path(models_dir)
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self.receptor_net = ReceptorInteractionNet()
        self.aroma_net = AromaProfileNet()
        self.texture_net = TextureProfileNet()
        
        # Move to device
        self.receptor_net.to(self.device)
        self.aroma_net.to(self.device)
        self.texture_net.to(self.device)
        
        # Load pre-trained models if available
        self._load_models()
        
        # Set to evaluation mode
        self.receptor_net.eval()
        self.aroma_net.eval()
        self.texture_net.eval()
        
        # Aroma class mapping
        self.aroma_classes = {
            0: "ERDIG", 1: "SÜßLICH", 2: "HOLZIG", 3: "FRUCHTIG",
            4: "BLUMIG", 5: "MINZIG", 6: "WÜRZIG", 7: "ZITRISCH",
            8: "NUSSIG", 9: "VANILLE", 10: "KARAMELL", 11: "KRÄUTER"
        }
        
        # Molecule feature encoder
        self.feature_encoder = MoleculeFeatureEncoder()
        
    def _load_models(self):
        """Load pre-trained models"""
        try:
            receptor_path = self.models_dir / "receptor_net.pth"
            aroma_path = self.models_dir / "aroma_net.pth"
            texture_path = self.models_dir / "texture_net.pth"
            
            if receptor_path.exists():
                self.receptor_net.load_state_dict(torch.load(receptor_path, map_location=self.device))
                self.logger.info("Loaded receptor interaction model")
            else:
                self.logger.info("No pre-trained receptor model found, using random weights")
                
            if aroma_path.exists():
                self.aroma_net.load_state_dict(torch.load(aroma_path, map_location=self.device))
                self.logger.info("Loaded aroma profile model")
            else:
                self.logger.info("No pre-trained aroma model found, using random weights")
                
            if texture_path.exists():
                self.texture_net.load_state_dict(torch.load(texture_path, map_location=self.device))
                self.logger.info("Loaded texture profile model")
            else:
                self.logger.info("No pre-trained texture model found, using random weights")
                
        except Exception as e:
            self.logger.error(f"Error loading models: {e}")
    
    def simulate_interactions(self, molecules: List[Dict[str, Any]], 
                            simulation_id: str = None) -> Dict[str, Any]:
        """
        Simulate molecular interactions using neural networks
        
        Args:
            molecules: List of molecule dictionaries
            simulation_id: Optional simulation ID for tracking
            
        Returns:
            Complete simulation results
        """
        try:
            # Extract features for all molecules
            molecule_features = []
            molecule_concentrations = []
            
            for mol in molecules:
                if 'features' in mol:
                    features = self._encode_molecule_features(mol['features'])
                    molecule_features.append(features)
                    molecule_concentrations.append(mol.get('concentration', 0.1))
                else:
                    # Fallback feature encoding
                    features = self._encode_molecule_name(mol['name'])
                    molecule_features.append(features)
                    molecule_concentrations.append(mol.get('concentration', 0.1))
            
            if not molecule_features:
                raise ValueError("No valid molecule features found")
            
            # Convert to tensors
            features_tensor = torch.FloatTensor(molecule_features).to(self.device)
            concentrations = torch.FloatTensor(molecule_concentrations).to(self.device)
            
            # Run neural simulations
            with torch.no_grad():
                # Receptor interactions
                receptor_results = self.receptor_net(features_tensor)
                
                # Aroma profile
                aroma_results = self.aroma_net(features_tensor)
                
                # Texture profile
                texture_results = self.texture_net(features_tensor)
                
                # Weight by concentrations and aggregate
                weighted_receptor = {}
                for taste, scores in receptor_results.items():
                    weighted_scores = scores.squeeze() * concentrations
                    weighted_receptor[taste] = float(torch.mean(weighted_scores))
                
                # Process aroma results
                weighted_aroma = torch.mean(aroma_results * concentrations.unsqueeze(1), dim=0)
                aroma_profile = {}
                for idx, score in enumerate(weighted_aroma):
                    if idx < len(self.aroma_classes):
                        aroma_profile[self.aroma_classes[idx]] = float(score)
                
                # Process texture results
                weighted_texture = torch.mean(texture_results * concentrations.unsqueeze(1), dim=0)
                texture_profile = {
                    "viskosität": float(weighted_texture[0]),
                    "kristallinität": float(weighted_texture[1])
                }
                
                # Calculate confidence based on concentration balance
                total_concentration = sum(molecule_concentrations)
                concentration_balance = min(1.0, total_concentration / 0.5)  # Optimal around 0.5
                confidence = 0.7 + 0.2 * concentration_balance
                
                # Determine primary molecule for each taste
                taste_molecules = {}
                for taste, score in weighted_receptor.items():
                    if score > 0.1:  # Threshold for significant taste
                        # Find molecule with highest contribution
                        max_contrib = 0
                        primary_mol = None
                        for i, mol in enumerate(molecules):
                            contrib = float(receptor_results[taste][i]) * molecule_concentrations[i]
                            if contrib > max_contrib:
                                max_contrib = contrib
                                primary_mol = mol['name']
                        taste_molecules[taste] = primary_mol
                
                # Format results
                simulation_results = {
                    "grundgeschmack": {
                        "süß": {
                            "score": round(weighted_receptor["sweet"], 3),
                            "molekül": taste_molecules.get("sweet", None)
                        },
                        "sauer": {
                            "score": round(weighted_receptor["sour"], 3),
                            "molekül": taste_molecules.get("sour", None)
                        },
                        "salzig": {
                            "score": round(weighted_receptor["salty"], 3),
                            "molekül": taste_molecules.get("salty", None)
                        },
                        "bitter": {
                            "score": round(weighted_receptor["bitter"], 3),
                            "molekül": taste_molecules.get("bitter", None)
                        },
                        "umami": {
                            "score": round(weighted_receptor["umami"], 3),
                            "molekül": taste_molecules.get("umami", None)
                        }
                    },
                    "aromaProfil": {k: round(v, 3) for k, v in aroma_profile.items() if v > 0.01},
                    "texturProfil": {k: round(v, 3) for k, v in texture_profile.items()},
                    "confidence": round(confidence, 3),
                    "simulation_method": "NEURAL_MD",
                    "model_version": "NeuralMD-v1.0.0"
                }
                
                return simulation_results
                
        except Exception as e:
            self.logger.error(f"Neural MD simulation failed: {e}")
            raise
    
    def _encode_molecule_features(self, features) -> List[float]:
        """Encode molecule features for neural network"""
        if hasattr(features, 'molecular_weight'):
            # Full MoleculeFeatures object
            return [
                features.molecular_weight / 200.0,  # Normalized
                features.logp / 5.0,
                features.polar_surface_area / 100.0,
                features.rotatable_bonds / 10.0,
                features.aromatic_rings / 3.0,
                self._encode_taste_category(features.taste_category),
                features.concentration_range[0],
                features.concentration_range[1]
            ] + [0.0] * 24  # Pad to 32 features
        else:
            # Fallback encoding
            return [0.5] * 32
    
    def _encode_molecule_name(self, name: str) -> List[float]:
        """Encode molecule by name (fallback method)"""
        # Simple name-based encoding
        name_hash = hash(name) % 1000
        base_features = [
            (name_hash % 100) / 100.0,  # Pseudo molecular weight
            (name_hash % 50) / 50.0,    # Pseudo logP
            (name_hash % 80) / 80.0,    # Pseudo PSA
            (name_hash % 10) / 10.0,    # Pseudo rotatable bonds
            (name_hash % 3) / 3.0,      # Pseudo aromatic rings
        ]
        
        # Add taste category encoding
        taste_encoding = self._encode_taste_category(self._guess_taste_category(name))
        base_features.append(taste_encoding)
        
        # Pad to 32 features
        return base_features + [0.0] * (32 - len(base_features))
    
    def _encode_taste_category(self, category: str) -> float:
        """Encode taste category as float"""
        categories = {
            "SWEET": 0.1, "BITTER": 0.2, "SOUR": 0.3, "SALTY": 0.4,
            "UMAMI": 0.5, "EARTHY": 0.6, "CITRUS": 0.7, "MINT": 0.8,
            "SPICY": 0.9, "FLORAL": 1.0, "ALMOND": 0.15, "VANILLA": 0.25
        }
        return categories.get(category.upper(), 0.5)
    
    def _guess_taste_category(self, name: str) -> str:
        """Guess taste category from molecule name"""
        name_lower = name.lower()
        if "vanil" in name_lower or "sweet" in name_lower:
            return "SWEET"
        elif "geosmin" in name_lower or "earth" in name_lower:
            return "EARTHY"
        elif "citral" in name_lower or "limonene" in name_lower:
            return "CITRUS"
        elif "menthol" in name_lower or "mint" in name_lower:
            return "MINT"
        elif "eugenol" in name_lower or "spice" in name_lower:
            return "SPICY"
        elif "linalool" in name_lower or "floral" in name_lower:
            return "FLORAL"
        elif "benzaldehyde" in name_lower or "almond" in name_lower:
            return "ALMOND"
        else:
            return "SWEET"

class MoleculeFeatureEncoder:
    """Encodes molecular features for neural networks"""
    
    def __init__(self):
        self.taste_categories = {
            "SWEET": 0.1, "BITTER": 0.2, "SOUR": 0.3, "SALTY": 0.4,
            "UMAMI": 0.5, "EARTHY": 0.6, "CITRUS": 0.7, "MINT": 0.8,
            "SPICY": 0.9, "FLORAL": 1.0, "ALMOND": 0.15, "VANILLA": 0.25
        }
    
    def encode_molecule(self, features) -> np.ndarray:
        """Encode molecular features to numerical vector"""
        if hasattr(features, 'molecular_weight'):
            return np.array([
                features.molecular_weight / 200.0,  # Normalized
                features.logp / 5.0,
                features.polar_surface_area / 100.0,
                features.rotatable_bonds / 10.0,
                features.aromatic_rings / 3.0,
                self.taste_categories.get(features.taste_category, 0.5),
                features.concentration_range[0],
                features.concentration_range[1]
            ])
        else:
            return np.array([0.5] * 8)

# Training functions for the neural models
def create_training_data():
    """Create synthetic training data for neural MD models"""
    # This would be replaced with real experimental data
    # For now, create synthetic data based on known molecule properties
    
    molecules = [
        {"name": "Vanillin", "sweet": 0.9, "bitter": 0.1, "aroma": "VANILLA"},
        {"name": "Geosmin", "sweet": 0.0, "bitter": 0.3, "aroma": "EARTHY"},
        {"name": "Citral", "sweet": 0.2, "bitter": 0.0, "aroma": "CITRUS"},
        {"name": "Menthol", "sweet": 0.0, "bitter": 0.2, "aroma": "MINT"},
        {"name": "Eugenol", "sweet": 0.1, "bitter": 0.4, "aroma": "SPICY"},
        {"name": "Linalool", "sweet": 0.3, "bitter": 0.0, "aroma": "FLORAL"},
        {"name": "Benzaldehyde", "sweet": 0.4, "bitter": 0.1, "aroma": "ALMOND"},
        {"name": "Limonene", "sweet": 0.1, "bitter": 0.0, "aroma": "CITRUS"},
    ]
    
    # Generate feature vectors and labels
    training_data = []
    for mol in molecules:
        # Create feature vector (simplified)
        features = [hash(mol["name"]) % 1000 / 1000.0] + [0.5] * 31
        
        # Labels
        labels = {
            "sweet": mol["sweet"],
            "bitter": mol["bitter"],
            "sour": 0.1,
            "salty": 0.05,
            "umami": 0.05,
            "aroma": mol["aroma"]
        }
        
        training_data.append((features, labels))
    
    return training_data

def train_neural_md_models():
    """Train the neural MD models"""
    # This would implement the actual training
    # For now, just create dummy models
    
    models_dir = Path("models/neural_md")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and save dummy models
    receptor_net = ReceptorInteractionNet()
    aroma_net = AromaProfileNet()
    texture_net = TextureProfileNet()
    
    torch.save(receptor_net.state_dict(), models_dir / "receptor_net.pth")
    torch.save(aroma_net.state_dict(), models_dir / "aroma_net.pth")
    torch.save(texture_net.state_dict(), models_dir / "texture_net.pth")
    
    print("Neural MD models created and saved")

if __name__ == "__main__":
    # Train models
    train_neural_md_models()
    
    # Test simulator
    simulator = NeuralMDSimulator()
    
    # Test simulation
    test_molecules = [
        {"name": "Vanillin", "concentration": 0.3},
        {"name": "Geosmin", "concentration": 0.02}
    ]
    
    results = simulator.simulate_interactions(test_molecules)
    print("Simulation results:", json.dumps(results, indent=2))