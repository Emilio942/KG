# Mathematik KI: Theoretischer Master-Plan für das KG-System

Dieses Dokument enthält die mathematischen Grundlagen zur Transformation des Projekts von einer einfachen VAE-Architektur zu einem hochdimensionalen, geometrisch-topologischen Entdeckungssystem.

## 1. Geometrie des latenten Raums (OT-VAE)
- **Konzept:** Übergang von euklidischen Vektoren zu Maßen im Wasserstein-Raum $(\mathcal{P}_2(\mathbb{R}^d), W_2)$.
- **Ziel:** Permutationsinvarianz und topologische Konsistenz bei chemischen Mischungen.
- **Implementierung:** Sinkhorn-Divergenz als Loss-Funktion, Dirichlet-Prior für Konzentrationen.

## 2. Physikalische Interaktionen (Kernels & Stability)
- **Konzept:** Integration von Synergie und Antagonismus durch second-order interaction kernels $K(v_i, v_j)$.
- **Ziel:** Modellierung nicht-linearer Geschmackseffekte ohne Verlust der konvexen Eigenschaften (CAT(0)).
- **Stabilität:** Lipschitz-Kontinuität des Encoders durch Entropie-Regularisierung ($\epsilon$).

## 3. Differenzierbare Logik & Graph-Integration
- **Konzept:** Transformation von symbolischen KG-Regeln in differenzierbare Potentialbarrieren $V(\mu)$.
- **Ziel:** Hypothesengenerierung als Gradient Flow auf der Wasserstein-Mannigfaltigkeit.
- **Navigation:** Ollivier-Ricci-Krümmung des Knowledge Graphs zur dynamischen Metrik-Modulation ("Gefahrenzonen" verlangsamen die Exploration).

## 4. Informationsgeometrie (Curiosity-Driven Discovery)
- **Konzept:** Fisher-Information-Metrik $\mathcal{G}(\mu)$ zur Quantifizierung des Expected Information Gain (EIG).
- **Ziel:** Aktives Targeting von Regionen mit hoher epistemischer Unsicherheit.
- **Dynamik:** Stochastische Differentialgleichungen (SDE) zur Flucht aus lokalen Wissensfallen.

## 5. Topologische Datenanalyse (Finding Flavor Voids)
- **Konzept:** Persistent Homology zur Identifizierung von "Wissenslöchern" im Geschmacksraum.
- **Ziel:** Entdeckung radikal neuer Kategorien statt bloßer Interpolation.
- **Validierung:** Wasserstein-Distanz zwischen Persistenz-Diagrammen als Beweis für strukturelle Neuheit.
