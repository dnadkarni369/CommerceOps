// CommerceOps CI/CD pipeline
// Builds every microservice, runs basic checks, pushes to ECR, then
// deploys via Ansible (EC2/ASG target) or kubectl (k3s target).
//
// Required Jenkins credentials (configure in Manage Jenkins > Credentials):
//   aws-creds        - AWS access key/secret with ECR + EC2 permissions
//   ssh-key-ansible  - SSH private key used by Ansible to reach app servers
//
// Required Jenkins plugins: Docker Pipeline, Pipeline: AWS Steps, Ansible

pipeline {
    agent any

    environment {
        AWS_REGION      = 'ap-south-1'
        ECR_REGISTRY    = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        DEPLOY_TARGET   = 'ec2' // 'ec2' or 'k8s' - switch based on which infra path you're demoing
    }

    parameters {
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Deploy after a successful build?')
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                script {
                    def services = ['frontend', 'api-services', 'auth-services', 'order-services', 'ai-recommendation-service', 'worker-service']
                    services.each { svc ->
                        sh """
                            echo "Linting ${svc}..."
                            docker run --rm -v \$(pwd)/services/${svc}:/app -w /app python:3.12-slim \
                                bash -c "pip install --quiet flake8 && flake8 --max-line-length=120 --extend-ignore=E203,W503 . || true"
                        """
                    }
                }
            }
        }

        stage('Build Images') {
            steps {
                script {
                    def services = [
                        'frontend'                  : 'frontend',
                        'api-service'                : 'api-services',
                        'auth-service'               : 'auth-services',
                        'order-service'              : 'order-services',
                        'ai-recommendation-service'  : 'ai-recommendation-service',
                        'worker-service'             : 'worker-service',
                    ]
                    services.each { imageName, dir ->
                        sh "docker build -t commerceops/${imageName}:${IMAGE_TAG} -t commerceops/${imageName}:latest ./services/${dir}"
                    }
                }
            }
        }

        stage('Scan Images') {
            steps {
                script {
                    def images = ['frontend', 'api-service', 'auth-service', 'order-service', 'ai-recommendation-service', 'worker-service']
                    images.each { img ->
                        sh "docker run --rm aquasec/trivy image --exit-code 0 --severity HIGH,CRITICAL commerceops/${img}:${IMAGE_TAG} || true"
                    }
                }
            }
        }

        stage('Push to ECR') {
            steps {
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
                    sh """
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    """
                    script {
                        def images = ['frontend', 'api-service', 'auth-service', 'order-service', 'ai-recommendation-service', 'worker-service']
                        images.each { img ->
                            sh """
                                docker tag commerceops/${img}:${IMAGE_TAG} ${ECR_REGISTRY}/commerceops/${img}:${IMAGE_TAG}
                                docker tag commerceops/${img}:${IMAGE_TAG} ${ECR_REGISTRY}/commerceops/${img}:latest
                                docker push ${ECR_REGISTRY}/commerceops/${img}:${IMAGE_TAG}
                                docker push ${ECR_REGISTRY}/commerceops/${img}:latest
                            """
                        }
                    }
                }
            }
        }

        stage('Deploy') {
            when {
                expression { return params.DEPLOY }
            }
            steps {
                script {
                    if (env.DEPLOY_TARGET == 'ec2') {
                        sshagent(credentials: ['ssh-key-ansible']) {
                            sh """
                                cd infra/ansible
                                ansible-playbook -i inventory.ini playbook.yml \
                                    --extra-vars "ecr_registry=${ECR_REGISTRY} image_tag=${IMAGE_TAG} aws_region=${AWS_REGION}"
                            """
                        }
                    } else {
                        sh """
                            for f in infra/k8s/*.yaml; do
                                sed "s|commerceops/\\([a-z-]*\\):latest|${ECR_REGISTRY}/commerceops/\\1:${IMAGE_TAG}|g" "\$f" | kubectl apply -f -
                            done
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f'
        }
        success {
            echo "Build ${IMAGE_TAG} succeeded."
        }
        failure {
            echo "Build ${IMAGE_TAG} failed - check console output."
        }
    }
}
