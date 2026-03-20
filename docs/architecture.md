# Technical Architecture : DealTracker

## 1. Stack Technique

| Composant | Technologie | Justification |
| :--- | :--- | :--- |
| **Frontend** | React + Tailwind CSS | Interface fluide, intégration rapide du Design System. |
| **Backend / API** | Python (FastAPI) | Performance asynchrone pour la gestion des Webhooks et IA. |
| **Base de données / Auth**| Supabase (PostgreSQL) | Backend-as-a-service, Auth native, RLS, hébergement EU. |
| **WhatsApp API** | Twilio | Sandbox pour le MVP, robuste. |
| **Transcription Vocale**| Mistral Voxtral Mini Transcribe V2 | Souveraineté européenne, haute performance pour le français. |
| **NLU / Parsing** | Claude API (Sonnet) | Raisonnement complexe pour l'extraction structurée (JSON). |
| **Hosting (Backend)** | Railway / Render (EU) | Déploiement simple du conteneur FastAPI. |

## 2. Modèle de Données (Supabase)

**Table `users` (Liée à auth.users)**
* `id` (UUID, PK)
* `email` (String, Unique)
* `full_name` (String)
* `whatsapp_number` (String, Unique) - *Clé pour le mapping Twilio*
* `created_at` (Timestamp)

**Table `deals`**
* `id` (UUID, PK)
* `owner_id` (UUID, FK -> users.id)
* `company` (String)
* `description` (Text)
* `action` (String)
* `deadline` (Date)
* `status` (Enum: active, won, lost)
* `created_at` (Timestamp)
* `closed_at` (Timestamp)

## 3. Diagramme de Flux (Webhook WhatsApp)

1. **Twilio** reçoit un audio WhatsApp -> Déclenche `POST /webhook/twilio` sur **FastAPI**.
2. **FastAPI** interroge **Supabase** avec le numéro de téléphone pour identifier le `owner_id`.
3. **FastAPI** envoie l'audio à **Mistral V2** -> Récupère le texte.
4. **FastAPI** envoie le texte + contexte (dossiers en cours) à **Claude Sonnet**.
5. **Claude** retourne le JSON : `{"intent": "update", "company": "...", "action": "..."}`.
6. **FastAPI** met à jour la table `deals` dans **Supabase**.
7. **FastAPI** demande à **Twilio** d'envoyer la confirmation WhatsApp à l'utilisateur.