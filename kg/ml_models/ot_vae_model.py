import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class SinkhornLoss(nn.Module):
    """
    Entropic Regularized Optimal Transport Loss (Sinkhorn Divergence)
    Approximates the 2-Wasserstein distance between two empirical measures.
    """
    def __init__(self, eps: float = 0.05, max_iter: int = 30):
        super().__init__()
        self.eps = eps
        self.max_iter = max_iter

    def forward(self, x: torch.Tensor, y: torch.Tensor, wx: torch.Tensor, wy: torch.Tensor) -> torch.Tensor:
        """
        x, y: [B, N, D] - atom positions
        wx, wy: [B, N] - weights (concentrations)
        """
        B, N, D = x.shape
        # Compute cost matrix C [B, N, N]
        C = torch.cdist(x, y, p=2)**2

        # Sinkhorn iterations
        u = torch.ones_like(wx) / N
        v = torch.ones_like(wy) / N
        
        K = torch.exp(-C / self.eps)

        for _ in range(self.max_iter):
            u = wx / (torch.matmul(K, v.unsqueeze(-1)).squeeze(-1) + 1e-8)
            v = wy / (torch.matmul(K.transpose(-2, -1), u.unsqueeze(-1)).squeeze(-1) + 1e-8)

        # Optimal transport plan
        P = u.unsqueeze(-1) * K * v.unsqueeze(-2)
        
        # OT Cost
        loss = torch.sum(P * C, dim=(-2, -1))
        return loss.mean()

class SetEncoder(nn.Module):
    """
    Permutation-invariant encoder for molecular sets (DeepSets style)
    """
    def __init__(self, input_dim: int = 8, hidden_dim: int = 128, latent_dim: int = 64):
        super().__init__()
        # Point-wise transformation
        self.phi = nn.Sequential(
            nn.Linear(input_dim + 1, hidden_dim), # +1 for concentration
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        # Set-wise transformation (Aggregation)
        self.rho = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        self.mu_layer = nn.Linear(hidden_dim, latent_dim)
        self.logvar_layer = nn.Linear(hidden_dim, latent_dim)

    def forward(self, x: torch.Tensor, c: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        x: [B, N, input_dim] - molecular features
        c: [B, N, 1] - concentrations
        """
        # Concatenate features and concentrations
        combined = torch.cat([x, c], dim=-1) # [B, N, input_dim+1]
        
        # Apply phi to each atom
        h = self.phi(combined) # [B, N, hidden_dim]
        
        # Sum pooling (Permutation invariant)
        pooled = torch.sum(h, dim=1) # [B, hidden_dim]
        
        # Global transformation
        h_global = self.rho(pooled) # [B, hidden_dim]
        
        mu = self.mu_layer(h_global)
        logvar = self.logvar_layer(h_global)
        return mu, logvar

class SetDecoder(nn.Module):
    """
    Decoder that outputs a set of atoms and concentrations
    """
    def __init__(self, latent_dim: int = 64, num_atoms: int = 5, atom_dim: int = 8):
        super().__init__()
        self.num_atoms = num_atoms
        self.atom_dim = atom_dim
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 512),
            nn.ReLU(),
            nn.Linear(512, num_atoms * (atom_dim + 1)) # +1 for concentration logit
        )

    def forward(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        B = z.shape[0]
        out = self.decoder(z) # [B, num_atoms * (atom_dim + 1)]
        out = out.view(B, self.num_atoms, self.atom_dim + 1)
        
        # Split features and concentrations
        atom_feats = out[:, :, :self.atom_dim]
        conc_logits = out[:, :, self.atom_dim:]
        
        # Ensure concentrations sum to 1 (Softmax over atoms)
        concs = F.softmax(conc_logits.squeeze(-1), dim=-1) # [B, num_atoms]
        
        return atom_feats, concs

class OT_VAE(nn.Module):
    """
    The full Optimal Transport VAE
    """
    def __init__(self, atom_dim: int = 8, latent_dim: int = 64, num_atoms: int = 5):
        super().__init__()
        self.encoder = SetEncoder(input_dim=atom_dim, latent_dim=latent_dim)
        self.decoder = SetDecoder(latent_dim=latent_dim, num_atoms=num_atoms, atom_dim=atom_dim)
        self.sinkhorn = SinkhornLoss()

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x, c):
        mu, logvar = self.encoder(x, c)
        z = self.reparameterize(mu, logvar)
        recon_x, recon_c = self.decoder(z)
        return recon_x, recon_c, mu, logvar
