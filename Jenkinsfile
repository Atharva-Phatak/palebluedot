pipeline {
  agent {
    kubernetes {
      label 'docker-builder' // This should match the label in your pod template
      defaultContainer 'jnlp' // This is where the Jenkins agent runs
    }
  }

  environment {
    GHCR_PAT = credentials('ghcr-token') // From Jenkins Credentials
  }

  triggers {
    githubPush()
  }

  stages {
    stage('Clone Repository') {
      steps {
        checkout scm
      }
    }

    stage('Detect Changed Pipeline') {
      steps {
        script {
          def changes = currentBuild.changeSets.collectMany { it.items }.collectMany { it.affectedFiles*.path }
          echo "Changed files: ${changes}"

          def pipelineChanged = changes.find { it.startsWith("pbd/pipelines/") && it.endsWith("Dockerfile") }
          if (!pipelineChanged) {
            echo "No pipeline Dockerfile changes detected. Skipping build."
            currentBuild.result = 'NOT_BUILT'
            error("No relevant pipeline changes.")
          }

          def parts = pipelineChanged.split("/")
          env.PIPELINE_NAME = parts[2]
          echo "Pipeline detected: ${env.PIPELINE_NAME}"
        }
      }
    }

    stage('Build & Push Docker Image') {
      agent {
        // Run this stage inside the DinD-enabled pod
        kubernetes {
          label 'docker-builder'
          defaultContainer 'docker' // This is the DinD container
        }
      }
      steps {
        container('docker') {
          sh '''
            chmod +x scripts/jenkins_build.sh
            PIPELINE_NAME=$PIPELINE_NAME ./scripts/jenkins_docker_build.sh
          '''
        }
      }
    }
  }
}
