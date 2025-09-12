# NeuraOps Scripts

Collection de scripts pour automatiser les tâches courantes du projet NeuraOps.

## 📜 Scripts Disponibles

### 🔧 **install.sh** - Installation Complète
Installation complète de NeuraOps et de ses dépendances.

```bash
./scripts/install.sh
```

**Fonctionnalités :**
- Vérifie les prérequis (Python 3.11+, Node.js 18+)
- Installe UV package manager
- Configure les environnements Python pour Core et Agent
- Installe les dépendances Node.js pour l'UI
- Crée les fichiers .env depuis les templates
- Vérifie l'installation

**Variables d'environnement :**
- `INSTALL_UV=true/false` - Installer UV (défaut: true)
- `INSTALL_OLLAMA=true/false` - Installer Ollama (défaut: false)
- `SETUP_ENV=true/false` - Créer les fichiers .env (défaut: true)

---

### 🏗️ **build.sh** - Construction du Projet
Build tous les composants NeuraOps pour production ou développement.

```bash
# Build complet pour production
./scripts/build.sh all production

# Build composant spécifique
./scripts/build.sh core
./scripts/build.sh agent
./scripts/build.sh ui
./scripts/build.sh docker

# Build pour développement
./scripts/build.sh all development
```

**Options :**
- `all` - Build tous les composants (défaut)
- `core` - Build NeuraOps Core seulement
- `agent` - Build NeuraOps Agent seulement
- `ui` - Build NeuraOps UI seulement
- `docker` - Build images Docker seulement

**Environnements :**
- `production` - Build optimisé pour production (défaut)
- `development` - Build pour développement

---

### 🚀 **dev.sh** - Environnement de Développement
Lance l'environnement de développement avec rechargement automatique.

```bash
# Démarrage standard (Core API + UI)
./scripts/dev.sh

# Options avancées
./scripts/dev.sh --with-agent     # Inclure l'agent
./scripts/dev.sh --with-ollama    # Auto-démarrer Ollama
./scripts/dev.sh --no-core        # Sans Core API
./scripts/dev.sh --no-ui          # Sans interface UI
```

**Services démarrés :**
- **Core API** : http://localhost:8000 (avec docs sur /docs)
- **Web UI** : http://localhost:3000
- **Agent** : Service en arrière-plan (si --with-agent)

**Contrôles :**
- `Ctrl+C` - Arrêter tous les services
- Monitoring automatique des services

---

### 🧹 **clean.sh** - Nettoyage du Projet
Nettoie les fichiers de build, cache et fichiers temporaires.

```bash
# Nettoyage standard
./scripts/clean.sh

# Nettoyage approfondi
./scripts/clean.sh deep

# Nettoyage complet
./scripts/clean.sh all

# Simulation (dry-run)
./scripts/clean.sh standard dry-run
```

**Niveaux de nettoyage :**

#### **Standard**
- Cache Python (`__pycache__`, `.pytest_cache`)
- Build files (`dist/`, `build/`, `.next/`)
- Logs et fichiers temporaires

#### **Deep**
- Tout du niveau standard
- Environnements virtuels (`venv/`, `.venv/`)
- Images et conteneurs Docker

#### **All**
- Tout du niveau deep
- `node_modules/`
- Fichiers `.env` (garde `.env.example`)

---

## 🎯 Workflows Typiques

### Installation Initiale
```bash
# 1. Installation complète
./scripts/install.sh

# 2. Configuration manuelle des .env
nano neuraops-core/.env
nano neuraops-agent/.env
nano neuraops-ui/.env

# 3. Démarrage Ollama (si installé)
ollama serve

# 4. Test de développement
./scripts/dev.sh
```

### Développement Quotidien
```bash
# Démarrer l'environnement
./scripts/dev.sh

# Dans un autre terminal : tests/modifications
cd neuraops-core
uv run python -m src.main health --verbose

# Nettoyage périodique
./scripts/clean.sh standard
```

### Build de Production
```bash
# Nettoyage complet
./scripts/clean.sh deep

# Build de production
./scripts/build.sh all production

# Test du build
cd dist/ && ls -la
```

### Réinitialisation Complète
```bash
# Nettoyage total
./scripts/clean.sh all

# Réinstallation
./scripts/install.sh

# Rebuild
./scripts/build.sh all
```

---

## ⚙️ Configuration

### Variables d'Environnement Globales

```bash
# Installation
export INSTALL_UV=true
export INSTALL_OLLAMA=false
export SETUP_ENV=true

# Développement
export NEXT_PUBLIC_API_URL=http://localhost:8000
export OLLAMA_BASE_URL=http://localhost:11434
```

### Prérequis Système
- **Python** 3.11+ avec pip
- **Node.js** 18+ avec npm
- **UV** (installé automatiquement)
- **Ollama** (optionnel, pour l'IA)
- **Docker** (optionnel, pour conteneurisation)

---

## 🔍 Dépannage

### Erreurs Communes

#### "Python 3.11+ required"
```bash
# Vérifier la version
python3 --version

# Sur macOS avec Homebrew
brew install python@3.11
```

#### "Node.js 18+ required"
```bash
# Vérifier la version
node --version

# Installation avec nvm
nvm install 18
nvm use 18
```

#### "UV not found"
```bash
# Installation manuelle
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
```

#### "Ollama connection failed"
```bash
# Vérifier Ollama
ollama serve

# Dans un autre terminal
curl http://localhost:11434/api/tags
```

### Logs de Debugging
```bash
# Core API logs
cd neuraops-core
uv run python -m src.main health --verbose

# Agent logs
cd neuraops-agent
uv run python -m src.main status

# UI logs (dans le navigateur)
# Console développeur : F12
```

---

## 📁 Structure des Scripts

```
scripts/
├── README.md           # Ce fichier
├── install.sh          # Installation complète
├── build.sh            # Build du projet
├── dev.sh              # Environnement de développement
└── clean.sh            # Nettoyage du projet
```

---

## 🤝 Contribution

Pour ajouter de nouveaux scripts :

1. Créer le script dans `scripts/`
2. Le rendre exécutable : `chmod +x scripts/nouveau-script.sh`
3. Suivre le format des scripts existants
4. Documenter dans ce README
5. Tester sur différents OS (macOS, Linux)

**Template de script :**
```bash
#!/bin/bash
set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
print_step() { echo -e "${YELLOW}▸ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

# Main logic
main() {
    print_step "Starting..."
    # ... script logic ...
    print_success "Done!"
}

main "$@"
```