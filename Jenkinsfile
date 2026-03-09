// ---------------------------------------------------------------------------
// Jenkinsfile — ACEest Fitness & Gym Management
// Declarative Pipeline for the BUILD phase quality gate
// ---------------------------------------------------------------------------

pipeline {

    agent any

    environment {
        APP_NAME    = 'aceest-fitness'
        IMAGE_TAG   = "${APP_NAME}:${env.BUILD_NUMBER}"
        LATEST_TAG  = "${APP_NAME}:latest"
    }

    stages {

        stage('Checkout') {
            steps {
                echo '📥 Pulling latest code from GitHub...'
                checkout scm
                echo "Build #${env.BUILD_NUMBER} — Branch: ${env.GIT_BRANCH}"
            }
        }

        stage('Build Environment') {
            steps {
                echo '📦 Installing Python dependencies...'
                sh '''
                    python3 -m pip install --upgrade pip
                    pip3 install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo '🔍 Running flake8 lint checks...'
                sh 'flake8 app.py --max-line-length=120 --statistics'
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "🐳 Building Docker image: ${IMAGE_TAG}"
                sh '''
                    docker build -t $IMAGE_TAG .
                    docker tag  $IMAGE_TAG $LATEST_TAG
                '''
            }
        }

        stage('Run Tests') {
            steps {
                echo '🧪 Executing Pytest suite inside Docker container...'
                sh '''
                    docker run --rm \
                        -e PYTHONDONTWRITEBYTECODE=1 \
                        $IMAGE_TAG \
                        pytest tests/ -v --tb=short
                '''
            }
        }

        stage('Clean Up') {
            steps {
                echo '🧹 Removing intermediate Docker image...'
                sh 'docker rmi $IMAGE_TAG || true'
            }
        }
    }

    post {
        success {
            echo '✅ BUILD SUCCEEDED — All stages passed. Code is ready for deployment.'
        }
        failure {
            echo '❌ BUILD FAILED — Check stage logs above for details.'
        }
        always {
            echo "Pipeline completed for build #${env.BUILD_NUMBER}"
        }
    }
}
