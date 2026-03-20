# Product Requirements Document (PRD) : DealTracker
**Version :** 1.0
**Statut :** Validé (MVP)
**Auteur :** Nico (Edge Consulting) & Équipe BMad

## 1. Goals and Background Context

**Contexte et Problème :**
Le suivi commercial est actuellement géré via un fichier Excel partagé. Cela engendre une friction élevée sur le terrain (obligeant à ouvrir Excel pour modifier une ligne), un manque de mise à jour en temps réel, une perte de l'historique lors de la clôture, et une absence de visibilité analytique.

**Proposition de Valeur :**
Permettre à l'équipe commerciale de gérer son pipeline depuis n'importe où via un simple message WhatsApp (texte ou vocal), tout en offrant à la direction une vue structurée et analytique accessible par navigateur.

**Objectifs & Métriques :**
* **O1 :** Remplacer le fichier Excel par une app web (Métrique : 100% des dossiers gérés dans l'app sous 1 mois).
* **O2 :** Permettre la création/MAJ via WhatsApp omnicanal (Métrique : Adoption par 80% de l'équipe en 2 semaines).
* **O3 :** Offrir un dashboard analytique actionnable (Métrique : Temps de revue en réunion réduit de 50%).
* **O4 :** Conserver l'historique complet (Métrique : Historique consultable sur 12+ mois).

## 2. Target Audience & Requirements (MVP)

**2.1 Utilisateurs Cibles (Personas)**
* **Consultant terrain :** Cherche à mettre à jour ses dossiers sans friction, souvent en mobilité. *Canal : WhatsApp (Vocal + Texte).*
* **Manager commercial :** A besoin de visibilité sur le pipeline et les retards. *Canaux : App Web (Filtres) + Rappels.*
* **Direction :** Cherche à suivre les KPIs de conversion. *Canal : App Web (Dashboard).*

**2.2 Exigences Fonctionnelles (MVP)**
* **FR1 - Authentification :** Connexion via Email/Mot de passe.
* **FR2 - Gestion (CRUD) :** Créer, modifier, clôturer et archiver un dossier via l'app web.
* **FR3 - Vues et Filtres :** Filtrage et tri des dossiers actifs/archivés.
* **FR4 - Dashboard :** Suivi des KPIs (actifs, gagnés, perdus, conversion).
* **FR5 - Intégration WhatsApp Omnicanale :** Création, modification et clôture via WhatsApp (Texte ET Vocal).
* **FR6 - Rappels Automatisés :** Envoi le lundi à 8h00 d'un récapitulatif par Email et WhatsApp.

**2.3 Exigences Non-Fonctionnelles (MVP)**
* **NFR1 & NFR2 - Sécurité :** Tokens JWT, validation signature Twilio, API keys sécurisées, HTTPS.
* **NFR3 - Performance :** Rate Limiting, traitement asynchrone pour l'IA.
* **NFR4 - RGPD :** Hébergement en Europe.
* **NFR5 - IA Vocale :** Utilisation de Mistral Voxtral Mini Transcribe V2 pour la rapidité et la souveraineté.

## 3. Product Backlog (Epics & User Stories)

**Epic 1 : Fondations & Authentification (Supabase)**
* **US 1.1 :** Configurer Supabase et le schéma de DB (`users`, `deals`).
* **US 1.2 :** Authentification Email/Mot de passe via Supabase Auth.
* **US 1.3 :** Mapping des numéros WhatsApp aux utilisateurs.

**Epic 2 : Application Web**
* **US 2.1 :** Vue Liste (CRUD) des dossiers.
* **US 2.2 :** Filtres (statut, owner) et tris (deadline).
* **US 2.3 :** Dashboard Analytique (KPIs temps réel).

**Epic 3 : Assistant WhatsApp Omnicanal**
* **US 3.1 :** Réception Webhook Twilio sécurisé.
* **US 3.2 :** Transcription vocale via Mistral Voxtral Mini Transcribe V2.
* **US 3.3 :** Extraction NLU via Claude API (Sonnet) vers format JSON.
* **US 3.4 :** Exécution en DB et envoi du message de confirmation WhatsApp.

**Epic 4 : Rappels Automatisés**
* **US 4.1 :** Cron job pour l'envoi des récapitulatifs du lundi matin (Email + WhatsApp).