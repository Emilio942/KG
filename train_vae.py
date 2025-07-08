#!/usr/bin/env python3
"""
Training script for the TasteVAE model
Trains the VAE on taste combination data
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import DataLoader, Dataset
from pathlib import Path
import json
import logging
from typing import List, Dict, Any, Tuple
import matplotlib.pyplot as plt
from tqdm import tqdm

from kg.ml_models.vae_model import TasteVAE, MoleculeFeatureEncoder, MoleculeFeatures

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TasteDataset(Dataset):
    """Dataset for taste combinations"""
    
    def __init__(self, data_path: str = None):
        self.encoder = MoleculeFeatureEncoder()
        self.data = self._generate_synthetic_data()
        
    def _generate_synthetic_data(self) -> List[np.ndarray]:
        """Generate synthetic taste combination data"""
        # Known good combinations
        combinations = [
            # Sweet + Citrus
            {"Vanillin": 0.3, "Citral": 0.05, "Limonene": 0.1},
            {"Vanillin": 0.25, "Citral": 0.08, "Linalool": 0.03},
            
            # Earthy + Sweet  
            {"Geosmin": 0.02, "Vanillin": 0.4, "Benzaldehyde": 0.05},
            {"Geosmin": 0.015, "Vanillin": 0.35, "Eugenol": 0.01},
            
            # Mint + Citrus
            {"Menthol": 0.05, "Citral": 0.06, "Limonene": 0.12},
            {"Menthol": 0.04, "Linalool": 0.04, "Citral": 0.08},
            
            # Spicy + Sweet
            {"Eugenol": 0.02, "Vanillin": 0.3, "Benzaldehyde": 0.04},
            {"Eugenol": 0.025, "Vanillin": 0.28, "Linalool": 0.035},
            
            # Floral + Citrus
            {"Linalool": 0.05, "Citral": 0.07, "Geosmin": 0.008},
            {"Linalool": 0.045, "Limonene": 0.09, "Menthol": 0.02},
            
            # Complex combinations
            {"Vanillin": 0.2, "Geosmin": 0.01, "Citral": 0.05, "Linalool": 0.025},
            {"Benzaldehyde": 0.06, "Menthol": 0.03, "Eugenol": 0.015, "Limonene": 0.08},
            {"Vanillin": 0.15, "Citral": 0.04, "Geosmin": 0.005, "Eugenol": 0.01},
            
            # Variations
            {"Vanillin": 0.35, "Citral": 0.09},
            {"Geosmin": 0.025, "Vanillin": 0.32},
            {"Menthol": 0.06, "Linalool": 0.05},
            {"Eugenol": 0.018, "Benzaldehyde": 0.07},
            {"Limonene": 0.11, "Vanillin": 0.22},
            {"Citral": 0.065, "Geosmin": 0.012},
            {"Linalool": 0.055, "Menthol": 0.035},
        ]
        
        # Generate feature vectors
        data = []
        molecule_db = self._get_molecule_database()
        
        for combo in combinations:
            # Create molecule objects
            molecules = []
            for name, concentration in combo.items():
                if name in molecule_db:
                    molecules.append({
                        "name": name,
                        "concentration": concentration,
                        "features": molecule_db[name]
                    })
            
            # Encode to feature vector
            if molecules:
                features = self.encoder.encode_hypothesis(molecules)
                data.append(features)
        
        # Add noise variants
        for _ in range(len(data)):
            if data:
                base_features = data[np.random.randint(0, len(data))]
                noise = np.random.normal(0, 0.1, base_features.shape)
                noisy_features = base_features + noise
                # Clip to valid range
                noisy_features = np.clip(noisy_features, 0, 1)
                data.append(noisy_features)
        
        return data
    
    def _get_molecule_database(self) -> Dict[str, MoleculeFeatures]:
        """Get molecule database"""
        return {
            "Vanillin": MoleculeFeatures(
                molecular_weight=152.15, logp=1.21, polar_surface_area=38.69,
                rotatable_bonds=2, aromatic_rings=1, taste_category="SWEET",
                concentration_range=(0.1, 0.5)
            ),
            "Geosmin": MoleculeFeatures(
                molecular_weight=182.31, logp=3.57, polar_surface_area=20.23,
                rotatable_bonds=0, aromatic_rings=0, taste_category="EARTHY",
                concentration_range=(0.001, 0.05)
            ),
            "Citral": MoleculeFeatures(
                molecular_weight=152.24, logp=2.93, polar_surface_area=17.07,
                rotatable_bonds=4, aromatic_rings=0, taste_category="CITRUS",
                concentration_range=(0.01, 0.1)
            ),
            "Limonene": MoleculeFeatures(
                molecular_weight=136.24, logp=4.38, polar_surface_area=0.0,
                rotatable_bonds=1, aromatic_rings=0, taste_category="CITRUS",
                concentration_range=(0.05, 0.2)
            ),
            "Menthol": MoleculeFeatures(
                molecular_weight=156.27, logp=3.20, polar_surface_area=20.23,
                rotatable_bonds=1, aromatic_rings=0, taste_category="MINT",
                concentration_range=(0.01, 0.08)
            ),
            "Eugenol": MoleculeFeatures(
                molecular_weight=164.20, logp=2.27, polar_surface_area=29.46,
                rotatable_bonds=3, aromatic_rings=1, taste_category="SPICY",
                concentration_range=(0.005, 0.03)
            ),
            "Linalool": MoleculeFeatures(
                molecular_weight=154.25, logp=2.97, polar_surface_area=20.23,
                rotatable_bonds=4, aromatic_rings=0, taste_category="FLORAL",
                concentration_range=(0.01, 0.06)
            ),
            "Benzaldehyde": MoleculeFeatures(
                molecular_weight=106.12, logp=1.48, polar_surface_area=17.07,
                rotatable_bonds=1, aromatic_rings=1, taste_category="ALMOND",
                concentration_range=(0.02, 0.1)
            )
        }
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return torch.FloatTensor(self.data[idx])

def vae_loss(recon_x, x, mu, logvar):
    """VAE loss function"""
    # Reconstruction loss
    recon_loss = nn.functional.mse_loss(recon_x, x, reduction='sum')
    
    # KL divergence loss
    kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    
    return recon_loss + kl_loss

def train_vae(epochs: int = 100, batch_size: int = 32, learning_rate: float = 1e-3):
    """Train the VAE model"""
    
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on device: {device}")
    
    # Create dataset and dataloader
    dataset = TasteDataset()
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    logger.info(f"Training with {len(dataset)} samples")
    
    # Create model
    model = TasteVAE(input_dim=128, latent_dim=64, hidden_dim=256)
    model.to(device)
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Training loop
    model.train()
    losses = []
    
    for epoch in range(epochs):
        epoch_loss = 0
        num_batches = 0
        
        for batch in tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}"):
            batch = batch.to(device)
            
            # Forward pass
            recon_batch, mu, logvar, _ = model(batch)
            
            # Calculate loss
            loss = vae_loss(recon_batch, batch, mu, logvar)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        avg_loss = epoch_loss / num_batches
        losses.append(avg_loss)
        
        if (epoch + 1) % 10 == 0:
            logger.info(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
    
    # Save model
    model_path = Path("models/taste_vae.pth")
    model_path.parent.mkdir(exist_ok=True)
    
    torch.save(model.state_dict(), model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Plot training loss
    plt.figure(figsize=(10, 6))
    plt.plot(losses)
    plt.title('VAE Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.grid(True)
    plt.savefig('models/training_loss.png')
    logger.info("Training loss plot saved to models/training_loss.png")
    
    return model

def test_trained_model(model_path: str = "models/taste_vae.pth"):
    """Test the trained model"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load model
    model = TasteVAE(input_dim=128, latent_dim=64, hidden_dim=256)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    
    # Test generation
    with torch.no_grad():
        # Sample from latent space
        z = torch.randn(5, 64).to(device)
        
        # Generate samples
        generated = model.decode(z)
        
        logger.info("Generated samples:")
        for i, sample in enumerate(generated):
            logger.info(f"Sample {i+1}: {sample[:10].tolist()}")
    
    # Test with HypothesisGenerator
    from kg.ml_models.vae_model import HypothesisGenerator
    
    generator = HypothesisGenerator(model_path)
    
    # Generate hypotheses
    hypotheses = generator.generate_candidates(
        target_profiles=["SWEET", "CITRUS"],
        num_candidates=3
    )
    
    logger.info("Generated hypotheses:")
    for i, hyp in enumerate(hypotheses):
        logger.info(f"Hypothesis {i+1}:")
        for mol in hyp["molecules"]:
            logger.info(f"  {mol['name']}: {mol['concentration']}")

def main():
    """Main training function"""
    logger.info("Starting VAE training...")
    
    # Create models directory
    Path("models").mkdir(exist_ok=True)
    
    # Train model
    model = train_vae(epochs=50, batch_size=16, learning_rate=0.001)
    
    # Test model
    test_trained_model()
    
    logger.info("Training completed successfully!")

if __name__ == "__main__":
    main()