import torch
import numpy as np
from kg.ml_models.ot_vae_model import OT_VAE, SinkhornLoss
from kg.ml_models.exploration_sde import ExplorationEngine, DiscoverySDE, SafetyBarrier
from kg.ml_models.topology_loss import TopologicalLoss, VoidExplorer

def test_sinkhorn():
    print("--- Teste SinkhornLoss ---")
    loss_fn = SinkhornLoss(eps=0.1, max_iter=20)
    B, N, D = 2, 5, 8
    x = torch.randn(B, N, D)
    y = torch.randn(B, N, D)
    wx = torch.softmax(torch.randn(B, N), dim=1)
    wy = torch.softmax(torch.randn(B, N), dim=1)
    
    loss = loss_fn(x, y, wx, wy)
    print(f"Sinkhorn Loss: {loss.item():.4f}")
    assert loss.item() >= 0, "Loss muss positiv sein"
    print("✅ SinkhornLoss funktioniert.")

def test_ot_vae():
    print("\n--- Teste OT-VAE ---")
    B, N, D = 2, 5, 8
    latent_dim = 16
    model = OT_VAE(atom_dim=D, latent_dim=latent_dim, num_atoms=N)
    
    x = torch.randn(B, N, D)
    c = torch.softmax(torch.randn(B, N, 1), dim=1)
    
    recon_x, recon_c, mu, logvar = model(x, c)
    print(f"Recon C Sum (Batch 0): {recon_c[0].sum().item():.4f}")
    assert abs(recon_c[0].sum().item() - 1.0) < 1e-5, "Konzentrationen müssen sich auf 1 summieren"
    print("✅ OT-VAE funktioniert.")

def test_exploration_sde():
    print("\n--- Teste Exploration SDE & Safety Barrier ---")
    B, D = 3, 16
    sde = DiscoverySDE(latent_dim=D, lr=0.1)
    barrier = SafetyBarrier(temperature=0.5)
    
    z = torch.randn(B, D, requires_grad=True)
    target = torch.randn(B, D)
    safe_centers = torch.randn(4, D)
    safe_radii = torch.ones(4) * 2.0
    
    # Test Barrier
    barrier_val = barrier(z, safe_centers, safe_radii)
    assert barrier_val.shape == (B,), "Barrier Wert muss Form [B] haben"
    
    # Test SDE Step
    uncertainty = torch.rand(B)
    curvature = torch.rand(B) * 0.5
    
    z_next = sde.step(z, target, uncertainty, curvature)
    assert z_next.shape == (B, D), "Z_next muss Form [B, D] haben"
    assert not torch.allclose(z, z_next), "Z sollte sich nach dem SDE Step ändern"
    print("✅ Exploration SDE funktioniert.")

def test_topology_loss():
    print("\n--- Teste Topological Loss ---")
    B, K, D = 4, 10, 16
    loss_fn = TopologicalLoss(bandwidth=1.0)
    
    z_gen = torch.randn(B, D, requires_grad=True)
    z_known = torch.randn(K, D)
    
    loss = loss_fn(z_gen, z_known)
    print(f"Topological Loss: {loss.item():.4f}")
    assert loss.item() <= 0, "Topological loss is negative (we maximize distance)"
    
    loss.backward()
    assert z_gen.grad is not None, "Gradienten müssen durch den Topological Loss fließen"
    print("✅ Topological Loss funktioniert.")

if __name__ == "__main__":
    print("==========================================")
    print("🔬 STARTE MATHEMATIK CORE TESTS")
    print("==========================================")
    try:
        test_sinkhorn()
        test_ot_vae()
        test_exploration_sde()
        test_topology_loss()
        print("\n🎉 ALLE MATHEMATISCHEN KOMPONENTEN SIND FUNKTIONSFÄHIG!")
    except Exception as e:
        print(f"\n❌ FEHLER AUFGETRETEN: {e}")
        import traceback
        traceback.print_exc()
