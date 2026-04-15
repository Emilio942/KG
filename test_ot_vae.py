import torch
import torch.nn as nn
from kg.ml_models.ot_vae_model import OT_VAE, SinkhornLoss

def test_ot_vae():
    print("Starte OT-VAE Validierung...")
    
    # Hyperparameter
    B, N, D = 4, 5, 8 # Batch, Atome, Atom-Dimension
    latent_dim = 16
    
    # Modell initialisieren
    model = OT_VAE(atom_dim=D, latent_dim=latent_dim, num_atoms=N)
    sinkhorn = SinkhornLoss()
    
    # Dummy Daten: Molekül-Features und Konzentrationen
    x = torch.randn(B, N, D)
    c = torch.softmax(torch.randn(B, N, 1), dim=1) # Echte Konzentrationen (Summe=1)
    
    # Forward Pass
    recon_x, recon_c, mu, logvar = model(x, c)
    
    print(f"Input Shape: {x.shape}")
    print(f"Recon Shape: {recon_x.shape}")
    print(f"Recon Concentrations Sum (Batch 0): {recon_c[0].sum().item():.4f}")
    
    # Loss berechnen
    # SinkhornLoss(x, recon_x, weights_x, weights_recon)
    ot_loss = sinkhorn(x, recon_x, c.squeeze(-1), recon_c)
    
    # KL Divergenz
    kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    
    total_loss = ot_loss + 0.01 * kl_loss
    
    print(f"OT-Loss (Wasserstein): {ot_loss.item():.4f}")
    print(f"KL-Loss: {kl_loss.item():.4f}")
    print(f"Total Loss: {total_loss.item():.4f}")
    
    assert recon_x.shape == x.shape
    assert abs(recon_c[0].sum().item() - 1.0) < 1e-5
    
    print("OT-VAE Validierung ERFOLGREICH!")

if __name__ == "__main__":
    test_ot_vae()
