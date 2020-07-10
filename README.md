# GitHub Action

Explication de l'expérimentation d'un pipeline de déploiement avec GitHub Action.
L'utilisation de PHP est uniquement pour la démonstration,
les concepts peuvent être appliqués à n'importe quel langage.
Des éléments seront sauté puisque déjà abordé dans les exemples avec **Bitbucket** et **GitLab**.

## Sections

- [**Dossier** `.github`](##dossier-github`)
- [**Projet** `php-cicd`](##projet-php-cicd)
  - [**Fichier** `php-worflow.yml`](###fichier-php-workflowyml)
    - [**Élément** `name`](####élément-name)
    - [**Élément** `on`](####élément-on)
    - [**Élément** `env`](####élément-env)
    - [**Élément** `jobs`](####élément-jobs)
  - [**Fichier** `php-deploy-worflow.yml`](###fichier-php-deploy-workflowyml)
    - [**Élément deploy** `on`](####élément-deploy-on)
    - [**Élément deploy** `jobs`](####élément-deploy-jobs)
- [**Action** `docker-exist-action`](##action-docker-exist-action)
  - [**Fichier** `action.yml`](###fichier-actionyml)
  - [**Fichier** `Dockerfile`](###fichier-dockerfile)
  - [**Fichier** `entrypoint.sh`](###fichier-entrypointsh)
  - [**Fichier** `.github/workflows/main.yml`](###fichier-github/workflows/mainyml)
- [**GitHub Marketplace**](##github-marketplace)

## Dossier `.github`

J'aborde rapidement le dossier `.github` qui accept certain fichiers/dossiers qui sont interprété par GitHub.
Plusieurs **Action** du Marketplace utilise aussi ce dossier pour leur fichier de configuration.
L'élément le plus important pour cette exemple sera le dossier `workflow`.

- `CODE_OF_CONDUCT.md`: Décrit à la communauté voulant contribuer comment se comporter.
- `CONTRIBUTING.md`: Décrit comment contribuer au projet (aide techniquement).
- `FUNDING.yml`: Indique que le projet cherche du financement et comment contribuer financièrement.
- `ISSUE_TEMPLATE`: Dossier offrant plusieurs templates différents lors de rapport de bug selon le type de rapport. Voir [TensorFlow](https://github.com/tensorflow/tensorflow/tree/f3fd82f65724cdba600fdd23d251c2b01152ed3c/.github/ISSUE_TEMPLATE) pour une bonne exemple.
- `PULL_REQUEST_TEMPLATE.md`: Template à compléter lors de *Pull Request*.
- `SECURITY.md`: La démarche à suivre pour rapporter une faille de sécurité.
- `workflows`: Dossier ne pouvant posséder que des fichier **YAML** qui serons tous, sans exception, interprété comme un **Workflow** en lien avec **GitHub Action**.

[↑ Table des matières ↑](##sections)

## Projet `php-cicd`

Point particulier, GitHub Action gère nativement le **shell script** ainsi que le **javascript**. Dans cette exemple j'ai priorisé l'utilisation du **shell script**.

Un **Workflow** représente un pipeline qui peu être subdivisé en **Job** et une job peut être subdivisé en étape.

### Fichier `php-worflow.yml`

#### Élément `name`

Optionnel, permet de nommer le pipeline. Par défaut il sera représenté par le nom du fichier YAML.

#### Élément `on`

Élément déclencheur du *Workflow*, c'est ici qu'on peut définir un ou plusieurs éléments qui pourrons déclencher l'action.

Dans ce cas ci, le *workflow* se déclenche lors d'un push sur les branches `master` ou `production`.

```yml
on:
  push:
    branches:
      - master
      - production
```

Si j'aurai voulu le faire sur toutes les branches j'aurai aussi pu écrire:

```yml
on: [push]
```

Ou encore:

```yml
on:
  push:
    branches:
      - "*"
```

Il est aussi possible d'utiliser `*` et `**` pour représenter des patterns de nom de branche tel que `release-*`.

Point fort de GitHub, la très très large variété d'**events** pouvant démarrer un *workflow*. Que ce soit l'ajout d'un nouveau membre au *repository* pour lui envoyer un courriel de bienvenu, envoyer un mot de remerciements à un utilisateur votant un étoile au projet. Pour plus d'information voir la [liste des events](https://docs.github.com/en/actions/reference/events-that-trigger-workflows).

#### Élément `env`

Permet de définir les variable d'environnement qui seront commun à l'entièreté des Jobs.
On ne peut pas altérer ces variables, il faut les considérer comme constante, chaque **Job** est indépendante.

Dans mon exemple, j'utilise les variables d'environnement pour partager l'adresse du registre de container utiliser pour stocker mes images. Pour `DOCKER_USERNAME` et `DOCKER_PASSWORD`, ils sont présent pour faciliter l'utilisation de registre autres, principalement celui de github auquel la clef n'a pas à être ajouter à nous **secrets** car elle est généré automatiquement et accessible via `${{ github.token }}` ou `${{ GITHUB_TOKEN }}`. L'utilisation de ces variable permet donc de facilement changer de registre sans avoir à revérifier le code.

À noter que toutes les [variables par défaut de github](https://docs.github.com/en/actions/configuring-and-managing-workflows/using-environment-variables#default-environment-variables) peuvent s'utiliser en minuscule en replaçant les `"_"` par des `"."`.

```yml
env:
  DOCKER_REGISTRY: docker.io
  DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
  DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
  PHP_IMAGE: ${{ secrets.DOCKER_USERNAME }}/gh-php
  PHP_TEST_IMAGE: ${{ secrets.DOCKER_USERNAME }}/gh-php-test
```

#### Élément `jobs`

J'ai diviser ce *workflow* en 3 *jobs* distinctes soit `php_build`, `php_test` et `php_deploy_request`.

##### Builds

Pour cette *job*, nous devons obligatoirement définir sur quel OS s'exécutera le code parmi ceux offert par GitHub. Les machines Linux offrant le plus de temps d'accès c'est donc à privilégier si notre projet ne nécessite pas l'utilisation de MacOS ou Windows.

Optionnellement, nous pouvons donner un nom à notre *job* pour améliorer la lisibilité sur GitHub.

```yml
    name: Builds
    runs-on: ubuntu-latest
    steps:
```

Nous pouvons ensuite définir les étapes qui s'exécuterons en ordre dans notre *job*. Chaque étape peut être nommée et peut posséder différent élément conditionnel. Il s'agit d'un point fort de **GitHub Action**.

Dans la première étape, nous appelons l'action `actions/checkout@v2`, offert par GitHub, qui clone notre branche actuelle et nous permet d'accéder à nos fichiers dans les étapes subséquentes. Contrairement à Bitbucket et GitLab ou notre projet est cloné par défaut, cette méthode permet d'avoir des actions qui sont indépendante d'un projet, tel qu'une action déclenché manuellement via l'API de GitHub par le Hub pour ensuite envoyer des notifications (cas d'utilisation inutile par contre).

```yml
      - name: Checkout Repo
        uses: actions/checkout@v2
```

Pour l'étape suivante j'utilise l'action `trilom/file-changes-action@v1.2.4` qui me permet de récupérer la liste des fichiers ajouté/modifié/supprimé depuis le dernier push et de les produire en output. D'autres options sont aussi possible. Je déclare aussi un `id` qui est essentiel pour récupérer l'output généré par cette étape.

```yml
      - name: Get file changes
        id: file_changes
        uses: trilom/file-changes-action@v1.2.4
        with:
          githubToken: ${{ github.token }}
          output: ";"
```

Par la suite, j'ai créé ma propre action basé sur Docker et que j'explique en profondeur [ici](##action-docker-exist-action) qui génère comme output `0` is l'image existe, `1` autrement. En soit, j'interroge un registre de container pour savoir si mon image existe. Ça vise à palier le cas ou on ajoute une mécanique CICD à un projet existant pour lequel nous n'avons pas à retoucher à son `Dockerfile` ou encore un projet ou nous désirons changer l'emplacement de nos images. La première exécution, même si le fichier n'a pas changé, générera tout de même l'étape de build.

La clef `with` permet de définir les inputs de l'action.

```yml
      - name: Check if PHP image exist in registry
        id: is_php_image_exist
        uses: tm-bverret/docker-exist-action@v1.1.2
        with:
          registry: docker.io
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          image: ${{ env.PHP_IMAGE }}:latest
```

Pour la construction de l'image, j'utilise une action officiellement créé par Docker et qui facilite la mécanique. J'ai inclus la clef `if` qui me permet de définir dans quel condition cette étape doit être exécuté. GitHub offre certain function util tel que `contains` qui me permet de voir si le fichier `docker/Dockerfile` est présent dans les fichiers modifié de l'étape `file_changes`. J'ai aussi inclus la vérification de l'existence de l'image de l'étape `is_php_image_exist`.

Parmi les inputs de cette action, j'ai indiqué de consulter la dernière image créé pour accélérer la nouvelle image. Cette image possédera le tag du `sha` du commit du à l'option `tag_with_sha` ainsi que tous les tags inclus dans `tags` (mettre dans une liste si plusieurs). Par défaut seul la `latest` est créé.

```yml
      - name: Publish PHP Image
        # In this if, remove the or if use github docker registry
        if: contains(steps.file_changes.outputs.files, 'docker/Dockerfile') || !((steps.is_php_image_exist.outputs.image_exist))
        uses: docker/build-push-action@v1.1.0
        with:
          name: ${{ env.PHP_IMAGE }}
          username: ${{env.DOCKER_USERNAME}}
          password: ${{env.DOCKER_PASSWORD}}
          registry: ${{env.DOCKER_REGISTRY}}
          cache_froms: ${{ env.PHP_IMAGE }}:latest
          dockerfile: docker/Dockerfile
          repository: ${{ env.PHP_IMAGE }}
          tag_with_sha: true
          tags: latest
```

Pour l'image servant au test, l'étape est très similaire à celle précédente. J'aborderai donc uniquement les paramètres additionnel utilisé avec l'action `docker/build-push-action`. Bien qu'inutile de spécifier les deux, je voulais démontrer que nous pouvions utiliser plusieurs image comme cache dans `cache_froms`. Puisque l'image test permet des arguments nous pouvons utiliser `build_args` pour les inclure sous la forme d'une *string* `var1=1 var2=2`.

```yml
          cache_froms: ${{ env.PHP_IMAGE }}:latest,${{ env.PHP_TEST_IMAGE }}:latest
          build_args: base_image=${{env.DOCKER_REGISTRY}}/${{env.PHP_IMAGE}}:latest
```

Finalement, pour la gestion des erreurs j'ai ajouté l'étape `Build Failure Handler` qui se déclenche uniquement si une étape précédente d'une même job à échoué. Il est aussi possible de cibler l'échec d'une étape préciser, nous pourrions donc traiter l'échec du build de base différemment de l'échec du build de test.

```yml
      - name: Build Failure Handler
        if: failure()
        run: |
          chmod +x ./scripts/on_build_failure.sh
          sh ./scripts/on_build_failure.sh
```

_**Point à noter**: Une étapes ne peut pas utiliser la clef `uses` et `run` en même temps. Soit nous utilisons une action ou container via `uses`, soit nous exécutons du script via `run`._

##### Tests

Puisque par défaut les jobs s'exécute en parallèle et que nous désirons que les tests s'exécute après l'étape de build nous pouvons utiliser la clef `needs` pour définir la liste de toutes les *jobs* dont dépend celle-ci.

Pour cette *job*, j'indique que toutes les étapes doivent être exécuté dans un **container précis** plutôt que directement sur la machine virtuel *Linux*. L'image doit obligatoirement être public et ne pas nécessiter. Un des rares désavantage de GitHub Action face à GitLab CI est l'incapacité d'utiliser des variables dans le nom de l'image pour la clef `container`, les variables peuvent toujours être utilisé dans les étapes par contre.

Malheureusement, le registre de GitHub nécessitant obligatoirement une authentification pour *puller* une image même si l'image est publiquement accessible, nous ne pouvons donc pas utiliser une image stocker chez GitHub via `docker.pkg.github.com` présentement.

```yml
  php_test:
    name: Tests
    runs-on: ubuntu-latest
    needs: ["php_build"]
    container:
      # Variable not working in container image name
      # https://github.community/t/how-to-use-env-with-container-image/17252
      # image: ${{ env.DOCKER_REGISTRY }}/${{ env.PHP_TEST_IMAGE }}:latest
      # Github PKG Docker not working in container section
      # image: docker://docker.pkg.github.com/tm-bverret/php_cicd/gh-php-test:latest
      image: docker://docker.io/kerberosmorphy/gh-php-test:latest
```

Je n'aborderai pas les étapes considérant qu'ils sont fortement similaire au cas d'exemples de Bitbucket et GitLab.

##### Deploy Request

Si nous pouvons définir des conditions d'exécutions pour un **Workflow** ou des **Steps**, nous ne pouvons pas le faire pour un **Job**. Il peut être possible de déclencher un *workflow* manuellement et via push pour ensuite inclure dans chaque step une vérification de l'événement qui a déclenché le workflow pour savoir si c'était un déclenchement manuel mais ça entraînera tout de même un coup en ressources supplémentaire. C'est pourquoi j'ai intégré uniquement une étape visant à informer de la réussite des tests et pouvant offrir l'information nécessaire pour déclencher manuellement un workflow différent.

Il s'agit donc d'un job qui dépend des tests (`needs: ["php_test"]`) et auquel j'ai ajouter des variables d'environnement à la *job* désignant le `path` pour l'appel à l'API de GitHub ainsi que le `body` nécessaire. C'est information pourrait être utiliser pour générer une notification **Slack** interactive qui pourrait démarrer le *workflow* `php-deploy-workflow.yml`.

*Note: je n'ai pas testé l'appel et j'ignore si l'ID du workflow doit inclure ou non l'extension `yml` dans l'URL.*

```yml
  php_deploy_request:
    name: Deploy Request
    runs-on: ubuntu-latest
    env:
      DISPATCH_URL: /repos/${{ github.repository }}/actions/workflows/php-deploy-workflow.yml/dispatches
      BODY: '{"ref":"${{ github.ref }}", "is_approved":"1"}'
    needs: ["php_test"]
```

Concernant les notifications interactives **Slack**, ça doit obligatoirement passé par un application **Slack** créé et qui doit posséder un seul URL de réponse auquel sera retourner la réponse de l'intéraction. L'idéal pour ce cas d'utilisation serait d'avoir une fonction **Lambda@Edge** ou un **API Gateway** pour gérer les notifications et facilement intégrer divers plateforme tel que **Courriel**, **Microsoft Teams**, **Slack**, **Redmine**, etc.

[↑ Table des matières ↑](##sections)

### Fichier `php-deploy-worflow.yml`

Dû au problème expliqué à la job [Deploy Request](#####deploy-request), j'ai créé un workflow séparer pour l'exécution manuel d'un déploiement.

#### Élément deploy `on`

Nous utilisons donc l'événements `workflow_dispatch` qui permet un déclenchement manuel, ce *trigger* offrira aussi un interface graphique dans **GitHub** pour inclure des paramètres. C'est mêmes paramètres peuvent aussi être intégré pour un appel via l'**API** de **GitHub**.

J'ai choisi de créer le paramètre `is_approved` pour avoir un cas d'utilisation différent si le déploiement est accepté ou non. La valeur `0` représente `true` et toutes autres valeurs sera interprété comme `false`.

```yml
on:
  workflow_dispatch:
    inputs:
      is_approved:
        description: 'Would you start the deployment?'
        required: true
        default: '0'
```

#### Élément deploy `jobs`

Pour la *job* `Deploy`, il s'agit principalement de deux cas d'utilisation, soit le paramètre `github.event.inputs.is_approved` est vrai ou faux. Dans le cas `true`, nous pourrions procéder au déploiement, dans le cas `false` nous pourrions informer des individus du refus, utiliser l'API de Redmine pour modifier un status ou autres.

```yml
      - name: Deploy Approved
        if: ((github.event.inputs.is_approved))
        run: |
          echo "Deploy have been approved and will start."
      - name: Deploy Denied
        if: ((!github.event.inputs.is_approved))
        run: |
          echo "Deploy have been denied."
```

[↑ Table des matières ↑](##sections)

## Projet `docker-exist-action`

**GitHub Action** est basé autour des *"Actions"* qui se compare, mais en mieux, aux mécaniques de _**Pipes**_ offert par **Bitbucket**. GitLab peut simuler ce principe grâce à sa forte capacité de merger des mécaniques provenant de d'autres fichiers ou *repositories*. Les **Actions** on par contre l'avantage de pouvoir être soit basé Docker, donc un `Dockerfile` qui sera construit, soit en Javascript.

Pour explorer cette capacité j'ai exporté ma mécanique vérifiant l'existence préalable d'une image dans un registre de container quelconque.

[↑ Table des matières ↑](##sections)

### Fichier `action.yml`

Obligatoire, ce fichier défini l'action et permet de l'interpréter comme un action utilisable ailleurs.`

En dehors des informations standard tel que le `name`, la `description` et l'`author`:

```yml
name: 'Docker exist action'
description: 'Check if docker image exist'
author: 'Benoit Verret <benoit.verret@toumoro.com'
```

Nous avons les points important suivant:

#### Élément `inputs`

Défini les paramètres d'entré qui seront utiliser dans une *job* avec la clef `with`

```yml
inputs:
  registry:
    description: 'Container Registry'
    required: true
    default: 'docker.io'
  username:
    description: 'Container Registry Username'
    required: true
  password:
    description: 'Container Registry Password'
    required: true
  image:
    description: 'Image to check'
    required: true
```

Nous aurons donc le cas d'utilisation suivant:

```yml
      - name: Check if image exist
        id: is_image_exist
        uses: tm-bverret/docker-exist-action@v1.1.1
        with:
          registry: docker.io
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          image: ${{ secrets.DOCKER_USERNAME }}/my_image:tag
```

#### Élément `outputs`

Défini les paramètres de qui seront retourné et utilisable dans d'autres étapes via la référence à l'ID de l'étape utilisant l'action (`is_image_exist`).

```yml
outputs:
  image_exist:
    description: 'If image exist value is 1 else is 0'
```

Nous aurons donc le cas d'utilisation suivant:

```yml
      - name: Check if image exist
        id: is_image_exist
        uses: tm-bverret/docker-exist-action@v1.1.1
        with:
          registry: docker.io
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          image: ${{ secrets.DOCKER_USERNAME }}/my_image:tag
      - name: Publish Image if not exist
        if: ((!steps.is_image_exist.outputs.image_exist))
```

#### Élément `runs`

Défini si nous utilisons Docker ou Javascript (J'ai aussi vu un cas en GO). Permet aussi de faire passer les paramètres d'entrés. Nous pouvons les passer tel une liste sous la clef `args`, mais je trouvais plus facile à récupérer les arguments en les ajoutant comme variable d'environnement au Docker.

```yml
runs:
  using: 'docker'
  image: 'Dockerfile'
  env:
    REGISTRY: ${{ inputs.registry }}
    USERNAME: ${{ inputs.username }}
    PASSWORD: ${{ inputs.password }}
    IMAGE: ${{ inputs.image }}
```

À noter que la clef `image` pourrait aussi pointer directement sur un image docker tel que `image: 'docker://docker:dind'`, ce qui m'aurait permis de inclure de `Dockerfile` au projet en précisant mon `ENTRYPOINT` grâce à la clef `entrypoint` tel que:

```yml
runs:
  using: 'docker'
  image: 'docker://docker:dind'
  entrypoint: 'entrypoint.sh'
  env:
    REGISTRY: ${{ inputs.registry }}
    USERNAME: ${{ inputs.username }}
    PASSWORD: ${{ inputs.password }}
    IMAGE: ${{ inputs.image }}
```

J'ignore par contre si des problématiques de permission aurait été présent, j'en ai rencontré une m'obligeant à ajouter `RUN ["chmod", "+x", "/entrypoint.sh"]` dans mon `Dockerfile`.

Plus d'information sur la syntax du `runs` [**ici**](https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-docker-actions).

#### Élément `branding`

Sert à la publication de l'action dans le **Marketplace**. L'`icon` doit faire référence à un nom d'icon **Feather** et la `color` doit aussi représenter une couleur officiel de la librairie **Feather**.

```yml
branding:
  icon:  'eye'
  color: 'red'
```

[↑ Table des matières ↑](##sections)

### Fichier `Dockerfile`

[Lien vers le repository de 'docker-exist-action'](https://github.com/tm-bverret/docker-exist-action)
[Lien vers 'docker-exist-action' dans le Marketplace](https://github.com/marketplace/actions/docker-exist-action)

Plutôt simple, j'avais d'une image légère me donnant accès à **Docker CLI** à l'intérieur. Pour le reste il s'agit uniquement de définir mon point d'entré.

```Dockerfile
FROM docker:dind

COPY entrypoint.sh /entrypoint.sh

RUN ["chmod", "+x", "/entrypoint.sh"]

ENTRYPOINT ["/entrypoint.sh"]
```

[↑ Table des matières ↑](##sections)

### Fichier `entrypoint.sh`

La mécanique de mon **Action** se trouve ici. J'utilise la fonctionnalité de **Docker CLI** `docker manifest inspect` pour savoir si une image existe ou non sans avoir à effecter un `docker pull`. Si l'image n'existe pas je reçois un erreur que j'interprète comme `false` via `0`. J'utilise les commandes spéciales de **GitHub Action** `:set-output name=nom_de_ma_var::ma_valeur` pour définir l'`output` de mon **Action**. Ces commandes spéciales peuvent aussi être utilisé directement dans les *steps* d'une *job* d'un *workflow*.

Puisque `docker manifest inspect` est encore au niveau expérimental, je dois au préalable activer le mode expérimental pour y avoir accès.

```sh
#!/bin/sh -l

echo "Enabling experimental feature"
mkdir -p ~/.docker && echo '{"experimental": "enabled"}' > ~/.docker/config.json
echo "Login to docker registry $REGISTRY"
echo "$PASSWORD" | docker login --username $USERNAME --password-stdin $REGISTRY
echo "::set-output name=image_exist::$(docker manifest inspect $IMAGE > /dev/null && echo 1 || echo 0)"
```

_**Point important**: Le registre **GitHub** n'accepte pas l'inspection de manifest, il est donc impossible pour le moment de vérifier l'existence d'un image du registre **GitHub** sans effectuer un `pull`._

[↑ Table des matières ↑](##sections)

### Fichier `.github/workflows/main.yml`

Simple *workflow* visant à tester le fonctionnement de mon action. Je ne détaillerai pas l'explication mais voici le code.

```yml
name: Docker exist action tester

on: [push]

jobs:
  docker_exist_job:
    runs-on: ubuntu-latest
    name: Docker exist test
    steps:
      - name: Checkout
        uses: actions/checkout@v2
      - name: Docker exist action TRUE
        uses: tm-bverret/docker-exist-action@v1.1.2
        id: exist
        with:
          registry: 'docker.io'
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          image: 'hello-world:latest'
      - name: Docker exist action FALSE
        uses: tm-bverret/docker-exist-action@v1.1.2
        id: dont_exist
        with:
          registry: 'docker.io'
          username: '${{ secrets.DOCKER_USERNAME }}'
          password: '${{ secrets.DOCKER_PASSWORD }}'
          image: 'hello-world:fake_tag'
      - name: Get the output TRUE
        run: |
          echo "Value is: ${{ steps.exist.outputs.image_exist }}."
          if (( ${{ steps.exist.outputs.image_exist }} )); then
            exit 0
          else
            exit 1
          fi
      - name: Get the output FALSE
        run: |
          echo "Value is: ${{ steps.dont_exist.outputs.image_exist }}."
          if (( ${{ steps.dont_exist.outputs.image_exist }} )); then
            exit 1
          else
            exit 0
          fi
```

[↑ Table des matières ↑](##sections)

## GitHub Marketplace

Comparable à `npmjs`, il regroupe l'ensemble des **Action** publié par n'importe quel utilisateur **GitHub**. Si Bitbucket offre un service similaire, il semble par contre restreint à des **Pipes** semblant être créé uniquement par des gros services tel qu'**Azure** et **AWS**, comparativement au **GitHub Marketplace** qui offrent des actions de tous les types facilitant grandement l'intégration d'**Action** dans un projet et dans la gestion d'un projet et ce même avec une maigre connaissance du système en général.

Au niveau de GitLab, il ne semble pas avoir de marché l'action, mais étant basé `docker` il est possible de créer des images générique visant à exécuter des actions précises grâces à des paramètres d'entrés. Il offre aussi la fragmentation d'un **Pipeline**/**Workflow** en multiple fichier importable depuis d'autres projets.

[↑ Table des matières ↑](##sections)
