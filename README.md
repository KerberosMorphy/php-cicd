# GitLab CI

Explication de l'expérimentation d'un pipeline de déploiement avec GitLab CI.
L'utilisation de PHP est uniquement pour la démonstration,
les concepts peuvent être appliqués à n'importe quel langage.

## Sections

- [`.gitlab-ci.yml`](##fichier-gitlab-ciyml`)
- [`PHP-Build.gitlab-ci.yml`](docs/PHP-Build.md)
- [`PHP-Unit-Test.gitlab-ci.yml`](docs/PHP-Unit-Test.md)
- [`PHP-Deploy.gitlab-ci.yml`](docs/PHP-Deploy.md)

## Fichier `.gitlab-ci.yml`

Dans le fichier `.gitlab-ci.yml` situé à la racine du projet, nous avons 5 parties.

### Stages

La clef `stages` sert a définir les étapes de notre pipeline.

```yml
stages:
  - build
  - build:test
  - build:failure
  - test:unit
  - test:integration
  - test:functional
  - test:acceptance
  - test:coverage
  - test:failure
  - deploy
  - deploy:failure
```

### Variables

Le fait de définir les variables à l'extérieur d'un `Jobs` rend ces variables accessibles dans toutes les `Jobs`.
On peut simplifier en disant que les variables sont déclarées *globalement*.

```yml
variables:
  PHP_IMAGE: $CI_REGISTRY_IMAGE
  PHP_TEST_IMAGE: $CI_REGISTRY_IMAGE/php_test
```

La clef `PHP_IMAGE` représente le nom de l'image principale au registre GitLab.

La clef `PHP_TEST_IMAGE` représente le nom de l'image utilisé pour les tests, plus de détail dans la section [`PHP-Build`](docs/PHP-Build.md).

### Include

Le mot clef `include` permet d'ajouter des actions GitLab CI provenant de ressources externes.
Les fichiers peuvent être présent à même le repo du projet et être ciblés grâce à la clef `local`, mais peuvent aussi provenir d'un autre repo, d'un URL public ou de template officiel de GitLab, [plus d'information ici](https://docs.gitlab.com/ee/ci/yaml/#include).

Importation des Jobs définis localement. L'ordre peut être important, car la dernière pourrait remplacer des éléments ayant le même nom.

```yml

include:
  - local: /gitlab-ci/Jobs/PHP-Build.gitlab-ci.yml
  - project: benoit.verret.tm/php-cicd
    ref: master
    file: /gitlab-ci/Jobs/PHP-Unit-Test.gitlab-ci.yml
  - local: /gitlab-ci/Jobs/PHP-Deploy.gitlab-ci.yml
```

Pour l'exemple, bien que le fichier soit local dans le projet, j'ai joint une démonstration d'importation depuis un différent projet, on peut donc spécifier le non du projet, la branche et l'emplacement du fichier dans le projet. Si le projet fait parti d'un groupe on ferait `project: mon-groupe/mon-projet`.

En dehors des `Jobs`, on pourrait aussi imaginer avoir nos variables à l'extérieur.

### Before Script

La clef `before_script` définie du script a exécuté avant les scripts "normal" et pour toutes les `Jobs`, son contenu sera donc exécuté à nouveau avant le script de chaque `Job`.

```yml
before_script:
  - *auto_devops
  - set_stage_variable
```

On peut voir ici l'utilisation de la syntaxe spéciale **YAML** `*auto_devops` qui permet d'inclure le contenu de l'ancre `&auto_devops`.

### Utilisation d'ancre et définition de fonction

*Noter que le nom `.auto_devops` est arbitraire.*

J'ai défini plusieurs fonctions que je peux réutiliser au travers des `Jobs` selon les besoins.

Par exemple, `registry_login` nous log au registry de GitLab, mais on aurait aussi pu mettre une condition du type **« Si la variable AWS_ECR est définie, se connecter au Registry d'AWS ECR »**.

```sh
  function registry_login() {
    if [[ -n "$CI_REGISTRY_USER" ]]; then
      echo "Logging to GitLab Container Registry with CI credentials..."
      echo $CI_REGISTRY_PASSWORD | docker login -u "$CI_REGISTRY_USER" --password-stdin "$CI_REGISTRY"
      echo ""
    fi
  }
```

La fonction `build_docker` permet de construire l'image, elle va récupérer la plus récente si elle existe et l'utiliser comme cache pour en construire une nouvelle avec les modifications appliquées. C'est en suivant l'exemple de GitLab que j'ai choisi de construire 2 images, un avec le tag latest, l'autre avec le hash du commit comme tag, cette méthode permet de garder un suivi des versions. Une fois construit, les images seront poussées vers le registry du projet de GitLab.

Comparativement à la démonstration [Serverless-CICD](https://gitlab.com/benoit.verret.tm/serverless-cicd), des options ont été ajouté pour construire depuis des `Dockerfile` différent.

Nous avons donc les options suivante:

- **`-i`** : Sert à spécifier le nom de l'image dans le registre d'image GitLab. Il sera utilisé ainsi « `build_docker -i "$PHP_IMAGE"` »;

- **`-d`** : Sert à spécifier le nom du `Dockerfile` à utiliser, les dockerfile doivent être situé dans le dossier `docker/`. Il sera utilisé ainsi « `build_docker -i "$PHP_TEST_IMAGE" -d "Test.Dockerfile"` »;

- **`-a`** : Sert à spécifier les arguments à passer au `Dockerfile` pour personnaliser l'image, les dockerfile doivent être situé dans le dossier `docker/`. Par exemple, dans `Test.Dockerfile` je construis mon image en la base sur `php:7.4` par défaut, mais je me laisse l'option de pouvoir la bâtir sur un autre image tel que l'image préalablement construite « `build_docker -i "$PHP_TEST_IMAGE" -d "Test.Dockerfile" -a "base_image=$PHP_IMAGE:latest"` ». Cette méthode pourrait être fait pour utiliser des version php différente.;

```sh
  function build_docker() {
    dockerfile="Dockerfile"
    image_name=$CI_REGISTRY_IMAGE
    echo "Set registry image name to build..."
    while getopts ":i:d:a:" opt; do
      case $opt in
        i) image_name="$OPTARG";;
        d) dockerfile="$OPTARG";;
        a) args="$OPTARG";;
      esac
    done
    echo "Image name set to $image_name"
    echo "Dockerfile set to $dockerfile"
    echo ""
    echo "Pull image from registry to by used as cache..."
    docker pull --quiet $image_name:latest || true
    echo ""
    if [ -n "$args" ]; then
      echo "Build image with args $args from pulled image cache and create `latest` and `commit_sha` tags..."
      echo "docker build --quiet --cache-from $image_name:latest --build-arg $args --tag $image_name:$CI_COMMIT_SHA --tag $image_name:latest -f 'docker/$dockerfile' 'docker/'"
      docker build --quiet --cache-from $image_name:latest --build-arg $args --tag $image_name:$CI_COMMIT_SHA --tag $image_name:latest -f "docker/$dockerfile" "docker/"
    else
      echo "Build image from pulled image cache and create `latest` and `commit_sha` tags..."
      docker build --quiet --cache-from $image_name:latest --tag $image_name:$CI_COMMIT_SHA --tag $image_name:latest -f "docker/$dockerfile" "docker/"
    fi
    echo ""
    echo "Push the tagged Docker images to the container registry.."
    docker push $image_name:$CI_COMMIT_SHA
    docker push $image_name:latest
    echo ""
  }
```

Finalement, la fonction `set_stage_variable` me permet de définir ma variable `$STAGE` selon ma branche, l'exemple ici indique que pour la branche `master` mon stage est `staging` et que pour la branche `production` il utilisera `production`. La variable `$STAGE` est ensuite passé lors des build/deploy tel que `yarn build --mode=$STAGE` ou `sls deploy --stage=$STAGE`.

```sh
  function set_stage_variable() {
    echo "Set current stage..."
    if [[ "$CI_COMMIT_REF_NAME" == "master" ]]; then
      export STAGE="staging"
    elif [[ "$CI_COMMIT_REF_NAME" == "production" ]]; then
      export STAGE="production"
    fi
    echo "Stage set to `$STAGE`"
    echo ""
  }
```
