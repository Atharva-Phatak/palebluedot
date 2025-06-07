pipeline {
  agent any

  environment {
    GHCR_PAT = credentials('ghcr-token') // Jenkins Secret Text credential
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

  stages {
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

          // Extract pipeline name from path like pbd/pipelines/ocr_engine/Dockerfile
          def parts = pipelineChanged.split("/")
          env.PIPELINE_NAME = parts[2]
          echo "Pipeline detected: ${env.PIPELINE_NAME}"
        }
      }
    }

    stage('Build & Push Docker Image') {
      steps {
        sh '''
          chmod +x scripts/jenkins_build.sh
          PIPELINE_NAME=$PIPELINE_NAME ./scripts/jenkins_build.sh
        '''
      }
    }

    stage('Trigger ZenML') {
      steps {
        echo "Triggering ZenML pipeline for $PIPELINE_NAME"
        // You could do: sh "zenml pipeline run --name $PIPELINE_NAME" or a REST API call here
      }
    }
  }
}
