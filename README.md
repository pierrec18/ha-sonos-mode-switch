# Home Assistant — intégration native

L'intégration `sonos_mode_switch` utilise uniquement l'API HTTP du service.
Elle ne contacte pas directement les enceintes et ne nécessite ni SSH, ni
`rest_command`, ni package YAML dans Home Assistant.

## Installation

Dans HACS / Marketplace, ajouter `pierrec18/ha-sonos-mode-switch` comme dépôt
personnalisé de catégorie **Intégration**, télécharger la version `v0.1.0`,
puis redémarrer Home Assistant. Le dépôt reste privé : le compte GitHub de
HACS / Marketplace doit pouvoir le lire.

Dans **Paramètres → Appareils et services → Ajouter une intégration**, choisir
**Sonos Mode Switch**, puis saisir l'origine HTTP(S) du service (exemple :
`http://ADRESSE_DOCKER:8765`) et son jeton API. Le jeton est conservé par Home
Assistant dans l'entrée de configuration, et jamais dans les attributs des entités.

## Utilisation

L'appareil expose quatre entités :

- Sélecteur **Mode** : `music` / `cinema`, traduits en Musique / Cinéma.
- Capteur **Mode observé** : topologie effectivement observée, pas dernière demande.
- Capteur binaire **Transition en cours**.
- Capteur **Dernière opération** : acceptée, en cours, terminée ou échec, avec ID et erreur.

Le sélecteur devient indisponible pendant une transition, si les observations sont
périmées, si les enceintes sont inaccessibles ou si les écritures sont désactivées.
Une action recalcule le plan et transmet son empreinte. Aucune mutation n'est
relancée automatiquement après une erreur réseau ambiguë. La surveillance reprend
par `/v1/status` après redémarrage de HA ; le service conserve l'opération.
Le polling est réglable de 2 à 60 secondes, 5 par défaut. Un jeton refusé déclenche
le parcours standard de réauthentification.

La configuration et les redémarrages de l'intégration ne déclenchent aucune bascule.
La topologie Cinéma ne prouve pas le rendu audio : utiliser une piste 5.1 pour
vérifier les surrounds. Trueplay n'est ni sauvegardé ni garanti restauré.

## Archive manuelle

L'archive `sonos_mode_switch.zip` contient `custom_components/sonos_mode_switch/` :
elle s'extrait dans `/config`, pas dans le dossier de l'intégration.

## Développement

Python 3.14.2+ ; créer un environnement isolé puis :

```sh
pip install -r requirements-ha-test.txt
pip install --no-deps pytest-homeassistant-custom-component==0.13.375
python scripts/test_homeassistant.py
```

Le helper complet PyPI cible Core 2026.10.4 et n'est pas compatible avec les
internes logger de 2026.11.2. Les tests initialisent donc les vrais registres et le
vrai gestionnaire d'entrées de Core 2026.11.2 ; seul son mock HTTP indépendant est
réutilisé. Les sockets réseau sont désactivées. Aucun identifiant de production
n'est utilisé dans les tests.
