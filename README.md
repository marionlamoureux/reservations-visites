# Réservations visites — Ileart

Formulaire de demande de visite scolaire pour le parc de sculptures **Ileart**.
Les enseignants remplissent un formulaire public pour organiser la visite de leur
classe qui declenche un email aux personnes concernées à la mairie; les demandes sont consultables dans une interface d'administration protégée
par mot de passe, avec export CSV.

Application en production : <https://visites.ileart-sculptures.com/>

## Fonctionnalités

- **Formulaire public** (`/`) — Champs en français :
  - Date et heure de la visite
  - Besoin d'un accès aux toilettes municipales (Oui/Non)
  - Besoin d'accès au préau pour la pause méridienne (Oui/Non)
  - Nombre d'enfants (environ)
  - Nombre de véhicules sur le parking
  - Nom de l'établissement
  - Niveau scolaire
  - Nom, numero et email du responsable de la visite, présent sur place
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

## Infra
Application et base de données déployées sur un droplet Digital Ocean.


## Configuration

Commit github trigger le redeployement de l'application sur le droplet via un github Action
Pour la configuration des emails:
Sur le droplet copiez `.env.example` en `.env` et renseignez les valeurs :

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
