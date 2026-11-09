// Pipeline de deploy da Vinheria Agnello (ms-catalogo e ms-estoque)
pipeline {
    agent any

    environment {
        DESTINO = '/publicacao/vinheria'
    }

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Checkout') {
            steps {
                sh 'git log -1 --pretty="Commit %h — %s (%an)"'
            }
        }
        stage('Build') {
            steps {
                echo 'Deploy da Vinheria'
                sh 'python3 -m py_compile services/comum/seguranca.py services/ms-catalogo/app.py services/ms-estoque/app.py'
            }
        }
        stage('Testes') {
            steps {
                sh 'python3 -m unittest discover -s tests -v'
            }
        }
        stage('Segurança') {
            steps {
                sh 'sh scripts/verificar_segredos.sh'
            }
        }
        stage('Pacote') {
            steps {
                sh 'sh scripts/empacotar.sh "$BUILD_NUMBER" "$GIT_COMMIT"'
                archiveArtifacts artifacts: 'dist/**', fingerprint: true
            }
        }
        stage('Deploy') {
            steps {
                sh 'sh scripts/publicar.sh "$BUILD_NUMBER" "$DESTINO"'
            }
        }
    }

    post {
        success { echo "Versão ${env.BUILD_NUMBER} publicada em ${env.DESTINO}/atual" }
        failure { echo 'Falha no pipeline: nada foi publicado' }
    }
}
