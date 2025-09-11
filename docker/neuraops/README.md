# NeuraOps Docker Setup - Core API Edition

## 🚀 Quick Start - Compatible Mac M1/M2 et Intel

```bash
# Option 1: Docker Compose Full Stack (recommandé)
cd docker/
docker-compose up --build -d

# Option 2: Build manuel
./docker/build.sh

# Option 3: Run API seule (sans Redis/PostgreSQL)
docker run --rm -p 8000:8000 neuraops:latest
```

## 🏗️ Architecture des Services

```yaml
NeuraOps Stack:
├── neuraops-core     # API FastAPI + WebSocket (port 8000)
├── redis             # Cache & Sessions (port 6379)
└── postgres          # Base de données (port 5432)
```

## ✅ Compatibilité Multi-plateforme

Le Dockerfile intègre nativement le support multi-plateforme :
- ✅ **Mac M1/M2 (ARM64)** : Support natif
- ✅ **Intel/Linux (AMD64)** : Support natif
- ✅ **Auto-détection** de la plateforme
- ✅ **Pas de configuration** spécifique requise

### Build Multi-plateforme
```bash
# Build pour les deux architectures (AMD64 + ARM64)
./docker/build.sh neuraops:latest multiplatform

# Build pour la plateforme courante seulement
./docker/build.sh neuraops:latest local
```

## 🔧 Configuration

### 1. Variables d'Environnement
```bash
# Copier et éditer le fichier .env
cp .env .env.local
nano .env.local
```

**Variables importantes à changer en production :**
- `JWT_SECRET` : Clé secrète JWT (min 32 caractères)
- `DB_PASSWORD` : Mot de passe PostgreSQL
- `API_KEY` : Clé API pour enregistrement des agents

### 2. Endpoints Disponibles
- 📖 **API Docs** : http://localhost:8000/api/docs
- 🔍 **Health Check** : http://localhost:8000/api/health
- 🌐 **WebSocket** : ws://localhost:8000/ws/{agent_id}
- 📊 **Metrics** : http://localhost:8000/api/metrics

## 🧪 Test des Services

### Test de l'API
```bash
# Health check complet
curl http://localhost:8000/api/health

# Test avec CLI NeuraOps
docker exec neuraops-core python -m src.main health --verbose

# Test de l'API Python
docker exec neuraops-core python test_api.py
```

### Test des Connexions
```bash
# Redis
docker exec neuraops-redis redis-cli ping

# PostgreSQL
docker exec neuraops-postgres pg_isready -U neuraops

# Logs en temps réel
docker-compose logs -f
```

## 📊 Gestion de la Base de Données

### Accès PostgreSQL
```bash
# Connexion interactive
docker exec -it neuraops-postgres psql -U neuraops -d neuraops

# Voir les tables
\dt

# Voir les agents enregistrés
SELECT * FROM agents;
```

### Backup & Restore
```bash
# Backup
docker exec neuraops-postgres pg_dump -U neuraops neuraops > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i neuraops-postgres psql -U neuraops neuraops < backup.sql
```

## 🚦 Commandes Utiles

### Gestion des Services
```bash
# Démarrer tous les services
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes (reset complet)
docker-compose down -v

# Redémarrer un service spécifique
docker-compose restart neuraops-core
```

### Monitoring
```bash
# Status des containers
docker-compose ps

# Utilisation des ressources
docker stats

# Logs d'un service spécifique
docker-compose logs -f neuraops-core
docker-compose logs -f redis
docker-compose logs -f postgres
```

## 🔐 Sécurité

### Génération de Clés Sécurisées
```bash
# JWT Secret (production)
openssl rand -hex 32

# API Key pour agents
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Mot de passe PostgreSQL fort
openssl rand -base64 32
```

### Configuration CORS
```bash
# Production : Origines spécifiques
CORS_ORIGINS=https://app.example.com,https://api.example.com

# Développement : Toutes origines
CORS_ORIGINS=*
```

## 🛠️ Mode Développement

### Hot Reload pour Développement
```bash
# API avec rechargement automatique
docker-compose run --rm -p 8000:8000 neuraops-core \
  uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Exécution des Tests
```bash
# Tests unitaires
docker-compose run --rm neuraops-core pytest tests/

# Tests avec couverture
docker-compose run --rm neuraops-core pytest --cov=src tests/

# Test de l'API
docker-compose run --rm neuraops-core python test_api.py
```

## 🚢 Production

### Build pour Production
```bash
# Build optimisé
docker build -t neuraops-core:production -f Dockerfile ..

# Tag pour registry
docker tag neuraops-core:production registry.example.com/neuraops-core:latest

# Push vers registry
docker push registry.example.com/neuraops-core:latest
```

### Docker Compose Production
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  neuraops-core:
    image: registry.example.com/neuraops-core:latest
    env_file: .env.production
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## 🆘 Dépannage

### L'API ne démarre pas
```bash
# Vérifier les logs
docker-compose logs neuraops-core

# Vérifier les ports
lsof -i :8000

# Tester Ollama
curl https://ollama.prd.ihmn.fr/api/tags
```

### Problèmes de connexion PostgreSQL
```bash
# Réinitialiser PostgreSQL
docker-compose down
docker volume rm docker_postgres-data
docker-compose up -d postgres

# Attendre l'initialisation
sleep 10
docker-compose up -d
```

### Redis plein
```bash
# Vider le cache
docker exec neuraops-redis redis-cli FLUSHALL

# Vérifier la mémoire
docker exec neuraops-redis redis-cli INFO memory
```

## 📚 Documentation

- [API Documentation Interactive](http://localhost:8000/api/docs)
- [Configuration Complète](.env)
- [Schema PostgreSQL](sql/init.sql)
- [Architecture NeuraOps](../TASK.md)
- [Principes CLAUDE.md](../CLAUDE.md)