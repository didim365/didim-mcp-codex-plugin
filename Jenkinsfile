// didim-mcp-codex-plugin — Jenkins CI/CD (Harbor build/push)
//
// 기존 DIDIM 패턴(didim-rag-backend / didim-mcp-service-backend Jenkinsfile)을 따르되,
// **deploy 저장소 자동 commit/push 단계는 두지 않는다.**
//
//   왜: 기존 두 파이프라인은 마지막에 deploy 저장소를 clone 해
//   `environments/dev/kustomization.yaml` 의 newTag 를 고치고 **자동 push** 한다.
//   이 프로젝트의 정책은 "git commit / git push 는 사람이 직접 한다" 이므로(요구사항 §25 ·
//   §31 · `.claude/rules/release.md`), 그 동작을 그대로 복사하지 않는다.
//   대신 마지막에 **image tag 와 다음에 해야 할 일**을 출력하고 끝낸다. 운영자가 그 값을
//   didim-mcp-codex-plugin-deploy 의 overlay 에 적용하고 직접 commit 한다.
//
//   나중에 자동화를 도입하기로 **결정**하면, 기존 두 저장소의 "Update deploy repo" stage 를
//   그대로 옮겨 오면 된다(스크립트도 같은 것을 쓴다). 지금 임의로 켜지 않는다.
//
// 책임 분리:
//   - Poll SCM 기준은 이 Jenkinsfile 의 triggers 하나로 통일한다(Job UI Poll SCM 중복 금지).
//   - Jenkins 는 빌드/푸시만 한다. kubectl / argocd / DB / Alembic 을 실행하지 않는다.
//   - Quality Gate 는 Docker build 안에서 한 번 더 걸린다(`npm run build` = tsc + vite).
//     ruff / mypy / pytest / eslint / vitest 는 개발자가 로컬에서 push 전에 돌린다.
//
// Jenkins agent 제약: docker/git/sh/sed/grep/awk 만 있고 **python3 가 없다.**
// 이 파이프라인은 그 셋만 쓴다.

pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 90, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  triggers {
    pollSCM('H/5 * * * *')
  }

  environment {
    // 사내 Harbor 주소는 **소스에 적지 않는다**(이 저장소는 public 이다).
    // Jenkins 의 전역 환경변수 또는 job 파라미터 HARBOR_REGISTRY 에서 읽고, 없으면
    // Init 에서 명시적으로 실패한다. 값은 deploy 저장소(private)와 같은 것을 쓴다.
    REGISTRY   = "${env.HARBOR_REGISTRY ?: ''}"
    IMAGE_NAME = 'didim-mcp-codex-plugin/app'
    IMAGE      = "${REGISTRY}/${IMAGE_NAME}"

    // 참고용. 이 파이프라인은 여기에 push 하지 않는다(위 주석 참조).
    DEPLOY_REPO   = 'github.com/didim365/didim-mcp-codex-plugin-deploy.git'
    DEPLOY_BRANCH = 'develop'
    KUSTOMIZATION = 'environments/dev/kustomization.yaml'

    HARBOR_CREDENTIALS_ID = 'harbor-push-credential'
  }

  stages {
    stage('Init') {
      steps {
        script {
          if (!env.REGISTRY?.trim()) {
            error('HARBOR_REGISTRY is not set (Jenkins global env or job parameter). ' +
                  'The registry host is intentionally not committed to this public repo.')
          }
          if (!env.GIT_COMMIT?.trim()) {
            error('GIT_COMMIT is not available after SCM checkout')
          }
          env.SHA = env.GIT_COMMIT.take(7)
          if (!(env.SHA ==~ /^[0-9a-f]{7}$/)) {
            error("unexpected GIT_COMMIT short sha (not 7-hex): ${env.SHA}")
          }
          env.IMAGE_TAG  = "sha-${env.SHA}"
          env.FULL_IMAGE = "${env.IMAGE}:${env.IMAGE_TAG}"
        }
        echo "Source commit : ${env.GIT_COMMIT}"
        echo "Building image: ${env.FULL_IMAGE} (+ ${env.IMAGE}:dev)"
      }
    }

    stage('Plugin manifests') {
      // 이 저장소는 Codex Plugin artifact 도 함께 담고 있다. 매니페스트가 깨지면
      // 사용자 설치가 깨지므로 이미지 빌드 전에 형식만 확인한다(python3 없이 가능한 검사).
      steps {
        sh '''
          set -eu
          for f in .agents/plugins/marketplace.json \
                   plugins/didim-mcp/.codex-plugin/plugin.json; do
            test -s "$f" || { echo "missing manifest: $f" >&2; exit 1; }
            # 최소 형식 확인: 중괄호로 시작/끝나고 name 키가 있다.
            head -c 1 "$f" | grep -q '{' || { echo "not json: $f" >&2; exit 1; }
            grep -q '"name"' "$f" || { echo "no name key: $f" >&2; exit 1; }
          done
          # 배포되는 Skill 은 다섯 개다. 라우터 네 개는 Registry 를 참조해야 한다.
          test "$(ls -1d plugins/didim-mcp/skills/*/ | wc -l)" -eq 5
          for s in didim-mcp-usage didim-vault molit-apartment-transactions didim-dynamic-skill; do
            grep -q 'didim-skill__get_skill' "plugins/didim-mcp/skills/$s/SKILL.md" \
              || { echo "thin router lost its registry reference: $s" >&2; exit 1; }
          done
          echo "[OK] plugin manifests and thin routers look intact"
        '''
      }
    }

    stage('Prepare CA') {
      // 사내망 FortiGate CA 는 public 저장소에 커밋하지 않는다(certs/README.md 참고).
      // Jenkins Secret file 자격증명에서 꺼내 build context 에 놓는다. 자격증명이
      // 없으면 건너뛴다 — 사외망/격리 빌드에서는 필요 없기 때문이다.
      steps {
        script {
          try {
            withCredentials([file(credentialsId: 'didim-fortigate-ca', variable: 'CA_FILE')]) {
              sh 'install -m 0644 "$CA_FILE" certs/fortigate-ca.crt && echo "[OK] CA placed"'
            }
          } catch (ignored) {
            echo '[SKIP] didim-fortigate-ca credential not found — building without the CA'
          }
        }
      }
    }

    stage('Build') {
      // frontend lint/typecheck/build 는 이 build 안에서 실행된다
      // (web-build stage 의 `npm run build` = `tsc --noEmit && vite build`).
      steps {
        sh '''
          set -eu
          docker build -t "$IMAGE:dev" -t "$IMAGE:$IMAGE_TAG" .
        '''
      }
    }

    stage('Smoke') {
      // 이미지가 실제로 뜨는지만 본다. DB 없이 bootstrap 모드로 /health 가 200 이어야 한다.
      // 여기서 DB 에 붙지 않는다(Jenkins 에서 운영 DB 를 건드리지 않는다).
      steps {
        sh '''
          set -eu
          CID="$(docker run -d -p 18080:8080 "$IMAGE:$IMAGE_TAG")"
          trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT
          ok=0
          i=0
          while [ "$i" -lt 30 ]; do
            if docker exec "$CID" python -c \
                "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3).status==200 else 1)"; then
              ok=1; break
            fi
            i=$((i+1))
            sleep 2
          done
          [ "$ok" -eq 1 ] || { docker logs "$CID" >&2; echo "health check failed" >&2; exit 1; }
          echo "[OK] image starts and answers /health"
        '''
      }
    }

    stage('Push Harbor') {
      steps {
        withCredentials([
          usernamePassword(
            credentialsId: env.HARBOR_CREDENTIALS_ID,
            usernameVariable: 'HARBOR_USERNAME',
            passwordVariable: 'HARBOR_PASSWORD'
          )
        ]) {
          sh '''
            set -eu
            printf '%s' "$HARBOR_PASSWORD" |
              docker login "$REGISTRY" --username "$HARBOR_USERNAME" --password-stdin
            docker push "$IMAGE:dev"
            docker push "$IMAGE:$IMAGE_TAG"
            docker logout "$REGISTRY"
          '''
        }
      }
    }

    stage('Report image tag') {
      // 자동 push 를 하지 않으므로, 운영자가 그대로 복사할 수 있게 명확히 출력한다.
      steps {
        sh '''
          set -eu
          echo "=============================================================="
          echo " IMAGE  : ${FULL_IMAGE}"
          echo " TAG    : ${IMAGE_TAG}"
          echo ""
          echo " 다음 단계는 사람이 직접 수행한다(자동 push 하지 않는다):"
          echo "   1) ${DEPLOY_REPO} (${DEPLOY_BRANCH}) 를 clone"
          echo "   2) ${KUSTOMIZATION} 의 images[0].newTag 를 ${IMAGE_TAG} 로 변경"
          echo "      (scripts/update_kustomize_image_tag.sh 가 그 한 값만 바꾼다)"
          echo "   3) 새 컬럼을 기대하는 변경이면 migration Job 을 먼저 1회 실행"
          echo "   4) commit / push → ArgoCD 가 감지"
          echo "=============================================================="
        '''
      }
    }
  }

  post {
    always {
      // 로컬 dev image 는 다음 빌드 캐시에 유용하므로 삭제하지 않는다. prune 금지.
      sh 'docker logout "$REGISTRY" || true'
    }
  }
}
