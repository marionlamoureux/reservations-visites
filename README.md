# Réservations visites — Ileart

Formulaire de demande de visite scolaire pour le parc de sculptures **Ileart**.
Les enseignants remplissent un formulaire public pour organiser la visite de leur
classe ; les demandes sont consultables dans une interface d'administration protégée
par mot de passe, avec export CSV.

Application en production : <https://visites.ileart-sculptures.com/>

## Fonctionnalités

- **Formulaire public** (`/`) — 8 champs en français :
  - Date et heure de la visite
  - Besoin d'un accès aux toilettes municipales (Oui/Non)
  - Besoin d'accès au préau pour la pause méridienne (Oui/Non)
  - Nombre d'enfants (environ)
  - Nombre de véhicules sur le parking
  - Nom de l'établissement
  - Niveau scolaire
- **Notification e-mail** à chaque soumission, via l'API [Resend](https://resend.com).
- **Administration** protégée par identifiant/mot de passe :
  - `/admin` — liste des demandes reçues
  - `/admin/export.csv` — export CSV
  - `/admin/login`, `/admin/logout`
- **Page de confirmation** (`/merci`).

## Stack

- **Flask** (Python) servi par **gunicorn**
- **SQLite** (`submissions.db`) pour le stockage
- **nginx** en reverse proxy, service géré par **systemd**
- HTTPS via **Let's Encrypt** (certbot, renouvellement automatique)
- Hébergé sur un droplet **DigitalOcean** (Ubuntu 24.04, région `fra1`)

## Structure

```
app.py                    # Application Flask (routes, DB, notification e-mail)
requirements.txt          # Dépendances Python
.env.example              # Modèle de configuration (à copier en .env)
templates/                # Gabarits Jinja2
  base.html               #   mise en page + styles
  form.html               #   formulaire public
  thanks.html             #   page de confirmation
  login.html              #   connexion admin
  admin.html              #   tableau des demandes + export
deploy/
  provision.sh            # Crée le droplet DO et déploie (à lancer sur votre machine)
  bootstrap.sh            # Installe et démarre l'app (à lancer sur le serveur)
  visitform.service       # Unité systemd (gunicorn)
  nginx.conf              # Configuration nginx (reverse proxy)
```

## Configuration

Copiez `.env.example` en `.env` et renseignez les valeurs :

| Variable         | Rôle                                                        |
|------------------|-------------------------------------------------------------|
| `SECRET_KEY`     | Clé de session Flask (chaîne aléatoire longue)              |
| `ADMIN_USER`     | Identifiant de l'administration                             |
| `ADMIN_PASSWORD` | Mot de passe de l'administration                            |
| `RESEND_API_KEY` | Clé API Resend pour l'envoi des notifications               |
| `NOTIFY_EMAIL`   | Adresse qui reçoit les notifications de demande             |
| `FROM_EMAIL`     | Expéditeur (par défaut `onboarding@resend.dev`)             |
| `DB_PATH`        | (optionnel) Chemin de la base SQLite                        |

> Le fichier `.env` et la base `submissions.db` ne sont **jamais** versionnés
> (voir `.gitignore`) : ils contiennent des secrets et des données personnelles.

## Développement local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis éditez .env
python app.py               # http://localhost:8000
```

La table SQLite est créée automatiquement au démarrage (`init_db()`).

## Déploiement

```bash
# 1. Sur votre machine (doctl authentifié, clé SSH ajoutée à DigitalOcean)
export SSH_KEY_NAME="nom-de-votre-cle-dans-DO"
./deploy/provision.sh       # crée le droplet, copie les fichiers, bootstrap

# 2. Créez le .env sur le serveur, puis redémarrez
scp .env root@<IP>:/opt/visitform/.env
ssh root@<IP> 'systemctl restart visitform'
```

`bootstrap.sh` installe Python/nginx, crée le virtualenv, installe le service
systemd et configure nginx. Le HTTPS (certbot) est ajouté séparément une fois le
sous-domaine pointé vers le droplet.
