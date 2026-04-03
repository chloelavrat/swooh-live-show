Options du LPX_95_Custom

Drum pad

Zone correspondant aux pad du Drum Rack de Ableton. Ce grid 4x4 situé dans le coin en bas à gauche permet de sélectionner la note éditée dans la partie supérieure de la grille. Les pads Changement d’octaves [↑(CC1/89):↓(CC1/79)] permettent de changer d’octave, mais le rack de C1 à D#2 est affiché par défaut.

Les couleurs de ces pads correspondront aux couleurs des “Chain”.Si il est impossible de récupérer automatiquement les couleurs, ajouter un pad (ligne tout en haut, ou colonne tout à droite du launchpad) qui servira à changer de couleur comme suit:
			> PAD CHANGEMENT COULEUR + PAD KICK =
> Affichage d’un menu avec un choix de couleur
> Appuyer sur le pad correspondant à la couleur souhaitée =
> Changement de couleur effectuée et sortie du mode CHANGEMENT COULEUR.
*À noter que ces deux options (couleur automatiquement détectées et affichées, et changement de couleurs) sont présentes dans le script natif du Ableton Push 1, 2 et 3.

Comportement dynamique des couleurs en fonction des évènements suivants:
rouge: une note est jouée au passage de la tête de lecture.
Gris: pad/notes mutées.
Noir: Pads non armés/vides.
Coloré: Pads armés (Couleur correspondant à sa “Chain”).

Si j’appuie sur un pad, j’ai accès au step sequencer dédié à sa piste.



Step Sequencer

Le step Sequencer est par défaut sur un grid de 1/16 temps.

Un indicateur de métronome éclairé en orange avance pas-à-pas dans la grille afin d’indiquer la position actuelle de la tête de lecture.
*Cette fonctionnalité est purement informative et n’affecte en rien la fonction de chaque bouton au sein du mode.

Les couleurs affichées correspondent aux événements suivants: 
Vert: les notes jouées (dont l’intensité d’éclairage indique la vélocité).
gris: les notes mutées (les notes actuellement jouées clignotent en rouge au passage de la tête de lecture).
les notes actuellement jouées et en dehors de la portion de clip MIDI affichée clignotent en rouge également.

Si j’appuie sur une note vide, j’ajoute une note d’une velocity 100 sur le grid du piano roll (et donc du step sequencer).

Si j’appuie sur une note vide, j’ajoute une note d’une velocity 100 sur le grid du piano roll (et donc du step sequencer).

Si j’appuie sur une note déjà présente, alors je la supprime du piano roll et du Step Sequencer.

Affichage de la longueur et partie du clip joué [toggle]

Zone indiquant la longueur du clip MIDI joué: 1 pad = 1 temps.Le step sequencer ne peut afficher que 8 temps, si un clip est plus long, je peux accéder à la partie du clip non visible en appuyant sur la ligne correspondante.

Il est impossible de modifier la longueur d’un clip. Cette zone sert strictement à la navigation de l’affichage du step sequencer.


Navigation [↑(CC1/91):↓(CC1/92)] & [←(CC1/93);→(CC1/94)]

Ces pads permettent de naviguer dans l’interface de la fenêtre cession.

Lock/Unlock Piste/Clip [Toggle]

Mode permettant de se verrouiller soit seulement à la piste sélectionnée, soit à la piste et au clip MIDI en lecture. Si ces modes sont activés, les pads deviennent violets avec une luminosité plus forte.

Ce mode s’active en appuyant [toggle] pour passer d’un mode à l’autre:
- DÉSACTIVÉ (par défaut)
> LOCK PISTE
> FULL LOCK
> DÉSACTIVÉ

Le mode fonctionne comme suit:
Violet lumineux faible: Mode lock piste désactivé
Violet lumineux fort: Mode lock piste activé
les flèches de navigation [←→] se grisent.
Violet clignotement lent (fondu): Mode Full lock activé. Les flèches de navigation [←→] & [↑↓] se grisent.

Dès qu’un clip MIDI se déclenche, le step sequencer correspondant s’affiche automatiquement sur le Launchpad X.

Quand aucun clip midi n’est sélectionné, le step sequencer n’est pas affiché.







Trigger Roll mode [momentary]

Ce mode permet de trigger un pad du drum rack de manière à le faire jouer tous les 1/4, 1/8 ou 1/16 temps.

Il s’active en maintenant appuyé le pad [momentary], qui donne accès à un sous-menu qui s’affiche à la place de l'affichage de la longueur et partie du clip joué (3). C’est ici que le quantize s’affiche et que l’on sélectionne les temps  1/4, 1/8 ou 1/16.

Le temps 1/16 est sélectionné par défaut.

Le Trigger Roll ne fait effet que lorsque le pad du mode et le pad correspondant à la piste Drum que l’on veut trigger sont maintenus simultanément. 

*Définir si il est possible de créer un trigger roll sans effets midi Ableton. Si il n’est pas possible de le faire, alors ce mode fonctionne comme suit:
Appuyer (momentary) sur Trigger Roll
Ouvre le menu Quantize (permet d’activer l’Arpeggiator avec le quantize correspondant).
Appuyer sur la piste Drum que l’on veut trigger, cette dernière se joue alors comme une note midi déclenchée.
	> Permet à l’Arpeggiator de récupérer la note à Roll.
Sans la note déclenchée, l’Arpeggiator ne s’active qu’à la note suivante qui arrive.

Mute Button & Mute mode Change 

Le Mute mode permet de muter ou démuter la piste du drum rack comme suit:
			> PAD MUTE BUTTON + PAD KICK =
			> Piste sélectionnée mutée
(le pad devient gris dans le step sequencer ainsi que sur le l’affichage du drum rack sur la Launchpad X).
			> Relâchement PAD MUTE BUTTON =
			> Sortie du mode MUTE BUTTON.

Le Pad est en mode [momentary] par défaut. 

L’activation du Mute mode Change permet de passer dans le mode [Latch]. Dans ce cas, le Pad Mute devient orange avec un fondu clignotant et les  pads du drum rack ont aussi un fondu clignotant sauf ceux mutés et/ou vides. Je peux soit, activer ou désactiver une piste directement sans avoir à appuyer sur le pad Mute, soit sélectionner les pads que je veux désactiver tout en maintenant enfoncé le pad Mute pour les mute/unmute au relâchement de ce dernier.

Ce mode fonctionne comme suit:
> MUTE MODE ACTIVÉ [toggle]
> PAD MUTE BUTTON + PAD KICK + PAD CLAP + PAD HAT =
> Les pistes sélectionnées clignotent en vert.
> Pistes sélectionnées mutées au relâchement du pad Mute. Elles deviennent grises.

L’activation des pistes fonctionne de la même manière. 

