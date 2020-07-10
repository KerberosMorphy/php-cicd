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

Nous pouvons ensuite définir les étapes qui s'exécuterons en ordre dans notre *job*. Chaque étape peut être nommée et peut posséder différent élément conditionnel. Il s'agit d'un point fort de GitHub Action

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

##### Tests

Puisque par défaut les jobs s'exécute en parallèle et que nous désirons que les tests s'exécute après l'étape de build nous pouvons utiliser la clef `needs` pour définir la liste de toutes les *jobs* dont dépend celle-ci.

Pour cette *job*, j'indique que toutes les étapes doivent être exécuté dans un **container précis** plutôt que directement sur la machine virtuel *Linux*. L'image doit obligatoirement être public et ne pas nécessiter 

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
[↑ Table des matières ↑](##sections)

### Fichier `php-deploy-worflow.yml`

#### Élément deploy `on`

#### Élément deploy `jobs`

[↑ Table des matières ↑](##sections)

## Projet `docker-exist-action`

### Fichier `action.yml`

### Fichier `Dockerfile`

### Fichier `entrypoint.sh`

### Fichier `.github/workflows/main.yml`

## GitHub Marketplace
