import torch
import torch.nn as nn
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from kg.schemas import HGInput, HGOutput, Hypothese, MolekuelKomponente, TaskStatus, HGBeweis
from kg.ml_models.ot_vae_model import OT_VAE
from kg.ml_models.exploration_sde import ExplorationEngine
from kg.ml_models.topology_loss import TopologicalLoss, VoidExplorer

logger = logging.getLogger(__name__)

class HGAgent:
    """
    Hypothesen-Generator Agent 2.0 (Mathematical Edition)
    Uses OT-VAE, SDE exploration and Topological Data Analysis.
    """

    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize the mathematical arsenal
        self.atom_dim = 8 # Molecular descriptors dimension
        self.latent_dim = 32
        self.num_atoms = 5 # Max molecules in a mixture
        
        self.ot_vae = OT_VAE(atom_dim=self.atom_dim, latent_dim=self.latent_dim, num_atoms=self.num_atoms).to(self.device)
        self.engine = ExplorationEngine(self.ot_vae, latent_dim=self.latent_dim)
        self.topo_loss_fn = TopologicalLoss().to(self.device)
        self.void_explorer = VoidExplorer()
        
        # Placeholder for known data (Knowledge Base in Latent Space)
        # In a real system, this is loaded from the database
        self.z_known = torch.randn(100, self.latent_dim).to(self.device)
        
        logger.info("HG Agent 2.0 initialisiert mit OT-VAE und SDE-Engine.")

    async def initialize(self):
        """Pre-loading or model loading logic"""
        logger.info("HG Agent: Modelle geladen.")
        return True

    def _map_profile_to_latent(self, profile: List[str]) -> torch.Tensor:
        """
        Maps a symbolic taste profile to a target point in the latent manifold.
        (Simple implementation for the prototype)
        """
        # Deterministic mapping based on profile names
        seed = sum(ord(c) for p in profile for c in p)
        torch.manual_seed(seed)
        return torch.randn(1, self.latent_dim).to(self.device)

    def _generate_via_sde(self, constraints: Dict) -> Dict[str, Any]:
        """
        Generates a hypothesis by solving the discovery SDE.
        """
        target_profile = constraints.get("targetProfile", ["SÜSS"])
        target_z = self._map_profile_to_latent(target_profile)
        
        # Find the center of the largest 'Flavor Void'
        void_center = self.void_explorer.find_largest_void_center(self.z_known)
        
        # Balance between target profile and topological discovery
        exploration_target = 0.7 * target_z + 0.3 * void_center.unsqueeze(0)
        
        # Start point (current state of knowledge or random)
        start_z = torch.randn(1, self.latent_dim).to(self.device)
        
        # Define safe regions (from KG constraints)
        # Mock centers/radii for the prototype
        safe_centers = torch.randn(3, self.latent_dim).to(self.device)
        safe_radii = torch.ones(3).to(self.device) * 2.0
        
        # Run SDE Exploration
        logger.debug("Starte SDE-Gradient-Flow im latenten Raum...")
        z_final = self.engine.explore(start_z, exploration_target, safe_centers, safe_radii, steps=30)
        
        # Decode latent point to chemical atoms
        with torch.no_grad():
            atom_feats, concentrations = self.ot_vae.decoder(z_final)
            
        # Transform tensors to list of molecules
        # (Using mock names for molecular feature vectors)
        molecule_names = ["Vanillin", "Ethylvanillin", "Geosmin", "Limonene", "Citral"]
        components = []
        for i in range(self.num_atoms):
            conc = float(concentrations[0, i])
            if conc > 0.01: # Filter out trace amounts
                components.append({
                    "name": molecule_names[i % len(molecule_names)],
                    "konzentration": round(conc, 4)
                })
        
        return {
            "components": components,
            "latent_point": z_final,
            "novelty_score": float(torch.sigmoid(z_final.norm())) # Dummy metric
        }

    async def process_task(self, hg_input: HGInput) -> HGOutput:
        """
        Processes a task using the new mathematical framework.
        """
        logger.info(f"HG Agent 2.0 verarbeitet Task: {hg_input.taskID}")

        try:
            # Step 1: Generate via SDE
            gen_result = self._generate_via_sde(hg_input.constraints)
            
            # Step 2: Format components
            molekuel_komponenten = [
                MolekuelKomponente(name=c["name"], konzentration=c["konzentration"])
                for c in gen_result["components"]
            ]
            
            # Step 3: Create Hypothesis object
            hypothese = Hypothese(
                komponenten=molekuel_komponenten,
                typ="molekular"
            )
            
            # Step 4: Final Output
            beweis = HGBeweis(
                herleitung="Generiert via Wasserstein Gradient Flow (SDE) unter Berücksichtigung topologischer Voids.",
                noveltyScore=gen_result["novelty_score"],
                filterProtokoll="Mathematische Barrieren aktiv (Ollivier-Ricci Metrik Modulation).",
                constraintsPropagation=hg_input.constraints
            )
            
            return HGOutput(
                taskID=hg_input.taskID,
                status=TaskStatus.SUCCESS,
                hypotheseID=f"HYP-{uuid.uuid4().hex[:8].upper()}",
                hypothese=hypothese,
                beweis=beweis
            )

        except Exception as e:
            logger.error(f"Mathematischer Fehler im HG Agent: {e}", exc_info=True)
            # Fallback oder Fehlermeldung
            raise
