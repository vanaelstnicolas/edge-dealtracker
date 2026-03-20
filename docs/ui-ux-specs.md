# UI/UX Specifications : DealTracker

## 1. Design System (Branding Edge Consulting)

**Couleurs :**
* **Background :** `#FFFFFF` (Blanc)
* **Texte Principal :** `#000000` (Noir)
* **Couleur Primaire (Boutons, liens) :** `#CCBFFF` (Violet doux)
* **Couleur d'Accent / Succès :** `#D0F1E3` (Vert menthe)

**Typographie :**
* **Titres (Headings) :** `DegularDemo-Medium` (Utilisé pour KPIs, Noms de colonnes, Noms d'entreprise).
* **Corps de texte (Body) :** `Helvetica` (Fallback: Roboto). Taille de base: 19.2px pour une lecture sans effort des tableaux.

**Composants Visuels :**
* **Badges de Statut :** * Actif : Fond `#CCBFFF`, texte noir.
  * Gagné : Fond `#D0F1E3`, texte noir.
  * Perdu : Fond Gris clair neutre, texte sombre.
* **Logo :** Logo officiel d'Edge Consulting positionné en haut de la navigation latérale.

## 2. Sitemap & Navigation

L'application utilise une Sidebar (navigation latérale) persistante :
* `/dashboard` : Accueil et analytique.
* `/pipeline` : Espace de travail principal.
* `/settings` : Configuration (mapping WhatsApp).

## 3. Structure des Écrans (Wireframes)

**A. Dashboard (`/dashboard`)**
* **Top Cards (Titres en DegularDemo) :** 4 blocs affichant Dossiers Actifs, Gagnés, Perdus, Taux de conversion.
* **Alertes :** Liste rouge signalant les dossiers dont la deadline est dépassée.
* **Graphique :** Bar chart affichant la charge de dossiers par collaborateur.

**B. Pipeline (`/pipeline`) - VUE DATA TABLE**
* **Top Bar :** Barre de recherche globale, Boutons de filtres (Actifs, Gagnés, Perdus), Sélecteur d'Owner, Bouton Primaire (`#CCBFFF`) "+ Nouveau Dossier".
* **Data Table (Corps de texte en Helvetica) :** * Dense et triable (style Excel optimisé).
  * Colonnes : Entreprise, Description, Action, Deadline, Owner, Statut.
  * Les deadlines dépassées sont mises en surbrillance (ex: texte rouge).
* **Interaction :** Le clic sur une ligne ouvre un panneau latéral (Slide-over) pour modifier rapidement les données.

**C. Settings (`/settings`)**
* Tableau de configuration liant un Utilisateur à son `whatsapp_number` (format E.164).