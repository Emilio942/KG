import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Any, Tuple

class SafetyBarrier(nn.Module):
    """
    Transforms discrete symbolic constraints into a differentiable potential barrier $V(\mu)$.
    Uses Log-Sum-Exp for smooth approximation.
    """
    def __init__(self, temperature: float = 0.1):
        super().__init__()
        self.tau = temperature

    def forward(self, z: torch.Tensor, safe_centers: torch.Tensor, safe_radii: torch.Tensor) -> torch.Tensor:
        """
        z: [B, D] - Latent points
        safe_centers: [K, D] - Centers of safe regions
        safe_radii: [K] - Radii of safe regions
        """
        B = z.shape[0]
        K = safe_centers.shape[0]
        
        # Compute distances to all safe centers
        # dists: [B, K]
        dists = torch.cdist(z, safe_centers, p=2)
        
        # Violations (distance > radius)
        # violations: [B, K]
        violations = F.relu(dists - safe_radii.unsqueeze(0))
        
        # Smooth barrier using Log-Sum-Exp
        # The higher the violation, the higher the barrier penalty
        scaled_violations = violations / self.tau
        barrier_potential = self.tau * torch.logsumexp(scaled_violations, dim=1)
        
        return barrier_potential

class DiscoverySDE(nn.Module):
    """
    Implements the Stochastic Differential Equation for discovery trajectories.
    Combines Natural Gradient Descent with Receptor-Binding Noise.
    """
    def __init__(self, latent_dim: int, lr: float = 0.01, noise_temp: float = 0.1):
        super().__init__()
        self.latent_dim = latent_dim
        self.eta = lr # Learning rate / step size
        self.beta_inv = noise_temp # Intrinsic temperature (noise scale)

    def compute_information_gradient(self, z: torch.Tensor, target_features: torch.Tensor) -> torch.Tensor:
        """
        Approximates the gradient of the Expected Information Gain (EIG).
        For simplicity, we use distance to unexplored target features.
        """
        # Direction towards unexplored target
        grad_eig = z - target_features
        return grad_eig

    def compute_diffusion_tensor(self, z: torch.Tensor, uncertainty_map: torch.Tensor) -> torch.Tensor:
        """
        Computes the state-dependent diffusion (noise) matrix based on epistemic uncertainty.
        High uncertainty -> High noise (to escape local traps).
        """
        B = z.shape[0]
        # diffusion_scale: [B]
        diffusion_scale = torch.sqrt(2.0 * self.beta_inv * uncertainty_map)
        # eye: [D, D]
        eye = torch.eye(self.latent_dim, device=z.device)
        # result: [B, D, D]
        return diffusion_scale.view(B, 1, 1) * eye.unsqueeze(0)

    def step(self, z: torch.Tensor, target_features: torch.Tensor, 
             uncertainty: torch.Tensor, curvature_penalty: torch.Tensor) -> torch.Tensor:
        """
        Performs one Euler-Maruyama step of the SDE.
        z: current latent state
        curvature_penalty: scalar field from Ollivier-Ricci curvature (slows down in dangerous areas)
        """
        B, D = z.shape
        
        # 1. Deterministic Drift (Information Gain)
        grad_eig = self.compute_information_gradient(z, target_features)
        
        # Modulate speed by graph curvature (high curvature = slow movement)
        velocity = -self.eta * grad_eig / (1.0 + curvature_penalty.unsqueeze(-1))
        
        # 2. Stochastic Diffusion (Receptor Noise)
        # diffusion: [B, D, D]
        diffusion = self.compute_diffusion_tensor(z, uncertainty)
        
        # dW: [B, D, 1]
        dW = torch.randn(B, D, 1, device=z.device)
        
        # Matrix-vector multiplication for noise: [B, D, D] @ [B, D, 1] -> [B, D, 1]
        noise = torch.bmm(diffusion, dW).squeeze(-1)
        
        # 3. Update state
        z_next = z + velocity + noise
        
        return z_next

class ExplorationEngine:
    """
    High-level engine that uses the SDE to find new flavor hypotheses.
    """
    def __init__(self, ot_vae: nn.Module, latent_dim: int):
        self.ot_vae = ot_vae
        self.sde = DiscoverySDE(latent_dim=latent_dim)
        self.barrier = SafetyBarrier()

    def explore(self, start_z: torch.Tensor, target_z: torch.Tensor, 
                safe_centers: torch.Tensor, safe_radii: torch.Tensor,
                steps: int = 50) -> torch.Tensor:
        """
        Run the SDE simulation to find an optimal new latent point.
        """
        z_t = start_z.clone().detach().requires_grad_(True)
        
        for t in range(steps):
            # Evaluate constraints (Barrier)
            barrier_val = self.barrier(z_t, safe_centers, safe_radii)
            barrier_grad = torch.autograd.grad(barrier_val.sum(), z_t)[0]
            
            # Dummy curvature and uncertainty for the prototype
            # In a full system, these come from the KG
            curvature = torch.zeros(z_t.shape[0], device=z_t.device) # Assume flat space for now
            uncertainty = torch.ones(z_t.shape[0], device=z_t.device) # Assume max uncertainty
            
            # SDE Step
            # We add the barrier gradient as a repulsive force
            z_next = self.sde.step(z_t, target_z, uncertainty, curvature)
            z_next = z_next - self.sde.eta * barrier_grad
            
            z_t = z_next.detach().requires_grad_(True)
            
        return z_t
