#!groovy

pipeline {
    agent any
    stages {
        stage('Building') {
            steps {
                echo 'Stage: Building...'
                sh "pipeline/build.sh"
            }
        }
        stage('Style check') {
            steps {
                echo 'Stage: Style check...'
                sh "pipeline/checkstyle.sh"
            }
        }
        stage('Testing') {
            steps {
                echo 'Stage: Testing...'
                sh "pipeline/test.sh"
            }
        }
        stage('Publication') {
            steps {
                echo 'Stage: Publication...'
                sh "pipeline/publish.sh"
            }
        }
        stage('Promoting release v5.1') {
            when {
                branch 'v5.1'
            }
            stages {
                stage('Generating release') {
                    steps {
                        sh 'docker tag registry.sonata-nfv.eu:5000/tng-sdk-test:latest registry.sonata-nfv.eu:5000/tng-sdk-test:v5.1'
                        sh 'docker tag registry.sonata-nfv.eu:5000/tng-sdk-test:latest sonatanfv/tng-sdk-test:v5.1'
                        sh 'docker push registry.sonata-nfv.eu:5000/tng-sdk-test:v5.1'
                        sh 'docker push sonatanfv/tng-sdk-test:v5.1'
                    }
                }
            }
        }
    }

    post {
        success {
            emailext(from: "jenkins@sonata-nfv.eu", 
            to: "askhat.nuriddinov@ugent.be", 
            subject: "SUCCESS: ${env.JOB_NAME}/${env.BUILD_ID} (${env.BRANCH_NAME})",
            body: "${env.JOB_URL}")
        }
        failure {
            emailext(from: "jenkins@sonata-nfv.eu", 
            to: "askhat.nuriddinov@ugent.be", 
            subject: "FAILURE: ${env.JOB_NAME}/${env.BUILD_ID} (${env.BRANCH_NAME})",
            body: "${env.JOB_URL}")
        }
    }
}
